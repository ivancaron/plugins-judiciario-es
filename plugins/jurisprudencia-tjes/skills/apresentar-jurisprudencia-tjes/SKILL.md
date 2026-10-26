---
name: apresentar-jurisprudencia-tjes
description: Regras para apresentar jurisprudência do TJES vinda das ferramentas tjes_* (pesquisa nos cinco acervos e precedentes qualificados do BNP): transcrição literal de ementa e tese, card do julgado, data de juntada x sessão, redator x relator originário, situação do precedente e declaração de cobertura. Use SEMPRE que for exibir, resumir, comparar ou salvar resultado de tjes_pesquisar, tjes_inteiro_teor ou tjes_precedentes_qualificados, inclusive fora do comando /jurisprudencia-tjes (ex.: "o que a 2ª Câmara Criminal decide sobre X", "tem IRDR do TJES sobre Y", "acha sentenças de usucapião em Vila Velha").
---

# Apresentar jurisprudência do TJES

Quem lê vai decidir ou fundamentar com base no que você mostrar. O erro que mais custa é uma ementa "quase igual", uma data trocada ou um precedente superado apresentado como vivo. Estas regras existem para impedir isso.

## 1. Transcrição literal

- Ementa, trecho, dispositivo, tese e enunciado vão em bloco de citação (`>`), **exatamente** como a ferramenta devolveu, inclusive caixa alta, numeração e pontuação.
- Pode cortar, nunca reescrever: o corte se marca com `(...)`. Ementa longa em relatório: mantenha a cabeça (as palavras em caixa alta) e os itens que respondem à pergunta, com `(...)` entre eles.
- Nunca corrija erro de digitação do tribunal nem "atualize" texto de lei dentro da citação. Se notar o erro, aponte fora da citação.
- Sem ementa (1º grau, monocráticas, "voto servindo como ementa"), diga isso e use o trecho literal que a ferramenta trouxe, com o rótulo dela.

## 2. Card do julgado

```
### [n] CLASSE NÚMERO-CNJ
- Órgão julgador · Redator do acórdão / Magistrado · Relator originário (se houver)
- Data de juntada AAAA-MM-DD (não é a data da sessão) | Data de julgamento (legado e turmas)
- Assuntos
- Conferência: instrução que a ferramenta devolveu

**Ementa (literal):**
> ...
```

- **Redator x relator:** no acórdão do PJe, o campo de magistrado é o redator do voto vencedor. Quando a ferramenta aponta relator originário vencido, mostre os dois e diga que houve divergência. Não chame o redator de "relator" sem essa ressalva.
- **Datas:** no PJe a data é de juntada. Para citar "j. dd/mm/aaaa", a data da sessão precisa ser confirmada no processo. No acervo legado e nas turmas a data é de julgamento, e pode ser usada como tal.
- **Conferência:** a página pública do TJES não abre julgado por endereço. Reproduza a instrução (aba do acervo, "Busca Exata", número entre aspas). Não invente link.

## 3. Precedentes qualificados

- IRDR, IAC e súmula do TJES vinculam o próprio tribunal e os juízes a ele vinculados (art. 927, III e V, do CPC). Mostre-os antes dos julgados avulsos.
- A situação vem literal do BNP. "Não admitido", "Superado", "Revisado" e "Cancelado" ficam em bloco separado, com o aviso de não citar como vigente. "Admitido" ou "Em julgamento" significa que ainda não há tese: diga isso e, se for o caso, lembre de verificar suspensão de processos.
- Nota técnica não vincula; apresente como subsídio.
- A ferramenta não consulta STF nem STJ. Não afirme que "não há precedente vinculante sobre o tema", e sim que "não há precedente qualificado do TJES no BNP que case com os termos".

## 4. Panorama e leitura

- A distribuição por órgão, classe e magistrado é contagem do índice para aquela consulta. Apresente como número. Não transforme em perfil, tendência, rigor ou "favorável/desfavorável" a ninguém.
- A leitura das correntes é sua, não do tribunal: título "Leitura do assistente (conferir nos julgados)", cada afirmação com o número do card, sem recomendação de como decidir. Se os julgados exibidos são poucos diante do total, diga que a leitura vale para a amostra.

## 5. Cobertura (sempre)

Feche com o que foi e o que não foi consultado: acervo(s), consulta executada, total encontrado e exibido, filtros, período. Lembre que a busca é por palavras (julgado com outra redação pode ter ficado de fora) e que a ementa deve ser conferida no inteiro teor antes de ir para uma decisão.

## 6. Nunca

- Julgado, número, data, relator ou tese que não tenha vindo das ferramentas nesta conversa.
- Completar resultado vazio com memória ("o TJES costuma entender...").
- Pedir ou repetir dado de processo sob segredo de justiça.

Detalhes e exemplos: `references/regras-de-citacao.md`.
