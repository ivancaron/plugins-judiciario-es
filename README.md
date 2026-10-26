# plugins-judiciario-es

Plugins do [Claude Code](https://claude.com/claude-code) para o trabalho jurisdicional no Espírito Santo.

| Plugin | Comando | O que faz |
|---|---|---|
| `jurisprudencia-tjes` | `/jurisprudencia-tjes` | Pesquisa os cinco acervos públicos de jurisprudência do TJES com filtro por câmara, magistrado, classe, assunto e comarca, e traz os IRDR, IAC e súmulas do tribunal |

## Instalação (Windows, uma vez)

1. **Claude Code** instalado e com login feito.
2. **uv** (roda o servidor de pesquisa; baixa o Python sozinho se faltar). No PowerShell:

   ```powershell
   winget install --id=astral-sh.uv -e
   ```

   Feche e abra o terminal depois.
3. Dentro do Claude Code:

   ```
   /plugin marketplace add ivancaron/plugins-judiciario-es
   /plugin install jurisprudencia-tjes@judiciario-es
   ```

   Reinicie o Claude Code. Na primeira vez o servidor leva alguns segundos para preparar o ambiente; se aparecer como desconectado em `/mcp`, peça para reconectar.

Para conferir: `/jurisprudencia-tjes "fornecimento de medicamento" 1ª Câmara Cível`.

## Uso

```
/jurisprudencia-tjes <tema> [câmara | magistrado | classe] [--1g | --mono | --legado | --turmas] [--recentes] [--desde AAAA-MM-DD] [--n 10]
```

- **Tema:** palavras soltas precisam aparecer todas; expressão entre aspas é exigida inteira.
- **Filtro:** pode vir solto ("2ª Câmara Criminal", "des. Fulano", "apelação") ou explícito (`camara:`, `relator:`, `classe:`, `assunto:`, `comarca:`). O plugin acha o valor exato que o tribunal grava.
- **Acervo:** acórdãos do 2º grau por padrão; `--1g` sentenças e decisões do 1º grau; `--mono` decisões monocráticas; `--legado` 2º grau físico; `--turmas` turmas recursais do Projudi.

Também funciona em linguagem natural, sem o comando: "o que a 1ª Câmara Criminal tem decidido sobre tráfico privilegiado em 2026?".

### Cinco usos para o dia a dia

1. **Coerência da própria câmara (art. 926 do CPC):** `/jurisprudencia-tjes "dano moral" "atraso de voo" camara:"3ª Câmara Cível" --recentes`
2. **Divergência entre câmaras:** `/jurisprudencia-tjes "tráfico privilegiado" "maus antecedentes"`; o panorama mostra como o resultado se distribui pelos órgãos, e a leitura aponta as correntes com os julgados de cada uma.
3. **Precedente qualificado aplicável:** `/jurisprudencia-tjes "agente comunitário" jornada`; os IRDR e IAC do TJES aparecem antes, com a situação literal do Banco Nacional de Precedentes.
4. **Sentenças semelhantes no 1º grau:** `/jurisprudencia-tjes "usucapião especial urbana" comarca:"Vila Velha" --1g`
5. **Juizados:** `/jurisprudencia-tjes "negativação indevida" --turmas`

## O que sai e o que não sai da sua máquina

- O servidor de pesquisa roda no seu computador. Só os **termos de busca e os filtros** vão às APIs públicas do TJES e do CNJ. Não há login, senha nem telemetria.
- A conversa com o Claude segue as regras da sua conta. **Não cole dados de processo sob segredo de justiça:** a pesquisa só precisa do tema.

## Cuidados que o plugin já toma, e que valem conferir

- Ementa e tese são transcritas literalmente. Mesmo assim, confira no inteiro teor antes de levar a uma decisão.
- No PJe, a data devolvida pelo índice é a de **juntada**, não a da sessão.
- No acórdão, o magistrado do índice é o **redator** do voto vencedor; havendo divergência, o plugin indica o relator originário.
- A página pública do TJES não abre um julgado por endereço; cada card traz a instrução para achá-lo (aba do acervo, "Busca Exata", número).
- A ferramenta não consulta STF nem STJ.

## Desenvolvimento

```powershell
cd plugins/jurisprudencia-tjes/servidor
uv run pytest              # offline
uv run pytest -m rede      # contra as APIs reais
uv run ruff check src tests
uv run pytest ../../../tests   # trava de identidade
```

Licença MIT.
