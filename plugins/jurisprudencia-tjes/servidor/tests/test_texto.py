from tjes_juris_mcp import texto as tx


def test_normalizar_iguala_ordinal_por_extenso_e_abreviado():
    assert tx.normalizar("1ª Câmara Cível") == tx.normalizar("Primeira câmara civel")
    assert tx.normalizar("QUARTA CÂMARA CÍVEL ") == "4 camara civel"
    assert tx.normalizar("1a câmara criminal") == "1 camara criminal"


def test_limpar_tira_html_e_preserva_paragrafos_quando_pedido():
    bruto = "<p>EMENTA: A.&nbsp;B.</p>\n<p>  1. Item   um.</p>"
    assert tx.limpar(bruto) == "EMENTA: A. B. 1. Item um."
    assert tx.limpar(bruto, paragrafos=True) == "EMENTA: A. B.\n1. Item um."


def test_formatar_cnj_das_turmas_recompoe_zeros_a_esquerda():
    assert tx.formatar_cnj("134622720188080347") == "0013462-27.2018.8.08.0347"


def test_formatar_cnj_do_legado_prefere_o_numero_novo():
    assert tx.formatar_cnj("048.11.009830-7 | 0009830-61.2011.8.08.0048") == "0009830-61.2011.8.08.0048"


def test_trecho_e_substring_literal_e_acha_sem_acento():
    texto = "Primeira parte longa. " * 40 + "A usucapião especial urbana exige cinco anos. " + "Fim. " * 200
    recorte = tx.trecho(texto, ["usucapiao"], janela=200)
    corpo = recorte.removeprefix("(...) ").removesuffix(" (...)")
    assert corpo in texto
    assert "usucapião" in corpo
    assert recorte.startswith("(...)") and recorte.endswith("(...)")


def test_trecho_vazio_quando_o_termo_nao_aparece():
    assert tx.trecho("texto qualquer", ["inexistente"]) == ""


def test_dispositivo_comeca_na_ultima_marca():
    texto = "Relatório. Ante o exposto no parecer, segue. Fundamentos. Ante o exposto, JULGO PROCEDENTE."
    assert tx.dispositivo(texto) == "Ante o exposto, JULGO PROCEDENTE."
    assert tx.dispositivo("sem marca alguma") == ""


def test_data_iso_aceita_lista_e_texto():
    assert tx.data_iso("2023-11-24T19:26:42.560Z") == "2023-11-24"
    assert tx.data_iso(["2020-02-20T15:46:10Z"]) == "2020-02-20"
    assert tx.data_iso("") == ""
