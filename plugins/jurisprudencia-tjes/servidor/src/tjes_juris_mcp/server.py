"""Servidor MCP (stdio) da jurisprudência pública do TJES."""
from __future__ import annotations

import logging
import re
import sys
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from tjes_juris_mcp import bnp, formatacao
from tjes_juris_mcp.http import descrever_falha
from tjes_juris_mcp.resolver import resolver
from tjes_juris_mcp.tjes import ACERVOS, ConsultaRecusada, TjesClient

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

INSTRUCOES = """\
Pesquisa na jurisprudência pública do Tribunal de Justiça do Espírito Santo
(cinco acervos) e nos precedentes qualificados do TJES no Banco Nacional de
Precedentes do CNJ.

Ao apresentar:
- Transcreva ementa, trecho, tese e enunciado PALAVRA POR PALAVRA, como a
  ferramenta devolve. Não resuma dentro da citação, não corrija, não complete.
- Preserve os rótulos: no PJe a data é de JUNTADA, não da sessão; no acórdão
  o magistrado do índice é o redator do voto vencedor.
- Precedente não admitido, superado, revisado ou cancelado nunca aparece como
  vigente.
- Declare a cobertura: acervo consultado, total encontrado, quanto foi exibido
  e o que ficou de fora. Não preencha lacuna com conhecimento próprio.
- A distribuição por órgão e magistrado é contagem do índice. Não a converta
  em juízo sobre a pessoa ("favorável", "rigoroso").
"""

mcp = FastMCP("tjes-jurisprudencia", instructions=INSTRUCOES)

AcervoChave = Literal["pje2g", "pje2g_mono", "pje1g", "legado", "turma_recursal_legado"]
Valores = Annotated[
    list[str],
    Field(description="Valores EXATOS do índice (use tjes_resolver_filtro). Vários = OU."),
]
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _falha(exc: Exception, fonte: str = "A consulta pública do TJES") -> str:
    return f"**Falha:** {descrever_falha(exc, fonte)}"


@mcp.tool()
async def tjes_pesquisar(
    termo: Annotated[str, Field(
        description=(
            "Texto a procurar. Palavras soltas viram AND (todas precisam aparecer). "
            'Expressão exata vai entre aspas: "tráfico privilegiado". Aceita '
            "operadores AND, OR, NOT. Use *:* para listar sem termo."
        ),
        min_length=1, max_length=400,
    )],
    acervo: Annotated[AcervoChave, Field(
        description=(
            "pje2g = acórdãos do 2º grau (padrão); pje2g_mono = decisões "
            "monocráticas; pje1g = sentenças e decisões do 1º grau; legado = 2º grau "
            "físico; turma_recursal_legado = turmas recursais (Projudi)."
        ),
    )] = "pje2g",
    orgao: Valores = [],  # noqa: B006 - o FastMCP precisa do padrão no esquema
    magistrado: Valores = [],  # noqa: B006
    classe: Valores = [],  # noqa: B006
    assunto: Valores = [],  # noqa: B006
    comarca: Valores = [],  # noqa: B006
    jurisdicao: Valores = [],  # noqa: B006
    data_inicio: Annotated[str, Field(description="AAAA-MM-DD, opcional")] = "",
    data_fim: Annotated[str, Field(description="AAAA-MM-DD, opcional")] = "",
    ordem: Literal["relevancia", "recentes", "antigos"] = "relevancia",
    quantidade: Annotated[int, Field(ge=1, le=25)] = 10,
    pagina: Annotated[int, Field(ge=1, le=500)] = 1,
) -> str:
    """Pesquisa um acervo do TJES e devolve julgados com ementa (ou trecho)
    literal, a distribuição do resultado por órgão, magistrado, classe e
    assunto, e como conferir cada julgado na consulta pública."""
    filtros = {
        "orgao": orgao, "magistrado": magistrado, "classe": classe,
        "assunto": assunto, "comarca": comarca, "jurisdicao": jurisdicao,
    }
    filtros = {k: [v for v in vs if v] for k, vs in filtros.items() if vs}
    invalidos = [k for k in filtros if k not in ACERVOS[acervo].campos]
    if invalidos:
        disponiveis = ", ".join(ACERVOS[acervo].campos)
        return (
            f"O acervo `{acervo}` não tem o(s) filtro(s) {', '.join(invalidos)}. "
            f"Disponíveis: {disponiveis}."
        )
    for rotulo, data in (("data_inicio", data_inicio), ("data_fim", data_fim)):
        if data and not _DATA.match(data):
            return f"`{rotulo}` precisa estar no formato AAAA-MM-DD."
    try:
        async with TjesClient() as cliente:
            r = await cliente.pesquisar(
                acervo, termo, filtros, pagina=pagina, por_pagina=quantidade,
                ordem=ordem, data_inicio=data_inicio, data_fim=data_fim,
            )
    except ConsultaRecusada as exc:
        return f"**Consulta não enviada:** {exc}"
    except Exception as exc:  # noqa: BLE001 - devolvido como texto à conversa
        return _falha(exc)
    return formatacao.resultado(r)


@mcp.tool()
async def tjes_resolver_filtro(
    texto: Annotated[str, Field(
        description='O que a pessoa escreveu: "1ª câmara cível", "des. Fulano", "apelação".',
        min_length=2, max_length=200,
    )],
    acervo: AcervoChave = "pje2g",
    campo: Annotated[
        Literal["orgao", "magistrado", "classe", "assunto", "comarca", "jurisdicao"] | None,
        Field(description="Campo, se já se sabe; sem ele, a ferramenta deduz."),
    ] = None,
    termo: Annotated[str, Field(
        description="Tema da pesquisa, para que as contagens sejam as do tema.",
        max_length=400,
    )] = "",
) -> str:
    """Converte o filtro escrito pela pessoa no valor exato do índice (com
    caixa, acento e espaço como o tribunal grava). Os filtros de
    tjes_pesquisar só funcionam com o valor exato."""
    try:
        async with TjesClient() as cliente:
            lista = await resolver(cliente, acervo, texto, campo, termo)
    except Exception as exc:  # noqa: BLE001
        return _falha(exc)
    return formatacao.resolucoes(lista, acervo)


@mcp.tool()
async def tjes_inteiro_teor(
    numero_processo: Annotated[str, Field(min_length=10, max_length=60)],
    acervo: AcervoChave = "pje2g",
    posicao: Annotated[int, Field(
        ge=1, le=10, description="Qual documento, quando o processo tem vários no acervo."
    )] = 1,
) -> str:
    """Inteiro teor de um julgado pelo número do processo (até 60 mil
    caracteres; o corte é declarado)."""
    try:
        async with TjesClient() as cliente:
            julgados = await cliente.por_numero(acervo, numero_processo)
    except Exception as exc:  # noqa: BLE001
        return _falha(exc)
    return formatacao.inteiro_teor(julgados, numero_processo, acervo, posicao)


@mcp.tool()
async def tjes_precedentes_qualificados(
    termo: Annotated[str, Field(
        description=(
            "Palavras que precisam aparecer na tese ou na questão (todas). "
            "Vazio lista todos."
        ),
        max_length=300,
    )] = "",
    tipos: Annotated[
        list[Literal["IRDR", "IAC", "SIRDR", "SUM", "NT", "ENU", "OJ"]],
        Field(description="Restringe a espécies; vazio = todas."),
    ] = [],  # noqa: B006
) -> str:
    """IRDR, IAC, súmulas e notas técnicas do TJES no Banco Nacional de
    Precedentes, com tese literal e situação (não admitidos, superados e
    cancelados saem separados)."""
    try:
        todos = await bnp.BnpClient().todos()
    except Exception as exc:  # noqa: BLE001
        return _falha(exc, "O Banco Nacional de Precedentes")
    return formatacao.precedentes(bnp.filtrar(todos, termo, list(tipos)), termo, len(todos))


@mcp.tool()
async def tjes_acervos() -> str:
    """Estado e tamanho dos cinco acervos e os filtros de cada um. Serve
    também para testar a conexão com o tribunal."""
    try:
        async with TjesClient() as cliente:
            estado = await cliente.acervos()
    except Exception as exc:  # noqa: BLE001
        return _falha(exc)
    return formatacao.acervos(estado)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
