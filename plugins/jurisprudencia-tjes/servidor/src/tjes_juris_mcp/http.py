"""Cliente HTTP comum: nova tentativa só no transitório, TLS sempre verificado.

A verificação usa o repositório de certificados do sistema operacional
(`truststore`). Em rede corporativa com inspeção de TLS, a autoridade
interna já está ali, e a conexão funciona sem que ninguém precise
desligar a verificação, que é a saída errada para esse problema.
"""
from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import Awaitable, Callable

import httpx
import truststore

from tjes_juris_mcp import AGENTE

logger = logging.getLogger(__name__)

TIMEOUT = 40.0
STATUS_TRANSITORIOS = frozenset({408, 429, 500, 502, 503, 504})


def contexto_tls() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def novo_cliente(headers: dict[str, str] | None = None) -> httpx.AsyncClient:
    cabecalhos = {"User-Agent": AGENTE, "Accept": "application/json"}
    cabecalhos.update(headers or {})
    return httpx.AsyncClient(
        timeout=TIMEOUT, headers=cabecalhos, verify=contexto_tls()
    )


def _transitorio(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in STATUS_TRANSITORIOS
    return False


async def com_nova_tentativa(
    fazer: Callable[[], Awaitable[httpx.Response]], *, tentativas: int = 3
) -> httpx.Response:
    """Executa a requisição; repete com recuo só o que é transitório.

    Um 400 ou 403 é resposta definitiva: repetir só gasta o tempo de quem
    espera e a paciência do servidor do tribunal.
    """
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = await fazer()
            resposta.raise_for_status()
            return resposta
        except Exception as exc:  # noqa: BLE001 - reclassificado abaixo
            if not _transitorio(exc) or tentativa == tentativas:
                raise
            espera = 2 ** (tentativa - 1)
            logger.warning(
                "tentativa %d/%d falhou (%s); nova em %ds",
                tentativa, tentativas, exc, espera,
            )
            await asyncio.sleep(espera)
    raise RuntimeError("laço de nova tentativa sem resultado")


def descrever_falha(exc: Exception, fonte: str) -> str:
    """Mensagem de falha para quem usa, sem jargão de pilha."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 403:
            return (
                f"{fonte} recusou a consulta (HTTP 403). A recusa costuma ser "
                "da rede de onde a consulta sai (VPN, proxy ou provedor "
                "bloqueado), não do termo pesquisado."
            )
        return f"{fonte} respondeu com erro HTTP {status}."
    if isinstance(exc, httpx.TimeoutException):
        return f"{fonte} não respondeu a tempo ({int(TIMEOUT)} s)."
    if isinstance(exc, ssl.SSLError) or "CERTIFICATE" in str(exc).upper():
        return (
            f"Falha na verificação do certificado de {fonte}. Se a rede usa "
            "inspeção de TLS, a autoridade interna precisa estar instalada no "
            "sistema operacional."
        )
    if isinstance(exc, httpx.TransportError):
        return f"Sem conexão com {fonte} ({type(exc).__name__})."
    return f"Falha ao consultar {fonte}: {exc}"
