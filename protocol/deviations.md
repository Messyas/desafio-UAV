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
