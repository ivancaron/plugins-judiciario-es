import httpx
from conftest import FACETAS_2G, resposta_busca

from tjes_juris_mcp.resolver import _casa, _escolher, _tokens, resolver
from tjes_juris_mcp.tjes import TjesClient


def test_tokens_tiram_tratamento_e_expandem_abreviacao():
    assert _tokens("Des. Paulo Abib") == ["paulo", "abib"]
    assert _tokens("1a CC") == ["1", "camara", "civel"]


def test_casa_distingue_igualdade_de_contencao():
    assert _casa(_tokens("primeira câmara cível"), "1ª Câmara Cível") == 2
    assert _casa(_tokens("1ª câmara"), "1ª Câmara Cível") == 1
    assert _casa(_tokens("1ª câmara"), "4ª Câmara Cível") == 0
    assert _casa(_tokens("apela"), "APELAÇÃO CÍVEL") == 1


def test_grafias_do_mesmo_valor_resolvem_juntas():
    pares = [("APELAÇÃO CÍVEL", 61368), ("Apelação Cível", 1200), ("AGRAVO DE INSTRUMENTO", 3)]
    r = _escolher("classe", _tokens("apelação cível"), pares)
    assert r.situacao == "resolvido"
    assert r.valores == ["APELAÇÃO CÍVEL", "Apelação Cível"]


def test_valores_distintos_ficam_ambiguos_por_contagem():
    pares = [("1ª Câmara Cível", 10), ("1ª Câmara Criminal", 30)]
    r = _escolher("orgao", _tokens("1ª câmara"), pares)
    assert r.situacao == "ambiguo"
    assert [v for v, _ in r.candidatos] == ["1ª Câmara Criminal", "1ª Câmara Cível"]


def test_espaco_na_ponta_do_valor_e_preservado():
    r = _escolher("orgao", _tokens("quarta câmara cível"), [("QUARTA CÂMARA CÍVEL ", 5)])
    assert r.valores == ["QUARTA CÂMARA CÍVEL "]


async def test_resolver_usa_facetas_e_deduz_o_campo(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([], 0, FACETAS_2G)))
    async with TjesClient() as cliente:
        r = await resolver(cliente, "pje2g", "1ª câmara cível")
    assert r[0].campo == "orgao" and r[0].valores == ["1ª Câmara Cível"]


async def test_resolver_cai_no_curinga_quando_o_nome_nao_esta_nas_facetas(transporte):
    def manipulador(req: httpx.Request) -> httpx.Response:
        q = req.url.params["q"]
        if "magistrado:(" in q:
            return httpx.Response(200, json=resposta_busca([], 7, {"magistrado": ["ANA RARA DE SOUZA", 7]}))
        return httpx.Response(200, json=resposta_busca([], 0, FACETAS_2G))

    feitas = transporte(manipulador)
    async with TjesClient() as cliente:
        r = await resolver(cliente, "pje2g", "des. Ana Rara", termo="medicamento")
    assert r[0].situacao == "resolvido" and r[0].valores == ["ANA RARA DE SOUZA"]
    curinga = [f.url.params["q"] for f in feitas if "magistrado:(" in f.url.params["q"]][0]
    assert curinga.startswith("medicamento AND magistrado:(")
    assert "*RARA*" in curinga


async def test_campo_que_o_acervo_nao_tem(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([])))
    async with TjesClient() as cliente:
        r = await resolver(cliente, "legado", "Vitória", campo="comarca")
    assert r[0].situacao == "campo_indisponivel"
