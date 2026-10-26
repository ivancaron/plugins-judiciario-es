"""Precedentes qualificados do TJES no Banco Nacional de Precedentes (CNJ).

A API do BNP (`pangeabnp.pdpj.jus.br/api/v1`) é pública, sem autenticação
e não documentada. Para o TJES o conjunto é pequeno (169 registros em
26/10/2026: IRDR, IAC, súmulas e notas técnicas), então o cliente baixa o
conjunto inteiro uma vez por sessão e filtra aqui, sem acento e sem caixa.
Isso é mais previsível que a busca do próprio BNP, que ranqueia por
relevância e às vezes deixa de fora o que só casa na questão submetida.

A situação vem literal da fonte e nunca é suavizada. "Não admitido",
"Superado", "Revisado" e "Cancelado" são situações em que o enunciado
não vincula como está, e saem em seção própria.
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from tjes_juris_mcp import texto as tx
from tjes_juris_mcp.http import com_nova_tentativa, novo_cliente

API = "https://pangeabnp.pdpj.jus.br/api/v1"
PORTAL = "https://bnp.pdpj.jus.br/"
TIPOS = ("IRDR", "IAC", "SIRDR", "SUM", "NT", "ENU", "OJ")
NOMES = {
    "IRDR": "Incidente de Resolução de Demandas Repetitivas",
    "SIRDR": "Suspensão em IRDR",
    "IAC": "Incidente de Assunção de Competência",
    "SUM": "Súmula",
    "NT": "Nota técnica",
    "ENU": "Enunciado",
    "OJ": "Orientação jurisprudencial",
}
VINCULANTES = frozenset({"IRDR", "IAC", "SUM"})
_SEM_FORCA = ("nao admitid", "cancelad", "superad", "revogad", "revisad", "inadmitid")
_PLACEBOS = frozenset({"", "nao informado", "nao informada", "sem tese", "-", "n/a"})
_CACHE_SEGUNDOS = 6 * 3600


def _limpar_html(valor: object) -> str:
    if not valor:
        return ""
    texto = re.sub(r"(?i)<\s*(?:br|/p|/div|/li)\s*/?>", "\n", str(valor))
    texto = html.unescape(re.sub(r"<[^>]+>", "", texto)).replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


@dataclass
class Precedente:
    id: str
    tipo: str
    nr: int
    situacao: str
    tese: str
    questao: str
    atualizacao: str
    paradigmas: list[dict[str, Any]] = field(default_factory=list)

    @property
    def identificacao(self) -> str:
        return f"{self.tipo} {self.nr}/TJES"

    @property
    def sem_forca(self) -> bool:
        s = tx.sem_acentos(self.situacao).casefold()
        return any(m in s for m in _SEM_FORCA)

    @property
    def link(self) -> tuple[str, str]:
        """(endereço, observação). Endereço vazio quando não há."""
        for p in self.paradigmas:
            url = str((p or {}).get("link") or "")
            if url.startswith("http"):
                return url, "consulta do processo que originou o precedente"
        numeros = [str((p or {}).get("numero") or "") for p in self.paradigmas]
        numeros = [n for n in numeros if n]
        if numeros:
            return "", (
                "o BNP não traz endereço; consulte o processo "
                + ", ".join(numeros) + " no PJe do 2º grau"
            )
        return "", "o BNP não traz endereço; confira pelo portal " + PORTAL


def para_precedente(d: dict[str, Any]) -> Precedente | None:
    try:
        nr = int(d.get("nr"))
    except (TypeError, ValueError):
        return None
    tipo = str(d.get("tipo") or "").upper().strip()
    if not tipo or str(d.get("orgao") or "").upper() != "TJES":
        return None
    tese = _limpar_html(d.get("tese"))
    questao = _limpar_html(d.get("questao"))
    if tx.sem_acentos(tese).casefold().strip(" .") in _PLACEBOS:
        tese = ""
    if not tese and tipo == "SUM" and questao:
        # Nas súmulas o BNP grava o enunciado em `questao`.
        tese, questao = questao, ""
    paradigmas = d.get("processosParadigma")
    return Precedente(
        id=str(d.get("id") or ""), tipo=tipo, nr=nr,
        situacao=str(d.get("situacao") or "").strip(),
        tese=tese, questao=questao,
        atualizacao=str(d.get("ultimaAtualizacao") or ""),
        paradigmas=paradigmas if isinstance(paradigmas, list) else [],
    )


class BnpClient:
    """Baixa os precedentes do TJES e guarda por algumas horas."""

    _cache: tuple[float, list[Precedente]] | None = None

    def __init__(self, cliente: httpx.AsyncClient | None = None) -> None:
        self._cliente = cliente

    async def _pagina(self, cliente: httpx.AsyncClient, pagina: int) -> dict[str, Any]:
        corpo = {"filtro": {
            "buscaGeral": "", "todasPalavras": "", "quaisquerPalavras": "",
            "semPalavras": "", "trechoExato": "", "atualizacaoDesde": "",
            "atualizacaoAte": "", "cancelados": True, "ordenacao": "Text", "nr": "",
            "pagina": pagina, "tamanhoPagina": 100,
            "orgaos": ["TJES"], "tipos": list(TIPOS),
        }}

        async def fazer() -> httpx.Response:
            return await cliente.post(f"{API}/precedentes", json=corpo)

        return (await com_nova_tentativa(fazer)).json()

    async def todos(self) -> list[Precedente]:
        agora = time.monotonic()
        if BnpClient._cache and agora - BnpClient._cache[0] < _CACHE_SEGUNDOS:
            return BnpClient._cache[1]
        cliente = self._cliente or novo_cliente({"Content-Type": "application/json"})
        try:
            itens: list[dict[str, Any]] = []
            for pagina in range(1, 11):
                resposta = await self._pagina(cliente, pagina)
                lote = resposta.get("resultados") or []
                itens.extend(lote)
                if not lote or len(itens) >= int(resposta.get("total") or 0):
                    break
        finally:
            if self._cliente is None:
                await cliente.aclose()
        precedentes = [p for p in (para_precedente(i) for i in itens) if p]
        precedentes.sort(key=lambda p: (TIPOS.index(p.tipo) if p.tipo in TIPOS else 99, p.nr))
        BnpClient._cache = (agora, precedentes)
        return precedentes


def filtrar(precedentes: list[Precedente], termo: str, tipos: list[str] | None = None) -> list[Precedente]:
    """Todos os termos têm de aparecer na tese ou na questão (sem acento).

    Expressão entre aspas conta como um termo só. Termo vazio devolve
    todos os do tipo pedido.
    """
    frases = re.findall(r'"([^"]+)"', termo or "")
    resto = re.sub(r'"[^"]+"', " ", termo or "")
    palavras = [tx.normalizar(p) for p in resto.split() if len(p) >= 4]
    # Plural simples: "medicamentos" precisa achar "medicamento".
    palavras = [p[:-1] if len(p) >= 5 and p.endswith("s") else p for p in palavras]
    termos = [tx.normalizar(f) for f in frases] + palavras
    saida = []
    for p in precedentes:
        if tipos and p.tipo not in tipos:
            continue
        alvo = tx.normalizar(f"{p.tese} {p.questao}")
        if all(t in alvo for t in termos):
            saida.append(p)
    return saida
