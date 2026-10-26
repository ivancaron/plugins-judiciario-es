"""O repositório se apresenta de forma neutra, e por mais nada.

Nenhum arquivo versionado (comando, skill, descrição de ferramenta,
mensagem de erro, agente de requisição, manifesto) pode carregar
referência institucional, endereço pessoal, caminho de máquina ou nome
de repositório de onde partes do código vieram. A violação é fácil e
silenciosa: basta um docstring copiado ou um caminho de exemplo.

Rodar da raiz: `uv run --project plugins/jurisprudencia-tjes/servidor pytest tests`
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

PROIBIDOS = [
    r"defensoria",
    r"\bdpes\b",
    r"defensor\s+p[uú]blico",
    r"jurismcp",
    r"pje[_-]mcp",
    r"pipeline[_-]pje",
    r"pipeline[_-]canonico",
    r"mcp[_-]precedentes",
    r"ivan\s+mayer",
    r"ivancaron",
    r"[\w.+-]+@gmail\.com",
    r"C:\\\\?Users",
    r"/mnt/c/",
]
_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in PROIBIDOS]

# Exceção deliberada: o endereço do próprio repositório, sem o qual não há
# como instalar o marketplace. Vale só a forma exata; a conta solta em
# qualquer outro contexto continua barrada.
ENDERECO_DO_REPOSITORIO = re.compile(r"(?:github\.com/)?ivancaron/plugins-judiciario-es\b")
_BINARIOS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".lock"}


def _arquivos() -> list[Path]:
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [
        RAIZ / caminho for caminho in saida
        if Path(caminho).suffix.lower() not in _BINARIOS
        and Path(caminho).name != "test_identidade.py"
    ]


def test_nenhum_arquivo_carrega_identidade_alheia():
    achados = []
    for arquivo in _arquivos():
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        conteudo = ENDERECO_DO_REPOSITORIO.sub(lambda m: "x" * len(m.group(0)), conteudo)
        for padrao in _COMPILADOS:
            for m in padrao.finditer(conteudo):
                linha = conteudo.count("\n", 0, m.start()) + 1
                achados.append(f"{arquivo.relative_to(RAIZ)}:{linha}: {m.group(0)!r}")
    assert not achados, "Identidade proibida encontrada:\n" + "\n".join(achados)


def test_excecao_vale_so_para_o_endereco_exato():
    neutralizado = ENDERECO_DO_REPOSITORIO.sub("", "github.com/ivancaron/plugins-judiciario-es e ivancaron/outro")
    assert any(p.search(neutralizado) for p in _COMPILADOS)


def test_a_lista_de_arquivos_nao_esta_vazia():
    assert any(a.name == "plugin.json" for a in _arquivos())
