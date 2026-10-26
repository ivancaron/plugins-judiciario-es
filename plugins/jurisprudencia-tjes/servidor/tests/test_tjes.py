import httpx
import pytest
from conftest import (
    FACETAS_2G,
    doc_legado,
    doc_pje1g,
    doc_pje2g,
    doc_turma,
    resposta_busca,
)

from tjes_juris_mcp.tjes import (
    ACERVOS,
    ConsultaRecusada,
    TjesClient,
    compor_consulta,
    ler_facetas,
    montar,
    para_julgado,
    termos_de,
)


class TestComporConsulta:
    def test_palavras_soltas_viram_and_sem_palavras_vazias(self):
        assert compor_consulta("fornecimento de medicamento") == "fornecimento AND medicamento"

    def test_consulta_escrita_pela_pessoa_passa_intacta(self):
        assert compor_consulta('"tráfico privilegiado"') == '"tráfico privilegiado"'
        assert compor_consulta("a OR b") == "a OR b"
        assert compor_consulta('"dano moral" OR "voo"') == '"dano moral" OR "voo"'
        assert compor_consulta("magistrado:*ABIB*") == "magistrado:*ABIB*"

    def test_expressoes_entre_aspas_sem_operador_viram_and(self):
        assert compor_consulta('"dano moral" "atraso de voo" de') == '"dano moral" AND "atraso de voo"'
        assert compor_consulta('"fornecimento de medicamento" SUS') == '"fornecimento de medicamento" AND SUS'
        assert compor_consulta('"art. 33, § 4º"') == '"art. 33, § 4º"'

    def test_vazio_vira_tudo(self):
        assert compor_consulta("  ") == "*:*"

    def test_termos_para_trecho(self):
        assert termos_de('"tráfico privilegiado" redutor AND pena') == ["tráfico privilegiado", "redutor", "pena"]


class TestMontar:
    def test_valor_unico_vai_como_parametro(self):
        q, params = montar("a AND b", {"orgao_julgador": ["1ª Câmara Cível"]})
        assert q == "a AND b"
        assert params == {"orgao_julgador": "1ª Câmara Cível"}

    def test_varios_valores_viram_clausula_no_fim(self):
        q, params = montar("a AND b", {"classe_judicial": ["APELAÇÃO CÍVEL", "Apelação Cível"]})
        assert q == 'a AND b AND classe_judicial:("APELAÇÃO CÍVEL" OR "Apelação Cível")'
        assert params == {}

    def test_com_or_a_clausula_vem_antes_e_o_termo_agrupado_por_ultimo(self):
        q, _ = montar('"x y" OR z', {"orgao_julgador": ["A", "B"]})
        assert q == 'orgao_julgador:("A" OR "B") AND ("x y" OR z)'

    def test_forma_que_o_tribunal_recusa_nao_sai(self):
        with pytest.raises(ConsultaRecusada, match="grupo no fim"):
            montar("(a OR b) AND c", {})

    def test_dois_campos_com_varios_valores_nao_sai(self):
        with pytest.raises(ConsultaRecusada, match="Só um filtro"):
            montar("a", {"orgao_julgador": ["A", "B"], "magistrado": ["C", "D"]})

    def test_aspas_no_valor_sao_escapadas(self):
        q, _ = montar("*:*", {"orgao_julgador": ['A "x"', "B"]})
        assert q == 'orgao_julgador:("A \\"x\\"" OR "B")'


class TestParaJulgado:
    def test_acordao_com_ementa_e_divergencia(self):
        j = para_julgado(doc_pje2g(), ACERVOS["pje2g"], ["medicamento"])
        assert j.numero == "0000001-11.2023.8.08.0024"
        assert j.ementa.startswith("EMENTA: APELAÇÃO CÍVEL.")
        assert "\n1. Requisitos" in j.ementa
        assert j.relator_originario == "JOAO EXEMPLO DA SILVA"
        assert j.data == "2024-03-05" and j.data_rotulo == "juntada"
        assert j.trecho == ""

    def test_voto_servindo_como_ementa_vira_trecho(self):
        j = para_julgado(doc_pje2g(ementa="\nVoto servindo como ementa.\n"), ACERVOS["pje2g"], ["medicamento"])
        assert j.ementa == ""
        assert "voto servindo como ementa" in j.ementa_ausente_motivo
        assert "fornecimento de medicamento" in j.trecho

    def test_sentenca_sem_ementa_traz_trecho_e_dispositivo(self):
        j = para_julgado(doc_pje1g(), ACERVOS["pje1g"], ["usucapião especial urbana"])
        assert j.ementa == "" and "não tem campo de ementa" in j.ementa_ausente_motivo
        assert "usucapião especial urbana" in j.trecho
        assert j.dispositivo.startswith("Ante o exposto, JULGO PROCEDENTE")
        assert j.comarca == "Exemplo"

    def test_legado_usa_data_de_julgamento_e_numero_novo(self):
        j = para_julgado(doc_legado(), ACERVOS["legado"], [])
        assert j.numero == "0009830-61.2011.8.08.0048"
        assert j.data == "2018-03-12" and j.data_rotulo == "julgamento"
        assert j.data_publicacao == "2018-03-26"
        assert j.magistrado == "ANTONIO EXEMPLO"
        assert j.ementa.startswith("EMENTA")
        assert j.dispositivo.startswith("À unanimidade")

    def test_turma_extrai_ementa_do_texto(self):
        j = para_julgado(doc_turma(), ACERVOS["turma_recursal_legado"], [])
        assert j.numero == "0013462-27.2018.8.08.0347"
        assert j.ementa.startswith("E M E N T A: CONSUMIDOR.")
        assert j.classe == "Recurso Inominado"

    def test_inteiro_teor_cortado_declara_o_corte(self):
        j = para_julgado(doc_pje1g(), ACERVOS["pje1g"], [], com_texto=True, limite_texto=50)
        assert "[inteiro teor cortado em 50 de" in j.texto


def test_ler_facetas_converte_lista_alternada_e_descarta_vazios():
    facetas = ler_facetas({"facets": {"facet_fields": {**FACETAS_2G, "magistrado": ["", 3, "X", 0, "Y", 2]}}},
                          ACERVOS["pje2g"])
    assert facetas["orgao"][0] == ("1ª Câmara Cível", 28314)
    assert facetas["magistrado"] == [("Y", 2)]


async def test_pesquisar_envia_parametros_certos(transporte):
    feitas = transporte(lambda req: httpx.Response(200, json=resposta_busca([doc_pje2g()], 1741, FACETAS_2G)))
    async with TjesClient() as cliente:
        r = await cliente.pesquisar(
            "pje2g", "fornecimento de medicamento", {"orgao": ["1ª Câmara Cível"]},
            ordem="recentes", data_inicio="2025-01-01", por_pagina=5,
        )
    params = dict(feitas[0].url.params)
    assert params["core"] == "pje2g"
    assert params["q"] == "fornecimento AND medicamento"
    assert params["orgao_julgador"] == "1ª Câmara Cível"
    assert params["sort"] == "dt_juntada desc"
    assert params["dataIni"] == "2025-01-01" and "dataFim" not in params
    assert params["per_page"] == "5"
    assert r.total == 1741 and r.julgados[0].relator_originario


async def test_por_numero_nas_turmas_busca_pelos_digitos(transporte):
    feitas = transporte(lambda req: httpx.Response(200, json=resposta_busca([doc_turma()])))
    async with TjesClient() as cliente:
        julgados = await cliente.por_numero("turma_recursal_legado", "0013462-27.2018.8.08.0347")
    assert dict(feitas[0].url.params)["q"] == "num_processo:134622720188080347"
    assert julgados[0].texto.startswith("COLÉGIO RECURSAL")


async def test_erro_transitorio_tenta_de_novo(transporte, monkeypatch):
    monkeypatch.setattr("tjes_juris_mcp.http.asyncio.sleep", _sem_espera)
    respostas = iter([httpx.Response(503), httpx.Response(200, json=resposta_busca([doc_pje2g()]))])
    feitas = transporte(lambda req: next(respostas))
    async with TjesClient() as cliente:
        r = await cliente.pesquisar("pje2g", "x")
    assert len(feitas) == 2 and r.total == 1


async def test_403_nao_tenta_de_novo(transporte):
    feitas = transporte(lambda req: httpx.Response(403))
    async with TjesClient() as cliente:
        with pytest.raises(httpx.HTTPStatusError):
            await cliente.pesquisar("pje2g", "x")
    assert len(feitas) == 1


async def _sem_espera(_: float) -> None:
    return None
