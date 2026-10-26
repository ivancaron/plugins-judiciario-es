import httpx
from conftest import FACETAS_2G, doc_pje1g, doc_pje2g, resposta_busca

from tjes_juris_mcp import bnp, server


async def test_pesquisar_formata_card_com_rotulos_que_evitam_erro_de_citacao(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([doc_pje2g()], 1741, FACETAS_2G)))
    saida = await server.tjes_pesquisar(termo="medicamento", orgao=["1ª Câmara Cível"])
    assert "**Documentos que casam:** 1.741" in saida
    assert "Redator do acórdão (campo do índice):** MARIA REDATORA EXEMPLO" in saida
    assert "Relator originário, vencido:** JOAO EXEMPLO DA SILVA" in saida
    assert "Data de juntada:** 2024-03-05 (não é a data da sessão" in saida
    assert "> EMENTA: APELAÇÃO CÍVEL." in saida
    assert "> 1. Requisitos cumulativos" in saida
    assert "não abre o julgado por endereço direto" in saida
    assert "| `1ª Câmara Cível` | 28.314 |" in saida


async def test_pesquisar_sem_ementa_declara_e_traz_trecho(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([doc_pje1g()], 1)))
    saida = await server.tjes_pesquisar(termo="usucapião", acervo="pje1g")
    assert "*Sem ementa: este acervo não tem campo de ementa.*" in saida
    assert "Trecho literal do inteiro teor" in saida
    assert "Dispositivo (trecho literal)" in saida


async def test_pesquisar_sem_resultado_nao_afirma_inexistencia_geral(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([], 0)))
    saida = await server.tjes_pesquisar(termo="tema inexistente")
    assert "Isso diz respeito a este acervo e a esta consulta" in saida


async def test_filtro_que_o_acervo_nao_tem_volta_sem_consultar(transporte):
    feitas = transporte(lambda req: httpx.Response(200, json=resposta_busca([])))
    saida = await server.tjes_pesquisar(termo="x", acervo="legado", classe=["APELAÇÃO CÍVEL"])
    assert "não tem o(s) filtro(s) classe" in saida and not feitas


async def test_data_em_formato_errado(transporte):
    transporte(lambda req: httpx.Response(200, json=resposta_busca([])))
    assert "AAAA-MM-DD" in await server.tjes_pesquisar(termo="x", data_inicio="01/01/2025")


async def test_consulta_recusada_explica_a_reescrita(transporte):
    feitas = transporte(lambda req: httpx.Response(200, json=resposta_busca([])))
    saida = await server.tjes_pesquisar(termo="(a OR b) AND c")
    assert saida.startswith("**Consulta não enviada:**") and not feitas


async def test_403_vira_mensagem_sobre_a_rede(transporte):
    transporte(lambda req: httpx.Response(403))
    saida = await server.tjes_acervos()
    assert "HTTP 403" in saida and "rede" in saida


async def test_precedentes_separa_os_sem_forca(transporte, monkeypatch):
    monkeypatch.setattr(bnp.BnpClient, "_cache", None)
    resultados = [
        {"id": "1", "orgao": "TJES", "tipo": "IRDR", "nr": "1", "situacao": "Transitado em julgado",
         "tese": "Tese sobre medicamento.", "questao": "Questão.", "processosParadigma": []},
        {"id": "2", "orgao": "TJES", "tipo": "IRDR", "nr": "2", "situacao": "Não admitido",
         "tese": "", "questao": "Outra questão sobre medicamento.", "processosParadigma": []},
    ]
    transporte(lambda req: httpx.Response(200, json={"total": 2, "resultados": resultados}))
    saida = await server.tjes_precedentes_qualificados(termo="medicamento")
    vigentes, _, alerta = saida.partition("## Não admitidos")
    assert "IRDR 1/TJES" in vigentes and "IRDR 2/TJES" not in vigentes
    assert "IRDR 2/TJES" in alerta
    assert "*O BNP não traz tese fixada para este registro.*" in alerta


async def test_inteiro_teor_lista_os_documentos_do_processo(transporte):
    docs = [doc_pje2g(), doc_pje2g(id="102", classe_judicial="EMBARGOS DE DECLARAÇÃO CÍVEL")]
    transporte(lambda req: httpx.Response(200, json=resposta_busca(docs)))
    saida = await server.tjes_inteiro_teor(numero_processo="0000001-11.2023.8.08.0024", posicao=2)
    assert "O processo tem 2 documentos" in saida
    assert "EMBARGOS DE DECLARAÇÃO CÍVEL · 1ª Câmara Cível · juntada 2024-03-05 ← exibido" in saida
    assert "Inteiro teor (literal" in saida


async def test_registro_repetido_sai_e_a_omissao_e_declarada(transporte):
    repetido = doc_pje1g()
    outro = {**doc_pje1g(), "id": "202", "dt_juntada": "2026-03-26T10:00:00.000Z"}
    diferente = {**doc_pje1g(), "id": "203", "nr_processo": "0000003-33.2018.8.08.0064"}
    transporte(lambda req: httpx.Response(200, json=resposta_busca([repetido, outro, diferente], 3)))
    saida = await server.tjes_pesquisar(termo="usucapião", acervo="pje1g")
    assert saida.count("### [") == 2
    assert "Registros repetidos omitidos nesta página:** 1" in saida
