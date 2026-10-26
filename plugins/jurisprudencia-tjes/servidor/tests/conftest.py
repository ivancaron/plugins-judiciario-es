"""Respostas sintéticas da API, com a forma real de cada acervo.

A forma (nomes de campo, faceta em lista alternada, número só com dígitos
nas turmas, número duplo no legado) foi copiada de respostas reais em
26/10/2026. O conteúdo é inventado: o repositório é público e não carrega
nome de parte.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

EMENTA_2G = (
    "EMENTA: APELAÇÃO CÍVEL. FORNECIMENTO DE MEDICAMENTO. TEMA 106 DO STJ.\n"
    "1. Requisitos cumulativos não demonstrados.\n2. Recurso conhecido e provido."
)
ACORDAO_2G = (
    "ESTADO DO ESPÍRITO SANTO\nPODER JUDICIÁRIO\nAPELAÇÃO CÍVEL\n"
    "VOTO VENCEDOR\nRELATOR ORIGINÁRIO: DES. JOAO EXEMPLO DA SILVA\n"
    "Acompanho a divergência quanto ao fornecimento de medicamento."
)
SENTENCA_1G = (
    "ESTADO DO ESPÍRITO SANTO\nPODER JUDICIÁRIO\nJuízo de Exemplo - Vara Única\n"
    "SENTENÇA\nTrata-se de ação de usucapião especial urbana ajuizada por "
    "PARTE AUTORA contra PARTE RÉ. É o relatório. Decido. "
    "A posse mansa e pacífica por mais de cinco anos ficou demonstrada. "
    "Ante o exposto, JULGO PROCEDENTE o pedido para declarar o domínio. "
    "Sem custas. P.R.I."
)


def doc_pje2g(**extra: Any) -> dict[str, Any]:
    base = {
        "id": "101", "nr_processo": "0000001-11.2023.8.08.0024",
        "classe_judicial": "APELAÇÃO CÍVEL", "orgao_julgador": "1ª Câmara Cível",
        "magistrado": "MARIA REDATORA EXEMPLO", "dt_juntada": "2024-03-05T18:00:00.000Z",
        "ementa": EMENTA_2G, "acordao": ACORDAO_2G,
        "lista_assunto": ["Fornecimento de medicamentos"], "jurisdicao": "Tribunal de Justiça",
    }
    base.update(extra)
    return base


def doc_pje1g() -> dict[str, Any]:
    return {
        "id": "201", "nr_processo": "0000002-22.2017.8.08.0064",
        "classe_judicial": "Procedimento Comum Cível", "comarca": "Exemplo",
        "orgao_julgador": "Juízo de Direito da Vara Única de Exemplo",
        "magistrado": "JOSE JUIZ EXEMPLO", "dt_juntada": "2026-03-27T23:39:48.346Z",
        "inteiro_teor": SENTENCA_1G, "lista_assunto": ["Usucapião Especial (Constitucional)"],
    }


def doc_legado() -> dict[str, Any]:
    return {
        "id": "abc-1", "numero_processo_legado": "048.11.009830-7 | 0009830-61.2011.8.08.0048",
        "orgao_julgador": "QUARTA CÂMARA CÍVEL ", "nome_desembargador": "ANTONIO EXEMPLO",
        "data_julgamento": "2018-03-12T03:00:00Z", "data_publicacao": ["2018-03-26T03:00:00Z"],
        "conteudo_decisao_html": "<p>EMENTA</p><p>APELAÇÃO CÍVEL. USUCAPIÃO. Recurso provido.</p>",
        "conteudo_decisao_completa_html": "<p>Inteiro teor do acórdão de usucapião.</p>",
        "conteudo_dispositivo_decisao_html": "À unanimidade: Conhecido o recurso e provido.",
        "orgao_origem": "SERRA - 5ª VARA CÍVEL",
    }


def doc_turma() -> dict[str, Any]:
    return {
        "id": "def-2", "num_processo": "134622720188080347", "classe_processo": "Recurso Inominado",
        "orgao_julgador": "2ª TURMA RECURSAL", "nome_juiz": "CARLOS JUIZ EXEMPLO",
        "data_julgamento": ["2020-02-20T15:46:10Z"],
        "cont_ementa": "COLÉGIO RECURSAL\nRECURSO INOMINADO\nE M E N T A: CONSUMIDOR. "
        "NEGATIVAÇÃO INDEVIDA. DANO MORAL CONFIGURADO.\nVOTO\nRelatório dispensado.",
    }


def resposta_busca(docs: list[dict[str, Any]], total: int | None = None,
                   facetas: dict[str, list[Any]] | None = None) -> dict[str, Any]:
    return {
        "docs": docs, "total": len(docs) if total is None else total,
        "page": 1, "per_page": 10, "total_pages": 1, "core_used": "pje2g",
        "facets": {"facet_fields": facetas or {}},
    }


FACETAS_2G = {
    "orgao_julgador": ["1ª Câmara Cível", 28314, "4ª Câmara Cível", 25953, "2ª Câmara Criminal", 9000],
    "magistrado": ["MARIA REDATORA EXEMPLO", 500, "PAULO EXEMPLO ABIB", 300],
    "classe_judicial": ["APELAÇÃO CÍVEL", 61368, "Apelação Cível", 1200, "AGRAVO DE INSTRUMENTO", 38934],
    "lista_assunto": ["Fornecimento de medicamentos", 1453],
    "jurisdicao": ["Tribunal de Justiça", 154118, "Turma Recursal", 84777],
}


@pytest.fixture
def transporte(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[httpx.Request]]:
    """Troca a rede por um manipulador; devolve a lista de requisições feitas."""

    def instalar(manipulador: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
        feitas: list[httpx.Request] = []

        def registrar(req: httpx.Request) -> httpx.Response:
            feitas.append(req)
            return manipulador(req)

        def novo(headers: dict[str, str] | None = None) -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=httpx.MockTransport(registrar), headers=headers)

        monkeypatch.setattr("tjes_juris_mcp.tjes.novo_cliente", novo)
        monkeypatch.setattr("tjes_juris_mcp.bnp.novo_cliente", novo)
        return feitas

    return instalar
