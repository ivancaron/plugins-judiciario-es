"""Do que a pessoa digitou ao valor exato que o índice guarda.

"1ª câmara cível", "primeira câmara cível" e "1a CC" precisam chegar a
"1ª Câmara Cível"; "des. Fulano" precisa chegar ao nome completo em caixa
alta; "apelação" precisa chegar às duas grafias que convivem no índice
("APELAÇÃO CÍVEL" e "Apelação Cível"). Sem isto, filtro devolve zero e
parece que não há jurisprudência.

Dois caminhos, nesta ordem:

1. as facetas do acervo inteiro (até cem valores por campo), comparadas
   sem acento, sem caixa e com ordinais normalizados;
2. quando o valor não está entre os cem, a busca por campo com curinga
   (`magistrado:*ABIB*`), que devolve as facetas só do que casa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from tjes_juris_mcp import texto as tx
from tjes_juris_mcp.tjes import ACERVOS, Acervo, TjesClient, compor_consulta, ler_facetas

# Palavras de tratamento ou genéricas que não identificam o valor.
_RUIDO = frozenset(
    "des desa desembargador desembargadora juiz juiza dr dra doutor doutora "
    "relator relatora exmo exma o a de da do dos das e".split()
)
_PISTAS_ORGAO = re.compile(
    r"\b(camara|camaras|grupo|turma|pleno|plenario|reunidas|vara|juizo|juizado|"
    r"colegio|tribunal|cc|cr)\b"
)
_PISTAS_MAGISTRADO = re.compile(r"\b(des|desa|desembargador|desembargadora|juiz|juiza|dr|dra)\b")

# Abreviações correntes de órgão.
_ABREVIACOES = {"cc": "camara civel", "ccrim": "camara criminal", "ccr": "camara criminal"}


@dataclass
class Resolucao:
    campo: str
    texto: str
    situacao: str  # resolvido | ambiguo | sem_casamento | campo_indisponivel
    valores: list[str] = field(default_factory=list)
    candidatos: list[tuple[str, int]] = field(default_factory=list)


def _tokens(texto: str) -> list[str]:
    base = tx.normalizar(texto)
    for abrev, extenso in _ABREVIACOES.items():
        base = re.sub(rf"\b{abrev}\b", extenso, base)
    return [t for t in base.split() if t not in _RUIDO]


def _casa(tokens: list[str], valor: str) -> int:
    """0 = não casa; 1 = todos os tokens contidos; 2 = igualdade."""
    alvo = tx.normalizar(valor)
    alvo_palavras = alvo.split()
    if not tokens:
        return 0
    if " ".join(tokens) == " ".join(t for t in alvo_palavras if t not in _RUIDO):
        return 2
    for t in tokens:
        if t.isdigit():
            if t not in alvo_palavras:
                return 0
        elif not any(p.startswith(t) for p in alvo_palavras):
            return 0
    return 1


def _escolher(campo: str, tokens: list[str], pares: list[tuple[str, int]]) -> Resolucao:
    exatos = [(v, c) for v, c in pares if _casa(tokens, v) == 2]
    contidos = [(v, c) for v, c in pares if _casa(tokens, v) == 1]
    if exatos:
        # Grafias que só diferem por caixa, acento ou espaço são o mesmo valor.
        return Resolucao(campo, "", "resolvido", [v for v, _ in exatos], exatos)
    if not contidos:
        return Resolucao(campo, "", "sem_casamento")
    formas = {tx.normalizar(v) for v, _ in contidos}
    if len(formas) == 1:
        return Resolucao(campo, "", "resolvido", [v for v, _ in contidos], contidos)
    contidos.sort(key=lambda p: -p[1])
    return Resolucao(campo, "", "ambiguo", [], contidos)


def _curinga(campo_indice: str, tokens: list[str], texto_original: str) -> str:
    """`campo:(*ABIB* OR *Abib* ...)` com a palavra mais longa do texto.

    Uma palavra só: duas cláusulas encadeadas (`...) AND campo:...`) caem
    no filtro de segurança do tribunal. As demais palavras são conferidas
    aqui, na escolha do candidato. O índice compara curinga com caixa e
    acento, então a palavra vai nas formas em que o tribunal costuma
    gravar: caixa alta com e sem acento, e a forma de título.
    """
    originais = {tx.normalizar(p): p for p in re.findall(r"[\wÀ-ÿ]+", texto_original)}
    uteis = [t for t in tokens if len(t) >= 3 and not t.isdigit()]
    if not uteis:
        return ""
    palavra = originais.get(max(uteis, key=len), max(uteis, key=len))
    formas = {
        palavra.upper(), tx.sem_acentos(palavra).upper(),
        palavra.capitalize(), tx.sem_acentos(palavra).capitalize(), palavra.lower(),
    }
    alternativas = " OR ".join(f"*{f}*" for f in sorted(formas) if re.fullmatch(r"[\wÀ-ÿ]+", f))
    return f"{campo_indice}:({alternativas})"


async def resolver(
    cliente: TjesClient, acervo_chave: str, texto: str, campo: str | None = None,
    termo: str = "",
) -> list[Resolucao]:
    """Resolve o texto num campo dado ou, sem campo, nos plausíveis.

    Com `termo`, as contagens dos candidatos são as do tema pesquisado, que
    é o que interessa para escolher; o acervo inteiro é a segunda fonte.
    """
    acervo: Acervo = ACERVOS[acervo_chave]
    tokens = _tokens(texto)
    if campo:
        candidatos = [campo]
    else:
        normal = tx.normalizar(texto)
        if _PISTAS_ORGAO.search(normal):
            candidatos = ["orgao"]
        elif _PISTAS_MAGISTRADO.search(normal):
            candidatos = ["magistrado"]
        else:
            candidatos = ["classe", "orgao", "comarca", "assunto", "magistrado"]
    candidatos = [c for c in candidatos if c in acervo.campos] or (
        [campo] if campo else []
    )
    if campo and campo not in acervo.campos:
        return [Resolucao(campo, texto, "campo_indisponivel")]

    fontes = [compor_consulta(termo)] if termo.strip() else []
    fontes.append("*:*")
    facetas_por_fonte = []
    for q in fontes:
        dados = await cliente.buscar_bruto(acervo, q, por_pagina=1)
        facetas_por_fonte.append(ler_facetas(dados, acervo))

    saida: list[Resolucao] = []
    for logico in candidatos:
        r = Resolucao(logico, texto, "sem_casamento")
        for facetas in facetas_por_fonte:
            r = _escolher(logico, tokens, facetas.get(logico, []))
            if r.situacao != "sem_casamento":
                break
        if r.situacao == "sem_casamento":
            q = _curinga(acervo.campos[logico], tokens, texto)
            if q:
                base = compor_consulta(termo) if termo.strip() else "*:*"
                if base != "*:*":
                    q = f"{q} AND ({base})" if ")" in base else f"{base} AND {q}"
                dados = await cliente.buscar_bruto(acervo, q, por_pagina=1)
                r = _escolher(logico, tokens, ler_facetas(dados, acervo).get(logico, []))
        r.texto = texto
        if r.situacao != "sem_casamento" or campo:
            saida.append(r)
        if r.situacao == "resolvido" and not campo:
            break
    return saida or [Resolucao(campo or "?", texto, "sem_casamento")]
