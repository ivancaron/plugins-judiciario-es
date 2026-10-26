---
description: Pesquisa a jurisprudência do TJES (cinco acervos) com filtro por câmara, magistrado ou classe, e traz os IRDR, IAC e súmulas do próprio tribunal
argument-hint: "<tema> [câmara | magistrado | classe] [--1g | --mono | --legado | --turmas] [--recentes] [--desde AAAA-MM-DD] [--n 10]"
allowed-tools: mcp__plugin_jurisprudencia-tjes_tjes-jurisprudencia__tjes_pesquisar, mcp__plugin_jurisprudencia-tjes_tjes-jurisprudencia__tjes_resolver_filtro, mcp__plugin_jurisprudencia-tjes_tjes-jurisprudencia__tjes_inteiro_teor, mcp__plugin_jurisprudencia-tjes_tjes-jurisprudencia__tjes_precedentes_qualificados, mcp__plugin_jurisprudencia-tjes_tjes-jurisprudencia__tjes_acervos
---

# /jurisprudencia-tjes

Pesquise a jurisprudência do Tribunal de Justiça do Espírito Santo sobre: **$ARGUMENTS**

Antes de apresentar qualquer resultado, siga a skill `apresentar-jurisprudencia-tjes` (regras de transcrição literal, card, cobertura).

## 1. Ler o pedido

Separe do texto:

- **Tema:** o que vem antes do filtro. Expressão entre aspas é exigida inteira e na ordem.
- **Filtro (opcional):** pode vir explícito (`camara:`, `relator:` ou `magistrado:`, `classe:`, `assunto:`, `comarca:`) ou solto no fim ("1ª Câmara Cível", "des. Fulano", "apelação"). Solto, a ferramenta deduz o campo.
- **Acervo:** padrão `pje2g` (acórdãos do 2º grau). `--1g` = `pje1g` (sentenças e decisões); `--mono` = `pje2g_mono` (monocráticas); `--legado` = `legado` (2º grau físico); `--turmas` = `turma_recursal_legado`. Sem flag, se o filtro for comarca ou vara, o acervo é o `pje1g`.
- **Ordem e período:** `--recentes` ordena pelos mais novos; `--desde`/`--ate` em AAAA-MM-DD.
- **Quantidade:** `--n`, padrão 10, teto 25.

Sem tema, peça o tema e pare. Se o tema for um número de processo, vá direto ao passo 5 (`tjes_inteiro_teor`).

## 2. Montar a consulta

Mostre ao usuário, numa linha, a consulta que vai rodar. Regras:

- Palavras soltas viram AND (todas precisam aparecer). Para o núcleo do tema, prefira a expressão entre aspas: `"fornecimento de medicamento"`, `"tráfico privilegiado"`.
- Se o tema tiver sinônimo corrente no tribunal, use OR com o grupo **no fim**: `medicamento AND ("alto custo" OR "não padronizado")`. A API do TJES recusa `(a OR b) AND c`; a ferramenta avisa se acontecer.
- Não invente termo técnico que a pessoa não usou só para ampliar; se o resultado vier pequeno, proponha a ampliação no fim.

## 3. Resolver o filtro

Com filtro, chame `tjes_resolver_filtro` com o texto do filtro, o acervo e o `termo` (para que as contagens sejam as do tema).

- **Resolvido:** use os valores exatamente como vieram (inclusive grafias diferentes da mesma classe, todas juntas).
- **Ambíguo:** mostre os candidatos com as contagens e pergunte qual usar. Exceção: se a pessoa escreveu só "apelação" num tema cível, use as classes de apelação cível e diga que fez isso.
- **Sem casamento:** mostre os valores mais próximos que a ferramenta trouxer, ou rode a pesquisa sem o filtro e mostre a distribuição para a pessoa escolher.
- **Campo indisponível no acervo:** diga quais campos o acervo tem.

## 4. Pesquisar

Numa mesma mensagem, em paralelo:

- `tjes_pesquisar` com termo, acervo, filtro resolvido, ordem, período e quantidade;
- `tjes_precedentes_qualificados` com as 1 a 3 palavras centrais do tema (sem aspas longas: a busca é por palavra na tese e na questão).

Se o total vier zero, tente uma vez com a consulta mais larga (tirar aspas ou um termo) e diga que alargou. Se vier acima de 300 sem filtro, mostre a distribuição e sugira o recorte (câmara, classe, período) antes de despejar julgados.

## 5. Apresentar

Nesta ordem, conforme a skill:

1. **Cabeçalho:** tema, acervo, consulta executada, filtros, período, total encontrado e quantos foram exibidos.
2. **Precedentes qualificados do TJES:** os que casam, com tese literal e situação. Os não admitidos, superados, revisados ou cancelados vão em bloco separado, com o aviso de que não se citam como vigentes. Se nenhum casar, diga isso em uma linha.
3. **Panorama:** a distribuição por órgão julgador, classe e magistrado (até 5 valores de cada), como contagem do índice.
4. **Julgados:** os cards, com ementa (ou trecho) **literal** em bloco de citação.
5. **Leitura das correntes:** só quando houver três julgados ou mais. Em poucas linhas, os entendimentos que aparecem e onde (órgão, período), cada afirmação ancorada no número do card (`[2]`, `[5]`). Título fixo: "Leitura do assistente (conferir nos julgados)". Sem recomendação de como decidir.
6. **Cobertura e limites:** acervo consultado e os não consultados; total e exibidos; data de juntada não é a data da sessão; conferir o inteiro teor antes de citar (instrução de conferência do card); a pesquisa é por palavras e pode deixar de fora julgado com outra redação.
7. **Próximos passos:** 2 ou 3 sugestões concretas de refinamento tiradas das facetas (ex.: `/jurisprudencia-tjes "fornecimento de medicamento" camara:"2ª Câmara Cível" --recentes`), mais a opção de ler o inteiro teor de um card.

Inteiro teor só sob pedido ou quando a ementa não basta para responder: `tjes_inteiro_teor` com número e acervo.

## 6. Salvar

Pergunte se a pessoa quer salvar. Se sim, grave o relatório em Markdown em `./pesquisas-tjes/AAAA-MM-DD_<tema-curto>.md` (diretório atual), com o mesmo conteúdo apresentado, e informe o caminho.

## Limites que não se negociam

- Ementa, trecho, tese e enunciado são transcritos **palavra por palavra** como a ferramenta devolveu. Nada de resumo dentro das aspas, correção ou complemento.
- Nenhum julgado, número, data ou relator que não tenha vindo da ferramenta nesta conversa.
- A distribuição por magistrado é contagem, nunca perfil, tendência ou juízo sobre a pessoa.
- Não cole nem peça dados de processo sob segredo de justiça: a pesquisa só precisa do tema.
