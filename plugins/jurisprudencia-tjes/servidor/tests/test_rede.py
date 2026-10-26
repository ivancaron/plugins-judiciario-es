"""Contra as APIs reais. Fora da suíte padrão: `uv run pytest -m rede`.

Servem para notar quando o tribunal muda o contrato (nome de campo,
forma da faceta, regra do filtro de segurança), o que nenhum teste
offline pega.
"""
import pytest

from tjes_juris_mcp import bnp
from tjes_juris_mcp.resolver import resolver
from tjes_juris_mcp.tjes import ACERVOS, TjesClient

pytestmark = pytest.mark.rede


async def test_cinco_acervos_ativos():
    async with TjesClient() as cliente:
        estado = await cliente.acervos()
    assert set(ACERVOS) <= set(estado)
    assert all(estado[c]["ativo"] for c in ACERVOS)


async def test_filtro_por_parametro_bate_com_a_faceta():
    async with TjesClient() as cliente:
        geral = await cliente.pesquisar("pje2g", "fornecimento medicamento")
        faceta = dict(geral.facetas["orgao"])["1ª Câmara Cível"]
        filtrado = await cliente.pesquisar("pje2g", "fornecimento medicamento", {"orgao": ["1ª Câmara Cível"]})
    assert filtrado.total == faceta


async def test_varios_valores_somam_e_passam_pelo_filtro_de_seguranca():
    async with TjesClient() as cliente:
        um = await cliente.pesquisar("pje2g", "medicamento", {"orgao": ["1ª Câmara Cível"]})
        dois = await cliente.pesquisar("pje2g", "medicamento", {"orgao": ["2ª Câmara Cível"]})
        ambos = await cliente.pesquisar("pje2g", "medicamento", {"orgao": ["1ª Câmara Cível", "2ª Câmara Cível"]})
        com_or = await cliente.pesquisar("pje2g", "medicamento OR remédio", {"orgao": ["1ª Câmara Cível", "2ª Câmara Cível"]})
    assert ambos.total == um.total + dois.total
    assert com_or.total >= ambos.total


@pytest.mark.parametrize("acervo", list(ACERVOS))
async def test_cada_acervo_devolve_julgado_com_numero_e_data(acervo):
    async with TjesClient() as cliente:
        r = await cliente.pesquisar(acervo, "dano moral", por_pagina=2)
    assert r.total > 0
    j = r.julgados[0]
    assert j.numero and j.data and (j.ementa or j.trecho)


async def test_resolvedor_acha_camara_e_magistrado():
    async with TjesClient() as cliente:
        camara = await resolver(cliente, "pje2g", "primeira câmara cível")
        legado = await resolver(cliente, "legado", "quarta câmara cível")
    assert camara[0].valores == ["1ª Câmara Cível"]
    assert legado[0].situacao == "resolvido" and legado[0].valores[0].startswith("QUARTA")


async def test_bnp_traz_irdr_do_tjes():
    bnp.BnpClient._cache = None
    todos = await bnp.BnpClient().todos()
    assert any(p.tipo == "IRDR" for p in todos)
