"""Consulta pública de jurisprudência do TJES: cinco acervos, cinco esquemas.

A API (`sistemas.tjes.jus.br/consulta-jurisprudencia/api`) responde sem
autenticação. Medido em 26/10/2026:

    pje1g                   1º grau, sentenças e decisões   1.629.350
    pje2g                   2º grau, acórdãos                 238.895
    pje2g_mono              2º grau, monocráticas             106.403
    legado                  2º grau, processos físicos        326.849
    turma_recursal_legado   turmas recursais (Projudi)         59.491

Cada acervo nomeia os campos do seu jeito: o magistrado é `magistrado` no
PJe, `nome_desembargador` no legado e `nome_juiz` nas turmas; só o acórdão
do 2º grau tem campo de ementa; o legado e as turmas trazem a data do
julgamento, e o PJe só a data de juntada. O mapa `ACERVOS` concentra essas
diferenças, para que o resto do código fale uma língua só.

Particularidades que mudam o resultado:

1. Palavras soltas são tratadas como alternativa pelo índice. "usucapião
   especial urbana" casava com quase todo o 1º grau, porque "especial"
   casa com "Juizado Especial". A consulta junta as palavras por AND.
2. Os filtros exigem o valor exato do índice, com caixa, acento e até
   espaço na ponta ("QUARTA CÂMARA CÍVEL "). Por isso os valores vêm do
   resolvedor, nunca do que a pessoa digitou.
3. No acórdão, o campo de magistrado traz o redator do voto vencedor.
   Havendo divergência, o relator originário sai do próprio texto.
4. A página pública não abre um julgado por endereço: ela ignora a URL.
   A conferência é por instrução (acervo + número entre aspas).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from tjes_juris_mcp import texto as tx
from tjes_juris_mcp.http import com_nova_tentativa, novo_cliente

logger = logging.getLogger(__name__)

BASE = "https://sistemas.tjes.jus.br/consulta-jurisprudencia"
API = f"{BASE}/api"

# Campos lógicos que quem pesquisa usa, em ordem de exibição.
CAMPOS_LOGICOS = ("orgao", "magistrado", "classe", "assunto", "comarca", "jurisdicao")
ROTULOS = {
    "orgao": "Órgão julgador",
    "magistrado": "Magistrado",
    "classe": "Classe",
    "assunto": "Assunto",
    "comarca": "Comarca",
    "jurisdicao": "Jurisdição",
}


@dataclass(frozen=True)
class Acervo:
    chave: str
    descricao: str
    nome_na_pagina: str
    campos: dict[str, str]
    texto: str
    ementa: str | None
    numero: str
    data: str
    data_rotulo: str
    ordem_data: str
    classe: str | None = None
    extras: tuple[str, ...] = ()


ACERVOS: dict[str, Acervo] = {
    "pje2g": Acervo(
        chave="pje2g",
        descricao="2º grau, acórdãos (PJe)",
        nome_na_pagina="2º Grau PJe",
        campos={
            "orgao": "orgao_julgador", "magistrado": "magistrado",
            "classe": "classe_judicial", "assunto": "lista_assunto",
            "jurisdicao": "jurisdicao",
        },
        texto="acordao", ementa="ementa", numero="nr_processo",
        data="dt_juntada", data_rotulo="juntada", ordem_data="dt_juntada",
        classe="classe_judicial",
    ),
    "pje2g_mono": Acervo(
        chave="pje2g_mono",
        descricao="2º grau, decisões monocráticas (PJe)",
        nome_na_pagina="2º Grau Monocrático PJe",
        campos={
            "orgao": "orgao_julgador", "magistrado": "magistrado",
            "classe": "classe_judicial", "assunto": "lista_assunto",
            "jurisdicao": "jurisdicao",
        },
        texto="inteiro_teor", ementa=None, numero="nr_processo",
        data="dt_juntada", data_rotulo="juntada", ordem_data="dt_juntada",
        classe="classe_judicial",
    ),
    "pje1g": Acervo(
        chave="pje1g",
        descricao="1º grau, sentenças e decisões (PJe)",
        nome_na_pagina="1º Grau PJe",
        campos={
            "orgao": "orgao_julgador", "magistrado": "magistrado",
            "classe": "classe_judicial", "assunto": "lista_assunto",
            "comarca": "comarca",
        },
        texto="inteiro_teor", ementa=None, numero="nr_processo",
        data="dt_juntada", data_rotulo="juntada", ordem_data="dt_juntada",
        classe="classe_judicial",
    ),
    "legado": Acervo(
        chave="legado",
        descricao="2º grau, processos físicos (acervo legado)",
        nome_na_pagina="2º Grau - Físicos",
        campos={"orgao": "orgao_julgador", "magistrado": "nome_desembargador"},
        texto="conteudo_decisao_completa_html", ementa="conteudo_decisao_html",
        numero="numero_processo_legado", data="data_julgamento",
        data_rotulo="julgamento", ordem_data="data_julgamento",
        extras=("orgao_origem", "conteudo_dispositivo_decisao_html", "data_publicacao"),
    ),
    "turma_recursal_legado": Acervo(
        chave="turma_recursal_legado",
        descricao="turmas recursais dos juizados (Projudi)",
        nome_na_pagina="Turmas Recursais - Projudi",
        campos={"orgao": "orgao_julgador", "magistrado": "nome_juiz"},
        texto="cont_ementa", ementa=None, numero="num_processo",
        data="data_julgamento", data_rotulo="julgamento",
        ordem_data="data_julgamento", classe="classe_processo",
    ),
}

ORDENS = ("relevancia", "recentes", "antigos")

# Palavras que só alargam a busca quando viram termo obrigatório.
_VAZIAS = frozenset(
    "a o e as os de da do das dos em no na nos nas por para com sem que ao aos "
    "um uma se ou".split()
)
_OPERADORES = ('"', " AND ", " OR ", " NOT ", "&&", "||", "*", "~", ":", "(")
_FRASE = re.compile(r'"[^"]*"')
_FRASE_OU_PALAVRA = re.compile(r'"[^"]*"|\S+')


def compor_consulta(termo: str) -> str:
    """Junta palavras e expressões entre aspas por AND.

    Com operador (AND, OR, NOT), parênteses, curinga ou busca por campo,
    a consulta passa intacta: foi escrita pela pessoa, e é a dela que
    vale. Aspas sozinhas não contam como operador: `"dano moral" "voo"`
    sem AND seria alternativa para o índice.
    """
    limpo = (termo or "").strip()
    if not limpo or limpo == "*:*":
        return "*:*"
    sem_frases = _FRASE.sub(" ", limpo)
    if any(op in f" {sem_frases} " for op in _OPERADORES if op != '"'):
        return limpo
    partes = [
        p for p in _FRASE_OU_PALAVRA.findall(limpo)
        if p.startswith('"') or p.casefold() not in _VAZIAS
    ]
    if len(partes) < 2:
        return partes[0] if partes else limpo
    return " AND ".join(partes)


def termos_de(termo: str) -> list[str]:
    """Termos para localizar o trecho: expressões entre aspas e palavras."""
    frases = re.findall(r'"([^"]+)"', termo or "")
    resto = re.sub(r'"[^"]+"|\b(?:AND|OR|NOT)\b|\w+:', " ", termo or "")
    palavras = [
        p for p in re.findall(r"[\wÀ-ÿ]{4,}", resto)
        if p.casefold() not in _VAZIAS
    ]
    return frases + palavras


def _escapar(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace('"', '\\"')


def clausula(campo: str, valores: list[str]) -> str:
    """`campo:("v1" OR "v2")`, com o valor exato entre aspas."""
    alternativas = " OR ".join(f'"{_escapar(v)}"' for v in valores)
    return f"{campo}:({alternativas})"


# O filtro de segurança na frente da API recusa (HTTP 403) a sequência
# "parêntese fechado, AND/OR/NOT, palavra": `(a OR b) AND c` não passa, e
# `c AND (a OR b)` passa. Medido em 26/10/2026. A consulta é montada para
# não produzir essa forma, e a escrita pela pessoa é conferida antes de
# sair, com a reescrita sugerida.
_FORMA_RECUSADA = re.compile(r"\)\s*(?:AND|OR|NOT|&&|\|\|)\s*[\w\"*]", re.IGNORECASE)


class ConsultaRecusada(ValueError):
    """Consulta que o filtro do tribunal recusaria; a mensagem diz como reescrever."""


def montar(consulta: str, filtros: dict[str, list[str]]) -> tuple[str, dict[str, str]]:
    """Devolve (q, parâmetros de filtro).

    Valor único vai como parâmetro da URL, que é como a própria página do
    tribunal filtra. Vários valores para um campo (grafias diferentes da
    mesma classe, duas câmaras) só cabem na consulta, como cláusula OR, e
    a API aceita no máximo um campo assim sem cair no filtro de segurança.
    """
    params = {c: v[0] for c, v in filtros.items() if len(v) == 1}
    multiplos = {c: v for c, v in filtros.items() if len(v) > 1}
    if len(multiplos) > 1:
        raise ConsultaRecusada(
            "Só um filtro pode ter vários valores por pesquisa (a API do tribunal "
            "recusa a combinação). Deixe um valor só em: "
            + ", ".join(sorted(multiplos)[1:]) + "."
        )
    if _FORMA_RECUSADA.search(consulta):
        raise ConsultaRecusada(
            "O filtro de segurança do tribunal recusa um grupo entre parênteses "
            "seguido de AND/OR/NOT e outra palavra, como `(a OR b) AND c`. "
            "Reescreva com o grupo no fim: `c AND (a OR b)`."
        )
    if not multiplos:
        return consulta, params
    campo, valores = next(iter(multiplos.items()))
    extra = clausula(campo, valores)
    if consulta == "*:*":
        return extra, params
    # Com OR/NOT solto, a precedência precisa do agrupamento; e o grupo só
    # pode vir por último.
    if ")" in consulta or re.search(r"\b(?:OR|NOT)\b|\|\|", consulta):
        return f"{extra} AND ({consulta})", params
    return f"{consulta} AND {extra}", params


@dataclass
class Julgado:
    acervo: str
    id: str
    numero: str
    numero_original: str = ""
    classe: str = ""
    orgao: str = ""
    magistrado: str = ""
    relator_originario: str = ""
    data: str = ""
    data_rotulo: str = ""
    data_publicacao: str = ""
    assuntos: list[str] = field(default_factory=list)
    comarca: str = ""
    jurisdicao: str = ""
    orgao_origem: str = ""
    ementa: str = ""
    ementa_ausente_motivo: str = ""
    trecho: str = ""
    dispositivo: str = ""
    texto: str = ""


_VOTO_VENCEDOR = re.compile(r"VOTO\s+VENCEDOR", re.IGNORECASE)
_RELATOR_ORIGINARIO = re.compile(
    r"RELATOR(?:\(A\))?\s*(?:ORIGIN[ÁA]RIO|VENCIDO)\s*:?\s*"
    r"(?:DES(?:EMBARGADOR)?(?:\(A\))?\.?\s*)?([A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][^\n\r]{3,60})",
    re.IGNORECASE,
)
_EMENTA_VAZIA = re.compile(r"^\s*voto\s+servindo\s+(?:como|de)\s+ementa\.?\s*$", re.I)
_MARCA_EMENTA = re.compile(r"\bE\s?M\s?E\s?N\s?T\s?A\b")


def relator_originario(texto: str, redator: str) -> str:
    """Relator originário quando o acórdão tem voto vencedor; senão vazio."""
    if not texto or not _VOTO_VENCEDOR.search(texto):
        return ""
    achado = _RELATOR_ORIGINARIO.search(texto)
    if not achado:
        return ""
    nome = tx.limpar(achado.group(1))
    return "" if nome.casefold() == (redator or "").casefold() else nome


def _ementa_do_texto(texto: str, tamanho: int = 3000) -> str:
    """Bloco que começa no cabeçalho EMENTA, quando o texto o tem."""
    achado = _MARCA_EMENTA.search(texto or "")
    if not achado:
        return ""
    bloco = texto[achado.start():achado.start() + tamanho]
    corte = len(bloco) < len(texto) - achado.start()
    return bloco.strip() + (" (...)" if corte else "")


def para_julgado(
    doc: dict[str, Any], acervo: Acervo, termos: list[str], *, com_texto: bool = False,
    limite_texto: int = 60_000,
) -> Julgado:
    """Converte um documento do índice no registro comum."""
    texto = tx.limpar(doc.get(acervo.texto), paragrafos=True)
    magistrado = tx.limpar(doc.get(acervo.campos["magistrado"]))
    numero_bruto = tx.limpar(doc.get(acervo.numero))
    julgado = Julgado(
        acervo=acervo.chave,
        id=str(doc.get("id") or ""),
        numero=tx.formatar_cnj(numero_bruto),
        numero_original=numero_bruto,
        classe=tx.limpar(doc.get(acervo.classe)) if acervo.classe else "",
        orgao=tx.limpar(doc.get("orgao_julgador")),
        magistrado=magistrado,
        data=tx.data_iso(doc.get(acervo.data)),
        data_rotulo=acervo.data_rotulo,
        data_publicacao=tx.data_iso(doc.get("data_publicacao")),
        assuntos=tx.lista(doc.get("lista_assunto")),
        comarca=tx.limpar(doc.get("comarca")),
        jurisdicao=tx.limpar(doc.get("jurisdicao")),
        orgao_origem=tx.limpar(doc.get("orgao_origem")),
    )
    if acervo.chave == "pje2g":
        julgado.relator_originario = relator_originario(texto, magistrado)

    ementa = tx.limpar(doc.get(acervo.ementa), paragrafos=True) if acervo.ementa else ""
    if not ementa and acervo.chave == "turma_recursal_legado":
        ementa = _ementa_do_texto(texto)
    if ementa and _EMENTA_VAZIA.match(ementa):
        julgado.ementa_ausente_motivo = (
            'o acórdão registra "voto servindo como ementa"; segue trecho do voto'
        )
        ementa = ""
    elif not ementa:
        julgado.ementa_ausente_motivo = (
            "este acervo não tem campo de ementa"
            if not acervo.ementa else "o índice não traz ementa para este documento"
        )
    julgado.ementa = ementa

    if not ementa:
        julgado.trecho = tx.trecho(texto, termos) or texto[:900] + (
            " (...)" if len(texto) > 900 else ""
        )
    if acervo.chave in ("pje1g", "pje2g_mono"):
        julgado.dispositivo = tx.dispositivo(texto)
    elif acervo.chave == "legado":
        julgado.dispositivo = tx.limpar(doc.get("conteudo_dispositivo_decisao_html"))
    if com_texto:
        julgado.texto = texto[:limite_texto]
        if len(texto) > limite_texto:
            julgado.texto += (
                f"\n\n[inteiro teor cortado em {limite_texto:,} de "
                f"{len(texto):,} caracteres]".replace(",", ".")
            )
    return julgado


def ler_facetas(dados: dict[str, Any], acervo: Acervo) -> dict[str, list[tuple[str, int]]]:
    """Facetas da busca, por campo lógico.

    A API devolve `[valor, contagem, valor, contagem, ...]`; ler isso como
    lista de valores daria contagens no lugar de nomes.
    """
    bruto = ((dados.get("facets") or {}).get("facet_fields") or {})
    saida: dict[str, list[tuple[str, int]]] = {}
    for logico, campo in acervo.campos.items():
        valores = bruto.get(campo) or []
        pares = [
            (valores[i], valores[i + 1])
            for i in range(0, len(valores) - 1, 2)
            if isinstance(valores[i], str) and isinstance(valores[i + 1], int)
            and valores[i + 1] > 0 and valores[i].strip()
        ]
        if pares:
            saida[logico] = pares
    return saida


@dataclass
class Resultado:
    acervo: Acervo
    termo: str
    consulta: str
    q: str
    filtros: dict[str, list[str]]
    total: int
    pagina: int
    por_pagina: int
    julgados: list[Julgado]
    facetas: dict[str, list[tuple[str, int]]]
    periodo: tuple[str, str] = ("", "")
    ordem: str = "relevancia"
    repetidos: int = 0


def sem_repeticao(julgados: list[Julgado]) -> tuple[list[Julgado], int]:
    """Tira da página o documento que o índice guarda mais de uma vez.

    Acontece nas monocráticas: a mesma decisão juntada duas vezes vira
    dois registros com o mesmo texto e datas vizinhas. Fica o primeiro
    (o mais recente, quando a ordem é por data); a quantidade omitida é
    devolvida para ser declarada. Mesmo processo com texto diferente
    (acórdão e embargos) não é repetição.
    """
    vistos: set[tuple[str, str, str]] = set()
    saida = []
    for j in julgados:
        chave = (j.numero, j.classe, (j.ementa or j.trecho)[:400] + j.dispositivo[:200])
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(j)
    return saida, len(julgados) - len(saida)


class TjesClient:
    """Cliente da consulta pública. Use com `async with`."""

    def __init__(self, cliente: httpx.AsyncClient | None = None) -> None:
        self._cliente = cliente
        self._proprio = cliente is None

    async def __aenter__(self) -> TjesClient:
        if self._cliente is None:
            self._cliente = novo_cliente({"Referer": f"{BASE}/"})
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._proprio and self._cliente is not None:
            await self._cliente.aclose()
            self._cliente = None

    async def _get(self, caminho: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._cliente is not None, "TjesClient usado fora do 'async with'"
        cliente = self._cliente

        async def fazer() -> httpx.Response:
            return await cliente.get(f"{API}{caminho}", params=params)

        resposta = await com_nova_tentativa(fazer)
        return resposta.json()

    async def acervos(self) -> dict[str, dict[str, Any]]:
        """Nome, total e estado de cada acervo.

        A resposta do serviço traz também endereço interno da
        infraestrutura do tribunal, que não interessa e não circula.
        """
        bruto = await self._get("/cores", {})
        return {
            chave: {"documentos": dados.get("total_docs"), "ativo": dados.get("status") == "active"}
            for chave, dados in bruto.items() if isinstance(dados, dict)
        }

    async def buscar_bruto(
        self, acervo: Acervo, q: str, *, pagina: int = 1, por_pagina: int = 10,
        ordem: str = "relevancia", data_inicio: str = "", data_fim: str = "",
        filtros: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "core": acervo.chave, "q": q,
            "page": max(1, pagina), "per_page": max(1, min(por_pagina, 50)),
        }
        params.update(filtros or {})
        if ordem == "recentes":
            params["sort"] = f"{acervo.ordem_data} desc"
        elif ordem == "antigos":
            params["sort"] = f"{acervo.ordem_data} asc"
        if data_inicio:
            params["dataIni"] = data_inicio
        if data_fim:
            params["dataFim"] = data_fim
        return await self._get("/search", params)

    async def pesquisar(
        self, acervo_chave: str, termo: str, filtros: dict[str, list[str]] | None = None,
        *, pagina: int = 1, por_pagina: int = 10, ordem: str = "relevancia",
        data_inicio: str = "", data_fim: str = "",
    ) -> Resultado:
        acervo = ACERVOS[acervo_chave]
        filtros_campo = {
            acervo.campos[logico]: valores
            for logico, valores in (filtros or {}).items() if valores
        }
        consulta = compor_consulta(termo)
        q, params = montar(consulta, filtros_campo)
        dados = await self.buscar_bruto(
            acervo, q, pagina=pagina, por_pagina=por_pagina, ordem=ordem,
            data_inicio=data_inicio, data_fim=data_fim, filtros=params,
        )
        termos = termos_de(termo)
        julgados, repetidos = sem_repeticao(
            [para_julgado(d, acervo, termos) for d in dados.get("docs") or []]
        )
        return Resultado(
            acervo=acervo, termo=termo, consulta=consulta, q=q,
            filtros={k: v for k, v in (filtros or {}).items() if v},
            total=int(dados.get("total") or 0), pagina=pagina, por_pagina=por_pagina,
            julgados=julgados, facetas=ler_facetas(dados, acervo),
            periodo=(data_inicio, data_fim), ordem=ordem, repetidos=repetidos,
        )

    async def por_numero(self, acervo_chave: str, numero: str) -> list[Julgado]:
        """Todos os documentos do processo no acervo, com inteiro teor."""
        acervo = ACERVOS[acervo_chave]
        digitos = re.sub(r"\D", "", numero)
        if acervo.chave == "turma_recursal_legado":
            q = f"{acervo.numero}:{digitos.lstrip('0') or digitos}"
        elif acervo.chave == "legado":
            q = f'"{tx.formatar_cnj(numero)}"'
        else:
            q = f'{acervo.numero}:"{tx.formatar_cnj(numero)}"'
        dados = await self.buscar_bruto(acervo, q, por_pagina=10, ordem="recentes")
        return [
            para_julgado(d, acervo, [], com_texto=True)
            for d in dados.get("docs") or []
        ]
