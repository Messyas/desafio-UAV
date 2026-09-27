# Desvios do protocolo

## 7 de setembro de 2026 — suspensão de GNN

- Regra anterior: o contexto relacional/temporal integraria o núcleo se os metadados passassem pelo gate de auditabilidade.
- Regra nova: GNN e modelagem temporal não integram as próximas rodadas. Agregados relacionais tabulares permanecem apenas como possível extensão futura.
- Motivo: decisão explícita do pesquisador e ausência de timestamp, sessão, execução e identidade física verificável no CSV público.
- Efeito: E1 e a parte UAVIDS-2025 de E2 avançam; P3 não será respondida nesta versão do estudo.
- Risco: o artigo não poderá comparar diretamente o ganho arquitetural alegado por FedGraph-ID; essa diferença deve aparecer como limitação, não como resultado negativo sobre GNN.

Para cada alteração futura, registrar: data, regra anterior, regra nova, motivo, informação consultada, etapa em que ocorreu e risco de viés introduzido.

## 8 de setembro de 2026 — retirada de CNN e fechamento no benchmark Docker local

- Regra anterior: redes compactas, incluindo uma eventual CNN residual inspirada em R4, integrariam o eixo principal; Docker e `tc-netem` poderiam representar local versus borda.
- Regra nova: a versão atual compara somente Random Forest e XGBoost no benchmark de sistemas. MLP permanece como baseline exploratório, enquanto CNN, GNN, stacking, Kubernetes e `tc-netem` ficam fora. O experimento de sistemas é um benchmark HTTP local em Docker Desktop/WSL2.
- Motivo: decisão explícita do pesquisador de concentrar o artigo nos resultados tabulares já obtidos e completar uma bancada Docker local verificável.
- Informação consultada: artefatos e hashes de `deployment_candidates_v1`, resultados S0/S1/S2, tuning aninhado, estabilidade por sementes e piloto local em processo.
- Etapa: antes da execução de `docker_local_v1`.
- Risco: o artigo não poderá concluir sobre superioridade frente a CNN/GNN, rede local versus borda, hardware embarcado ou consumo energético. R4 e R2 entram apenas na contextualização e nas limitações.

## 8 de setembro de 2026 — correção de transporte após piloto Docker v1

- Regra anterior: servidor HTTP padrão com conexões persistentes; a configuração não explicitava `TCP_NODELAY`.
- Regra nova: ativar `TCP_NODELAY` em cada socket aceito e repetir integralmente ambos os modelos como `docker_local_v2`.
- Motivo: o piloto mostrou aproximadamente 45 ms de diferença constante entre latência do cliente e inferência interna nos dois modelos, compatível com Nagle/delayed ACK em mensagens pequenas. Esse custo dominava artificialmente o XGBoost.
- Informação consultada: 5.000 registros individuais por modelo do piloto `docker_local_v1`, comparando `client_duration_ns`, `server_predict_ns` e `server_queue_wait_ns`.
- Etapa: após o piloto v1 e antes de qualquer uso dos números no artigo.
- Risco: a v1 e a v2 não são combináveis; somente a v2 será tratada como benchmark final. O transporte continua sendo loopback Docker Desktop/WSL2, não uma rede UAV.

## 26 de setembro de 2026 — reorganização acadêmica e correção de agregação

- Pedido do pesquisador: retirar DVC, simplificar o repositório e manter MLflow como ferramenta útil aos experimentos.
- Mudança de escopo: identificadores, populações S0/S1/S2 e ablação dos atributos formam o núcleo. Custo em processo é complementar; Docker/HTTP deixa de ser eixo obrigatório.
- Material antigo de produção e notebooks exploratórios movidos para `archive/`. Configurações executadas, CSV bruto, splits, modelos e predições foram preservados. O plano anterior foi arquivado.
- DVC substituído por obtenção da fonte canônica e verificação SHA-256. CSV local já existente não é substituído silenciosamente.
- Problema corrigido: a normalização de `confusion_pooled_oof.csv` agrupava por protocolo/modelo/classe verdadeira, omitindo a semente. Com três sementes, cada linha somava aproximadamente 1/3 em vez de 1. A correção usa denominador independente por semente. Contagens e predições não mudam.
- Reconstrução: `tools/rebuild_metrics.py` verifica hashes e métricas por job antes de reconstruir agregados. Ambiente de treinamento histórico permanece no manifesto; ambiente/data da agregação são registrados à parte.
- Proteção nova: retomada recusa alteração de CSV ou partições, mesmo que FlowID e quantidade de linhas permaneçam iguais. Identidade também é persistida antes do primeiro job.
- MLflow recebe cópias dos jobs existentes por exportador opcional. Não seleciona modelos, não promove versões e não retreina. CSV/JSON são a fonte científica.
- Os artefatos e resultados já foram examinados. A ablação prevista é exploratória; esta revisão não cria teste intocado. Nenhum novo treinamento foi apresentado como resultado desta limpeza.
- Ambiente de verificação: Python 3.12.14, com versões científicas de `requirements-research.txt`; o `.venv` antigo referencia Python 3.12.10 em caminho indisponível.
