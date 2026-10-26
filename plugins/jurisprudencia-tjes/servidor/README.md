# tjes-juris-mcp

Servidor MCP (stdio) que consulta a jurisprudência pública do Tribunal de
Justiça do Espírito Santo e os precedentes qualificados do TJES no Banco
Nacional de Precedentes (CNJ). Roda na máquina de quem usa: as consultas
saem pela rede local, sem intermediário.

Nenhuma credencial é necessária. Só os termos de busca e os filtros vão
às APIs públicas do tribunal e do CNJ.

```
uv run tjes-juris-mcp          # inicia o servidor (stdio)
uv run pytest                  # testes offline
uv run pytest -m rede          # testes contra a API real
```
