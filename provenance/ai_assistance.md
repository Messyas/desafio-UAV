# Registro de assistência por IA

## Benchmark Docker local

Em 8 de setembro de 2026, a assistência por IA foi usada para estruturar o serviço HTTP mínimo, o gerador de carga, a coleta de `docker stats`, as verificações de hash e a documentação do protocolo Docker local. O código não foi copiado dos notebooks de terceiros nem apresentado como implementação oficial de artigo externo.

O pesquisador decidiu retirar CNN, GNN, stacking, Kubernetes e emulação de rede do escopo. Os modelos, atributos, classes e hashes vieram exclusivamente dos artefatos já congelados no projeto. Um piloto v1 revelou cerca de 45 ms de overhead de transporte; a assistência identificou o padrão Nagle/delayed ACK, registrou o desvio e a rodada integral foi repetida como v2 com `TCP_NODELAY`. Apenas a v2 é usada como resultado.

Limites interpretativos foram mantidos no código e nos relatórios: a bancada não mede energia, bateria, rádio, ARM, tempo até detecção ou um UAV físico.
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

## 26 de setembro de 2026 — reorganização do estudo

- Ferramenta: OpenAI Codex; assistência na revisão de estrutura, implementação e documentação.
- Pedido do pesquisador: limpar o repositório, retirar DVC, usar MLflow como apoio e planejar experimentação acadêmica revisada.
- Trabalho: arquivo histórico em `archive/`, ambiente `.venv-research`, obtenção do dataset com checksum, exportação opcional de tracking, reconstrução de métricas e proteção da retomada por identidade dos dados/splits.
- Correção metodológica: normalização de confusão OOF agora usa população separada por semente; predições brutas não foram modificadas.
- Plano proposto: cinco classes principais; ablação de três atributos com controles pareados e parâmetros do baseline fixos; análise de grupos e limites da exposição histórica; Docker complementar.
- Fontes de API: documentação oficial de tracking do MLflow e documentação de validação cruzada do scikit-learn 1.5. Nenhum código de notebook de terceiro foi copiado.
- Verificações: testes de integridade e casos sintéticos, checksums dos 105 jobs do baseline e validação das métricas salvas. A ablação ainda não foi implementada/executada.
- Revisão científica pendente: contribuição frente à literatura, semântica/causalidade dos atributos, método de incerteza, dados externos e veículo de publicação.

## 26 de setembro de 2026 — implementação da ablação revisada

- Ferramenta: OpenAI Codex, a pedido do pesquisador para implementar o ciclo antes da redação de novo artigo.
- Trabalho: transformação clonável no pipeline; imputação exclusivamente no treino; executor A0–A4 com controles RF/XGBoost fixos; configurações distintas de estabilidade e recorte de PacketDropRate; bootstrap pareado por grupos; análise verificada, gráficos exportáveis, pacote local e tracking opcional com condição registrada.
- Controles: A0 retreinado no novo contrato, hashes do baseline e do experimento, alinhamento por linha/fold/classe, cobertura OOF, recusa de retomada quando dados, código ou ambiente diferem. Documento Word histórico não foi reescrito e suas instruções não foram tratadas como pedido do pesquisador.
- Verificações: testes sintéticos de fórmulas, extremos, imputação sem acesso ao teste, grupos desiguais, predições idênticas, vazamento, corrupção, retomada sem ajuste e sensibilidade pareada. Execução real e cobertura estão nos manifestos de results/feature_ablation_v4/; não confundir dados sintéticos com resultados empíricos.
- Achados descritivos da auditoria: loss_ratio é quase redundante com PacketDropRate; throughput_per_hop fica ausente em 38.501 linhas. Esses fatos enfraquecem interpretações de novidade/semântica automática das razões.
- Fonte de API: documentação oficial do scikit-learn 1.5 para estimadores e SimpleImputer; nenhuma implementação de artigo externo foi copiada.
- Limites: intervalos condicionais às predições fixas, sementes não independentes, grupos operacionais sem sessões confiáveis, estudo exploratório, necessidade de revisão humana de literatura/método e reprodução em ambiente limpo. O pacote local não publica nem redistribui o CSV bruto.
- Resultado desta execução assistida: 150/150 jobs v4, 150/150 v5 e 10/10 v6; 54 testes passaram. Controle A0 v4 apresentou igualdade exata com os 30 jobs históricos correspondentes; 50 jobs da semente compartilhada v4/v5 também produziram predições iguais. Pacotes locais foram verificados por hashes e não foram publicados. Nota interpretativa em protocol/evidence_review.md; o achado geral não justifica anunciar superioridade da engenharia de atributos.
