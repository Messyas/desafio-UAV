# Registro de assistência por IA

## 7 de setembro de 2026 — auditoria inicial

- Ferramenta: OpenAI Codex.
- Escopo: estruturar o protocolo inicial, implementar `src/uavids_study/data_audit.py`, gerar o notebook de auditoria e criar testes de integridade.
- Decisões propostas pela IA e registradas para revisão humana: cinco classes como tarefa principal; `FlowID` fora dos modelos principais; S0/S1/S2 como populações distintas; bloqueio de análise temporal sem metadados; exclusão inicial de Kubernetes.
- Fontes metodológicas declaradas: artigo do dataset UAVIDS-2025; documentação de prevenção de vazamento e validação por grupos do scikit-learn; R2/FedGraph-ID como motivação condicionada para contexto; R4 como hipótese de eficiência neural; R7 como hipótese de suficiência de Random Forest e como alerta sobre possível uso de `FlowID`.
- Código de terceiros copiado: nenhum. A API pública do pandas, NumPy e scikit-learn foi usada diretamente.
- Verificação humana ainda necessária: conferir o dicionário provisório com o artigo completo e respostas dos autores; revisar se as populações S1/S2 sustentam as alegações pretendidas; confirmar as licenças de dados e códigos antes de redistribuir.

Este arquivo não transfere autoria científica para a ferramenta. Os pesquisadores continuam responsáveis por hipóteses, execução, inspeção dos resultados, interpretação, texto final e declaração de uso de IA exigida pelo veículo de publicação.

## 7 de setembro de 2026 — baseline preditivo v1

- Ferramenta: OpenAI Codex.
- Escopo: propor e implementar a configuração exploratória, o executor retomável, métricas, testes, figuras, relatório e notebook de resultados.
- Modelos executados: Dummy, regressão logística, Random Forest, Extra Trees, XGBoost, MLP compacta e a ablação diagnóstica de Random Forest com `FlowID`.
- Decisão explícita do pesquisador: suspender GNN por falta de suporte metodológico no artefato atual.
- Código de terceiros copiado: nenhum. Foram usadas as APIs instaladas do scikit-learn, XGBoost, pandas, NumPy e Matplotlib.
- Interpretação proposta pela IA e sujeita a revisão humana: repetições exatas não explicam sozinhas a qualidade alta; `FlowID` contém sinal dominante; XGBoost é o candidato inicial de melhor relação entre qualidade e tamanho; a MLP requer nova rodada porque atingiu o limite de iterações.
- Limite: os resultados são exploratórios, com uma semente e hiperparâmetros fixos. Não constituem seleção confirmatória nem benchmark de implantação.

## 7 de setembro de 2026 — tuning, estabilidade e benchmark local

- A IA implementou tuning aninhado por grupos, repetição em três sementes, congelamento dos artefatos e benchmark local em processo.
- Todos os espaços, regras de desempate e configurações foram gravados antes de suas respectivas execuções.
- A IA propôs não ampliar o tuning após o resultado externo: RF ganhou menos de 0,001 em média e XGBoost não ganhou.
- A IA propôs XGBoost como candidato operacional por qualidade média, tamanho e latência local, mantendo RF como comparador.
- Docker foi apenas verificado. Nenhuma medição de rede, container, CPU limitada, energia ou hardware embarcado foi produzida nesta etapa.
