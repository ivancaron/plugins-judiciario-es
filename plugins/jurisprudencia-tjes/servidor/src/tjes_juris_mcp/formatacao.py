"""Saída das tools em Markdown, pronta para o modelo apresentar.

O texto do tribunal vai sempre em bloco de citação e sem retoque. Os
rótulos dizem o que cada dado é, e o que ele não é: a data do PJe é de
juntada, não da sessão; o magistrado do acórdão é o redator do voto
vencedor; a página pública não abre o julgado por endereço.
"""
from __future__ import annotations

from tjes_juris_mcp import bnp
from tjes_juris_mcp.resolver import Resolucao
from tjes_juris_mcp.tjes import ACERVOS, BASE, ROTULOS, Julgado, Resultado

ORDEM_ROTULO = {
    "relevancia": "relevância",
    "recentes": "mais recentes primeiro",
    "antigos": "mais antigos primeiro",
}


def _n(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _citacao(texto: str) -> str:
    return "\n".join(f"> {linha}" if linha else ">" for linha in texto.splitlines())


def conferencia(julgado: Julgado) -> str:
    acervo = ACERVOS[julgado.acervo]
    numero = julgado.numero or julgado.numero_original
    return (
        f"consulta pública ({BASE}/), aba \"{acervo.nome_na_pagina}\", "
        f"\"Busca Exata\" ligada, pesquisar `{numero}`. A página não abre "
        "o julgado por endereço direto."
    )


def card(posicao: int, j: Julgado) -> str:
    titulo = " ".join(p for p in (j.classe, j.numero or j.numero_original) if p)
    linhas = [f"### [{posicao}] {titulo or 'documento sem identificação'}", ""]
    if j.orgao:
        linhas.append(f"- **Órgão julgador:** {j.orgao}")
    if j.magistrado:
        rotulo = "Redator do acórdão (campo do índice)" if j.acervo == "pje2g" else "Magistrado"
        linhas.append(f"- **{rotulo}:** {j.magistrado}")
    if j.relator_originario:
        linhas.append(
            f"- **Relator originário, vencido:** {j.relator_originario} "
            "(houve divergência; o texto do acórdão diz quem ficou vencido)"
        )
    if j.data:
        aviso = " (não é a data da sessão; confirme no PJe)" if j.data_rotulo == "juntada" else ""
        linhas.append(f"- **Data de {j.data_rotulo}:** {j.data}{aviso}")
    if j.data_publicacao:
        linhas.append(f"- **Data de publicação:** {j.data_publicacao}")
    if j.comarca:
        linhas.append(f"- **Comarca:** {j.comarca}")
    if j.orgao_origem:
        linhas.append(f"- **Origem:** {j.orgao_origem}")
    if j.jurisdicao and j.jurisdicao != "Tribunal de Justiça":
        linhas.append(f"- **Jurisdição:** {j.jurisdicao}")
    if j.assuntos:
        linhas.append(f"- **Assuntos:** {'; '.join(j.assuntos)}")
    if j.numero_original and j.numero_original != j.numero:
        linhas.append(f"- **Número no índice:** {j.numero_original}")
    linhas.append(f"- **Conferência:** {conferencia(j)}")
    linhas.append("")
    if j.ementa:
        linhas += ["**Ementa (literal, como está no índice):**", "", _citacao(j.ementa), ""]
    else:
        if j.ementa_ausente_motivo:
            linhas.append(f"*Sem ementa: {j.ementa_ausente_motivo}.*")
            linhas.append("")
        if j.trecho:
            linhas += [
                "**Trecho literal do inteiro teor (recorte automático em torno do termo):**",
                "", _citacao(j.trecho), "",
            ]
    if j.dispositivo:
        linhas += ["**Dispositivo (trecho literal):**", "", _citacao(j.dispositivo), ""]
    return "\n".join(linhas)


def tabela_facetas(facetas: dict[str, list[tuple[str, int]]], limite: int = 10) -> str:
    blocos = []
    for logico in ROTULOS:
        pares = facetas.get(logico) or []
        if len(pares) < 2:
            continue
        linhas = [
            f"**{ROTULOS[logico]}** (`{logico}`)", "",
            "| Valor exato no índice | Documentos |", "|---|---|",
        ]
        linhas += [f"| `{v}` | {_n(c)} |" for v, c in pares[:limite]]
        if len(pares) > limite:
            linhas.append(f"| … mais {len(pares) - limite} valores | |")
        blocos.append("\n".join(linhas))
    return "\n\n".join(blocos)


def resultado(r: Resultado) -> str:
    total_paginas = max(1, -(-r.total // r.por_pagina)) if r.total else 0
    linhas = [
        f"# TJES · {r.acervo.descricao}",
        "",
        f"- **Termo:** {r.termo}",
        f"- **Consulta executada:** `{r.q}`",
    ]
    if r.filtros:
        aplicados = "; ".join(
            f"{ROTULOS.get(c, c)} = " + " ou ".join(f"`{v}`" for v in vs)
            for c, vs in r.filtros.items()
        )
        linhas.append(f"- **Filtros:** {aplicados}")
    if any(r.periodo):
        linhas.append(
            f"- **Período ({r.acervo.data_rotulo}):** {r.periodo[0] or 'início'} a {r.periodo[1] or 'hoje'}"
        )
    linhas.append(f"- **Ordenação:** {ORDEM_ROTULO.get(r.ordem, r.ordem)}")
    linhas.append(
        f"- **Documentos que casam:** {_n(r.total)} · exibidos {len(r.julgados)} "
        f"(página {r.pagina} de {_n(total_paginas)})"
    )
    if r.repetidos:
        linhas.append(
            f"- **Registros repetidos omitidos nesta página:** {r.repetidos} (mesmo "
            "processo e mesmo texto juntados mais de uma vez; o total acima conta "
            "registros, não processos)"
        )
    linhas.append("")
    if not r.julgados:
        linhas.append(
            "Nenhum documento casa com esta consulta neste acervo. Isso diz respeito "
            "a este acervo e a esta consulta: outro acervo, outra grafia ou menos "
            "filtros podem trazer resultado."
        )
        return "\n".join(linhas)

    facetas = tabela_facetas(r.facetas)
    if facetas:
        linhas += [
            "## Distribuição do resultado (contagem do índice)",
            "",
            "Para estreitar, repita a pesquisa com um destes valores, copiado "
            "exatamente como aparece.",
            "",
            facetas,
            "",
        ]
    linhas += ["## Julgados", ""]
    inicio = (r.pagina - 1) * r.por_pagina
    linhas += [card(inicio + i + 1, j) for i, j in enumerate(r.julgados)]
    return "\n".join(linhas)


def resolucoes(lista: list[Resolucao], acervo_chave: str) -> str:
    acervo = ACERVOS[acervo_chave]
    linhas = [f"# Resolução de filtro · {acervo.descricao}", ""]
    for r in lista:
        rotulo = ROTULOS.get(r.campo, r.campo)
        if r.situacao == "campo_indisponivel":
            disponiveis = ", ".join(f"`{c}`" for c in acervo.campos)
            linhas.append(
                f"- **{rotulo}:** este acervo não tem esse campo. Campos disponíveis: {disponiveis}."
            )
            continue
        if r.situacao == "sem_casamento":
            linhas.append(f"- **{rotulo}:** nenhum valor do índice corresponde a \"{r.texto}\".")
            continue
        if r.situacao == "resolvido":
            valores = " · ".join(f"`{v}`" for v in r.valores)
            linhas.append(f"- **{rotulo}:** resolvido para {valores}")
            if len(r.valores) > 1:
                linhas.append(
                    "  (grafias diferentes do mesmo valor no índice; passe todas no filtro)"
                )
            continue
        linhas.append(f"- **{rotulo}:** ambíguo. Candidatos (documentos):")
        linhas += [f"  - `{v}` ({_n(c)})" for v, c in r.candidatos[:15]]
    linhas += [
        "",
        f"Use o valor no parâmetro `{lista[0].campo if lista else 'campo'}` de "
        "`tjes_pesquisar`, exatamente como está entre crases.",
    ]
    return "\n".join(linhas)


def inteiro_teor(julgados: list[Julgado], numero: str, acervo_chave: str, posicao: int) -> str:
    acervo = ACERVOS[acervo_chave]
    if not julgados:
        return (
            f"Nenhum documento do processo `{numero}` no acervo {acervo.descricao}. "
            "O processo pode estar em outro acervo (1º grau, monocráticas, legado, turmas)."
        )
    posicao = max(1, min(posicao, len(julgados)))
    escolhido = julgados[posicao - 1]
    linhas = [f"# Inteiro teor · {acervo.descricao}", ""]
    if len(julgados) > 1:
        linhas.append(f"O processo tem {len(julgados)} documentos neste acervo (mais recente primeiro):")
        for i, j in enumerate(julgados, 1):
            marca = " ← exibido" if i == posicao else ""
            linhas.append(f"{i}. {j.classe} · {j.orgao} · {j.data_rotulo} {j.data}{marca}")
        linhas.append("")
    linhas.append(card(posicao, escolhido))
    linhas += [
        "**Inteiro teor (literal, sem a marcação HTML):**", "",
        _citacao(escolhido.texto or "(vazio no índice)"),
    ]
    return "\n".join(linhas)


def precedentes(lista: list[bnp.Precedente], termo: str, total_base: int) -> str:
    linhas = [
        "# Precedentes qualificados do TJES (Banco Nacional de Precedentes, CNJ)",
        "",
        f"- **Termo:** {termo or '(todos)'}",
        f"- **Registros do TJES no BNP:** {total_base} · **casam com o termo:** {len(lista)}",
        "",
    ]
    if not lista:
        linhas.append(
            "Nenhum IRDR, IAC, súmula ou nota técnica do TJES no BNP casa com o termo. "
            "Isso não exclui precedente de tribunal superior sobre o tema, que esta "
            "ferramenta não consulta."
        )
        return "\n".join(linhas)
    com_forca = [p for p in lista if not p.sem_forca and p.tipo in bnp.VINCULANTES]
    outros = [p for p in lista if not p.sem_forca and p.tipo not in bnp.VINCULANTES]
    sem_forca = [p for p in lista if p.sem_forca]
    for titulo, grupo in (
        ("## Com força de precedente (art. 927 do CPC)", com_forca),
        ("## Sem efeito vinculante (notas técnicas e similares)", outros),
        ("## Não admitidos, superados, revisados ou cancelados: não citar como vigentes", sem_forca),
    ):
        if not grupo:
            continue
        linhas += [titulo, ""]
        for p in grupo:
            url, obs = p.link
            linhas.append(f"### {p.identificacao} · {bnp.NOMES.get(p.tipo, p.tipo)}")
            linhas.append("")
            linhas.append(f"- **Situação (literal do BNP):** {p.situacao or 'não informada'}")
            if p.atualizacao:
                linhas.append(f"- **Última atualização no BNP:** {p.atualizacao}")
            linhas.append(f"- **Inteiro teor:** {url + ' (' + obs + ')' if url else obs}")
            linhas.append("")
            if p.questao:
                linhas += ["**Questão submetida (literal):**", "", _citacao(p.questao), ""]
            if p.tese:
                linhas += ["**Tese ou enunciado (literal):**", "", _citacao(p.tese), ""]
            else:
                linhas += ["*O BNP não traz tese fixada para este registro.*", ""]
    return "\n".join(linhas)


def acervos(estado: dict[str, dict]) -> str:
    linhas = [
        "# Acervos da consulta pública do TJES", "",
        "| Acervo | Chave | Documentos | Ativo |", "|---|---|---|---|",
    ]
    for chave, acervo in ACERVOS.items():
        e = estado.get(chave, {})
        docs = e.get("documentos")
        linhas.append(
            f"| {acervo.descricao} | `{chave}` | {_n(docs) if isinstance(docs, int) else '?'} | "
            f"{'sim' if e.get('ativo') else 'não'} |"
        )
    linhas += ["", "Filtros por acervo:"]
    for chave, acervo in ACERVOS.items():
        linhas.append(f"- `{chave}`: " + ", ".join(f"`{c}`" for c in acervo.campos))
    return "\n".join(linhas)
