# Regras de citação: detalhes e exemplos

## Recorte de ementa

Original devolvido pela ferramenta:

> EMENTA: APELAÇÃO CÍVEL. MEDICAMENTO NÃO PADRONIZADO. LAUDO MÉDICO QUE NÃO DESTACA A IMPRESCINDIBILIDADE DO MEDICAMENTO. TEMA 106 STJ. IMPOSSIBILIDADE DE FORNECIMENTO PELO PODER PÚBLICO. RECURSO CONHECIDO E PROVIDO. 1. Na esteira do entendimento firmado (...) 5. Recurso conhecido e provido.

Recorte aceitável (cabeça inteira, item pertinente, corte marcado):

> EMENTA: APELAÇÃO CÍVEL. MEDICAMENTO NÃO PADRONIZADO. LAUDO MÉDICO QUE NÃO DESTACA A IMPRESCINDIBILIDADE DO MEDICAMENTO. TEMA 106 STJ. IMPOSSIBILIDADE DE FORNECIMENTO PELO PODER PÚBLICO. RECURSO CONHECIDO E PROVIDO. (...) 3. Inexistem nos autos documentos que atestem a imprescindibilidade do uso do medicamento ora postulado (...).

Inaceitável: "A 1ª Câmara Cível entendeu que, sem laudo, não há fornecimento" entre aspas. Isso é paráfrase e vai fora da citação, como leitura do assistente.

## Referência depois do trecho

Formato sugerido para quem vai levar a citação a uma decisão:

`(TJES, Apelação Cível n. 0000000-00.0000.8.08.0000, 1ª Câmara Cível, Rel. [conferir], j. [conferir data da sessão])`

- "Rel." só depois de conferir no acórdão se houve divergência (redator x relator originário).
- "j." exige a data da sessão. A data de juntada do PJe não serve.
- No acervo legado e nas turmas, a data de julgamento devolvida pode ser usada.

## Acervos e o que cada um traz

| Acervo | Chave | Tem ementa? | Data | Campo de magistrado |
|---|---|---|---|---|
| 2º grau, acórdãos (PJe) | `pje2g` | sim (às vezes "voto servindo como ementa") | juntada | redator do acórdão |
| 2º grau, monocráticas (PJe) | `pje2g_mono` | não: trecho + dispositivo | juntada | prolator |
| 1º grau (PJe) | `pje1g` | não: trecho + dispositivo | juntada | juiz prolator |
| 2º grau físico | `legado` | sim | julgamento e publicação | desembargador |
| Turmas recursais (Projudi) | `turma_recursal_legado` | extraída do texto quando há cabeçalho EMENTA | julgamento | juiz |

O acervo `pje2g` inclui acórdãos das turmas recursais do PJe (jurisdição "Turma Recursal"). Para ficar só no Tribunal, filtre `jurisdicao` = `Tribunal de Justiça`.

## Situação de precedente no BNP

| Situação (literal) | Como apresentar |
|---|---|
| Vigente, Transitado em julgado, Mérito julgado | com força de precedente, tese literal |
| Admitido, Em julgamento, Afetado | ainda sem tese; verificar suspensão de processos |
| Não admitido | não é precedente; não citar como tal |
| Revisado, Superado, Cancelado, Revogado | não citar como vigente; indicar a situação |

## Quando a ferramenta falha

- **HTTP 403:** a recusa é da rede de onde a consulta sai (VPN, proxy, provedor). Teste com `tjes_acervos`; fora da rede do tribunal, tente outra conexão.
- **"Consulta não enviada":** a mensagem diz como reescrever (o tribunal recusa `(a OR b) AND c`; use `c AND (a OR b)`).
- **Certificado:** em rede com inspeção de TLS, a autoridade interna precisa estar instalada no Windows.
