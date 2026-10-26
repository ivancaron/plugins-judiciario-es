"""Tratamento de texto: limpeza, comparação sem acento e recorte literal.

Tudo o que sai daqui para a ementa ou para um trecho é **substring do
texto do tribunal**, só com marcação e espaços normalizados. Nada é
reescrito: o recorte marca o corte com "(...)", e quem lê sabe onde o
texto foi interrompido.
"""
from __future__ import annotations

import html
import re
import unicodedata

_TAGS = re.compile(r"<[^>]+>")
_ESPACOS = re.compile(r"\s+")
_DIGITOS = re.compile(r"\D")
_CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")

_ORDINAIS = {
    "primeira": "1", "primeiro": "1", "segunda": "2", "segundo": "2",
    "terceira": "3", "terceiro": "3", "quarta": "4", "quarto": "4",
    "quinta": "5", "quinto": "5", "sexta": "6", "sexto": "6",
    "setima": "7", "setimo": "7", "oitava": "8", "oitavo": "8",
    "nona": "9", "nono": "9", "decima": "10", "decimo": "10",
}
_ORDINAL_NUMERICO = re.compile(r"\b(\d{1,2})\s*(?:ª|º|°|a|o)\b")


def limpar(valor: object, *, paragrafos: bool = False) -> str:
    """Tira HTML e normaliza espaços; lista vira texto corrido.

    Com `paragrafos`, as quebras de linha do tribunal ficam (uma por
    parágrafo), para que a ementa estruturada ("I. CASO EM EXAME...")
    continue legível.
    """
    if not valor:
        return ""
    if isinstance(valor, list):
        valor = " ".join(str(v) for v in valor if v)
    texto = html.unescape(_TAGS.sub(" ", str(valor))).replace("\xa0", " ")
    if not paragrafos:
        return _ESPACOS.sub(" ", texto).strip()
    linhas = (_ESPACOS.sub(" ", linha).strip() for linha in texto.splitlines())
    return "\n".join(linha for linha in linhas if linha)


def lista(valor: object) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, list):
        return [limpar(v) for v in valor if limpar(v)]
    return [limpar(valor)]


def sem_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar(texto: str) -> str:
    """Forma de comparação: sem acento, sem caixa, ordinais por extenso
    reduzidos a número ("Primeira Câmara" e "1ª Câmara" ficam iguais)."""
    base = sem_acentos(texto or "").casefold()
    base = _ORDINAL_NUMERICO.sub(r"\1", base)
    base = re.sub(r"[^\w\s]", " ", base)
    palavras = [_ORDINAIS.get(p, p) for p in base.split()]
    return " ".join(palavras)


def _mapa_sem_acento(texto: str) -> str:
    """Versão do texto com o MESMO comprimento, para achar posições."""
    saida = []
    for c in texto:
        base = unicodedata.normalize("NFD", c)[0] if c else c
        saida.append(base.casefold()[:1] or " ")
    return "".join(saida)


def trecho(texto: str, termos: list[str], janela: int = 900) -> str:
    """Recorte literal do texto em torno da primeira ocorrência de um termo.

    Devolve vazio quando nenhum termo aparece. O recorte começa e termina
    em fronteira de palavra e leva "(...)" onde corta.
    """
    if not texto:
        return ""
    mapa = _mapa_sem_acento(texto)
    posicoes = [
        mapa.find(sem_acentos(t).casefold())
        for t in termos if t and len(t) >= 3
    ]
    posicoes = [p for p in posicoes if p >= 0]
    if not posicoes:
        return ""
    centro = min(posicoes)
    inicio = max(0, centro - janela // 3)
    fim = min(len(texto), inicio + janela)
    if inicio > 0:
        espaco = texto.find(" ", inicio)
        inicio = espaco + 1 if 0 <= espaco < centro else inicio
    if fim < len(texto):
        espaco = texto.rfind(" ", centro, fim)
        fim = espaco if espaco > centro else fim
    recorte = texto[inicio:fim].strip()
    return f"{'(...) ' if inicio > 0 else ''}{recorte}{' (...)' if fim < len(texto) else ''}"


_MARCAS_DISPOSITIVO = (
    "ante o exposto", "diante do exposto", "pelo exposto", "isto posto",
    "isso posto", "posto isso", "em face do exposto", "dispositivo",
)


def dispositivo(texto: str, tamanho: int = 1200) -> str:
    """Recorte literal a partir da última marca de dispositivo.

    Heurística declarada: procura "Ante o exposto", "Isto posto" e afins;
    sem marca, devolve vazio, e quem apresenta diz que não achou.
    """
    if not texto:
        return ""
    mapa = _mapa_sem_acento(texto)
    melhor = max((mapa.rfind(m) for m in _MARCAS_DISPOSITIVO), default=-1)
    if melhor < 0:
        return ""
    fim = min(len(texto), melhor + tamanho)
    if fim < len(texto):
        espaco = texto.rfind(" ", melhor, fim)
        fim = espaco if espaco > melhor else fim
    recorte = texto[melhor:fim].strip()
    return f"{recorte}{' (...)' if fim < len(texto) else ''}"


def formatar_cnj(valor: str) -> str:
    """Número no padrão CNJ quando os dígitos permitem; senão, como veio.

    O acervo das turmas guarda só os dígitos, às vezes sem os zeros à
    esquerda; o legado guarda o número antigo e o novo separados por "|".
    """
    texto = limpar(valor)
    achado = _CNJ.search(texto)
    if achado:
        return achado.group(0)
    digitos = _DIGITOS.sub("", texto)
    if 17 <= len(digitos) <= 20 and "|" not in texto:
        d = digitos.zfill(20)
        return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"
    return texto


def data_iso(valor: object) -> str:
    """'2023-11-24T19:26:42.560Z' ou ['2020-02-20T...'] vira '2023-11-24'."""
    if isinstance(valor, list):
        valor = valor[0] if valor else ""
    texto = str(valor or "").strip()
    return texto[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", texto) else ""
