# Passos restantes para concluir e submeter o artigo

Situação em 27 de setembro de 2026 — acompanha ARTIGO_UAVIDS2025_REVISADO.docx

## O que já está concluído

O dataset canônico foi identificado por hash e sua licença CC BY 4.0 foi conferida. Foram executados o painel principal v4 (150 ajustes), a estabilidade v5 (150 ajustes) e a sensibilidade v6 (10 ajustes). As análises possuem manifestos e predições rastreáveis. A reprodução em uma cópia limpa completou os 310 ajustes e verificou 13 tabelas com tolerância absoluta de 10⁻¹². Pacotes locais de reprodução e seus checksums estão preparados. O artigo foi reescrito com os resultados atuais, limitações explícitas e referências próximas ao problema.

O arquivo original ARTIGO_UAVIDS2025.docx permanece preservado. A nova versão é um manuscrito para revisão dos autores; não está submetida e não declara um depósito público que ainda não ocorreu.

## 1. Revisar a contribuição e a análise estatística

Responsável: autores e orientador; quando possível, leitor com experiência em avaliação de aprendizado de máquina.

Conferir se a comparação S0/S1/S2 e a ablação negativa acrescentam informação suficiente aos trabalhos de Zarkadis e Douligeris e de Demir e Gumus. A afirmação central deve continuar restrita ao benchmark e à tarefa fechada de cinco classes. Não apresentar origem disjunta, RF/XGBoost ou confusão Blackhole/Wormhole como novidades isoladas.

Revisar a adequação do bootstrap de grupos, particularmente a dependência entre assinaturas em S1 e a interpretação dos intervalos condicionais às predições fixas. Todos os contrastes são exploratórios. Se a revisão exigir mudança de unidade, estimador ou intervalo, versionar a análise e regenerar tabelas e texto. Não reinterpretar os intervalos atuais como prova de equivalência.

Critério de conclusão: um revisor humano consegue explicar o que cada protocolo estima, o que os intervalos cobrem e qual contribuição permanece diante da literatura. As decisões ficam registradas em protocol/statistical_review.md e protocol/literature_matrix.csv.

## 2. Decidir se a explicação de A3 exige um experimento adicional

Responsável: autores; implementação e execução podem ser automatizadas após a definição do protocolo.

A razão de vazão por salto fica ausente em 31,5% dos registros. O manuscrito atual reconhece que não separa o efeito do valor da razão do efeito da cobertura e imputação. Se a discussão pretender explicar o mecanismo, acrescentar uma ablação específica: A0 com apenas o indicador AverageHopCount≤0; A0 com a razão imputada; e A0 com razão e indicador. Usar os mesmos folds, dois modelos, parâmetros fixos e três sementes em S2. A comparação é exploratória porque os dados já foram vistos.

Registrar o tratamento de ausentes, as condições e o orçamento antes de executar; usar o mesmo indicador em treino e teste sem ajustar limiares pelo resultado. A conclusão pode continuar negativa. Esse experimento não é necessário para manter o relato limitado atual, mas é necessário para afirmar que o pequeno efeito de A3 vem da razão, da ausência ou de um mecanismo físico específico.

Critério de conclusão: executar todas as condições previstas e relatar seus resultados, ou manter expressamente a limitação sem explicação causal.

## 3. Escolher a revista e conferir suas regras atuais

Responsável: autores e programa de pós-graduação.

Selecionar uma revista cujo escopo aceite avaliação empírica e estudos reprodutíveis de segurança ou aprendizado de máquina. Conferir artigos recentes semelhantes, idioma, modelo de publicação, custos, extensão e exigência de disponibilidade de dados e código. Um periódico de exigência compatível pode ser mais adequado do que insistir em uma contribuição de arquitetura que não existe.

Não é possível garantir aceitação por um estrato. A CAPES informou que o Qualis 2021–2024 é retrospectivo e que o Qualis Periódicos não será utilizado no ciclo 2025–2028. Para a área de Ciência da Computação, qualquer referência a A2 ou B2 precisa indicar o ciclo histórico consultado e ser alinhada às regras do programa. Ainda não foi selecionada uma revista B2 específica. Fonte oficial: https://www.gov.br/capes/pt-br/assuntos/noticias/sobre-o-qualis-periodicos-na-avaliacao-quadrienal-2021-2024.

Critério de conclusão: registrar nome, ISSN, escopo, idioma, regras, custos e justificativa de adequação em protocol/journal_screen.md. A classificação histórica sozinha não resolve a escolha.

## 4. Fechar autoria e revisar o texto integralmente

Responsável: todos os autores.

Inserir nomes, afiliações, ORCID e autor correspondente antes da submissão. Definir contribuições, financiamento, conflitos e agradecimentos a partir de informações reais. Aprovar a declaração de assistência por IA segundo a política da revista. As informações editoriais pendentes foram mantidas neste plano para evitar declarações inventadas no artigo.

Conferir títulos, autores, DOI e versões das referências; atualizar a literatura imediatamente antes da submissão. Adicionar fundamentos metodológicos quando exigidos pela revista, sem inflar a bibliografia. Verificar cada número contra sua tabela de origem e distinguir pontos percentuais de valores absolutos de F1.

Adaptar o manuscrito ao template e ao idioma da revista. O resumo em inglês já está presente; a tradução integral deve preservar o alcance das conclusões. Abrir o Word e revisar paginação, cabeçalhos, tabelas e referências após aplicar o template.

Critério de conclusão: nenhum campo de autoria ou declaração pendente, aprovação de todos os autores e texto compatível com as regras do periódico.

## 5. Preparar o depósito público de reprodução

Responsável: autores; depósito externo depende da escolha de licença e da aprovação do conteúdo a publicar.

Definir a licença do código próprio e conferir materiais de terceiros. Não aplicar automaticamente CC BY 4.0 ao código: essa é a licença confirmada para o dataset. Revisar arquivos para evitar incluir dados pessoais, credenciais ou materiais sem autorização. O CSV pode ser obtido da fonte original; os pacotes locais não o redistribuem.

Publicar uma versão estável do código, configurações, ambiente, splits, predições e relatórios necessários à reprodução em um arquivo persistente, por exemplo Zenodo, após a revisão dos autores. Conferir os manifestos e os checksums dos pacotes antes do depósito. Obter DOI ou URL persistente e substituir o campo de disponibilidade no manuscrito. Não confundir os arquivos ZIP locais com um depósito público concluído.

Critério de conclusão: um leitor externo consegue obter os dados canônicos e executar ou verificar a análise seguindo RESEARCH_WORKFLOW.md, e o artigo aponta para a versão exata utilizada.

## 6. Fazer a conferência final e preparar a submissão

Responsável: autor correspondente, com aprovação dos coautores.

Verificar coerência entre resumo, métodos, tabelas e conclusão; confirmar que não há promessa de zero-day, detecção online, energia ou hardware que os experimentos não mediram. Preparar a carta de apresentação com a pergunta, a contribuição limitada e a adequação ao escopo. Separar figuras e arquivos suplementares conforme as instruções do periódico e anonimizar a versão de avaliação, quando exigido.

Critério de conclusão: manuscrito, suplemento, declarações, arquivo de reprodução e carta estão completos e aprovados. A submissão é uma ação posterior dos autores, não realizada nesta tarefa.

## Evolução científica além da versão atual

Para sustentar transferência a outras redes, obter dados com execuções, cenários e instante de coleta identificáveis; reservar um conjunto externo antes de examinar seus resultados. Se houver outro dataset, verificar compatibilidade de unidades, atributos, janelas e rótulos antes de construir uma tarefa de transferência. Diferentes sementes do CSV atual não resolvem essa lacuna.

Para sustentar detecção online ou embarcada, definir a janela de decisão e os atributos disponíveis nesse instante; implementar o coletor e medir atraso, custo de inferência, memória e energia no hardware pretendido. Essas atividades formam uma extensão experimental. Não são resultados presentes nem devem ser prometidas no artigo atual.

## Ordem recomendada

Primeiro, concluir a revisão científica e estatística. Em seguida, decidir sobre a ablação de A3 e escolher a revista. Depois, fechar texto, autoria e licença, realizar o depósito de reprodução e adaptar o template. Por fim, conferir o pacote e submeter. Não é necessário repetir os 310 ajustes sem uma mudança de protocolo ou uma falha que justifique isso.
