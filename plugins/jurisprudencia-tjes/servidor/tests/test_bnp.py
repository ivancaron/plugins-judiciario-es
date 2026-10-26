import httpx

from tjes_juris_mcp import bnp


def item(**extra):
    base = {
        "id": "tjes-irdr-1", "orgao": "TJES", "tipo": "IRDR", "nr": "1",
        "situacao": "Transitado em julgado", "tese": "<p>Tese jurídica 1: é ilegal o divisor.</p>",
        "questao": "A legalidade da jornada de 220 horas.", "ultimaAtualizacao": "20/07/2026",
        "processosParadigma": [{"link": "http://exemplo.invalid/processo", "numero": "00003448220"}],
    }
    base.update(extra)
    return base


def test_sumula_promove_o_enunciado_da_questao():
    p = bnp.para_precedente(item(tipo="SUM", nr="12", tese="Não informado", questao="Enunciado da súmula."))
    assert p.tese == "Enunciado da súmula." and p.questao == ""


def test_situacoes_sem_forca():
    assert bnp.para_precedente(item(situacao="Não admitido")).sem_forca
    assert bnp.para_precedente(item(situacao="Superado")).sem_forca
    assert not bnp.para_precedente(item(situacao="Vigente")).sem_forca


def test_link_do_paradigma_ou_ausencia_declarada():
    assert bnp.para_precedente(item()).link[0] == "http://exemplo.invalid/processo"
    url, obs = bnp.para_precedente(item(processosParadigma=[{"numero": "123"}])).link
    assert url == "" and "123" in obs


def test_descarta_registro_de_outro_orgao_ou_sem_numero():
    assert bnp.para_precedente(item(orgao="STJ")) is None
    assert bnp.para_precedente(item(nr="x")) is None


def test_filtrar_exige_todos_os_termos_sem_acento_e_aceita_plural():
    precedentes = [bnp.para_precedente(item()), bnp.para_precedente(item(id="2", nr="2", tese="Outra coisa.", questao="Outra questão."))]
    assert [p.nr for p in bnp.filtrar(precedentes, "jornada horas")] == [1]
    assert [p.nr for p in bnp.filtrar(precedentes, "jornadas")] == [1]
    assert bnp.filtrar(precedentes, '"divisor de 220"') == []
    assert len(bnp.filtrar(precedentes, "", ["IRDR"])) == 2
    assert bnp.filtrar(precedentes, "", ["SUM"]) == []


async def test_todos_pagina_ate_o_total_e_guarda_em_cache(transporte, monkeypatch):
    monkeypatch.setattr(bnp.BnpClient, "_cache", None)
    paginas = {1: [item(nr=str(n), id=str(n)) for n in range(1, 101)], 2: [item(nr="101", id="101")]}

    def manipulador(req: httpx.Request) -> httpx.Response:
        import json

        pagina = json.loads(req.content)["filtro"]["pagina"]
        return httpx.Response(200, json={"total": 101, "resultados": paginas.get(pagina, [])})

    feitas = transporte(manipulador)
    assert len(await bnp.BnpClient().todos()) == 101
    assert len(await bnp.BnpClient().todos()) == 101
    assert len(feitas) == 2
