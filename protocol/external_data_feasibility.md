# Viabilidade de validação externa (27-09-2026)

O usuário informou que não possui scripts NS-3, configurações nem IDs das execuções que originaram o CSV. O [registro canônico](https://zenodo.org/records/15336998) fornece o CSV e a descrição do benchmark, mas não identifica ali um pacote de scripts ou IDs de run. O repositório local tampouco contém esses materiais. Isso não prova que nunca existiram; impede inferir cenários independentes a partir deste material.

O `FlowID` é sequencial, mas a ordem do CSV não valida cronologia, sessão ou execução. `SrcAddr` permite S2 com origem inédita no próprio arquivo, não valida um UAV físico nem uma simulação nova. Logo S3 fica **não executável com evidência atual**. Não dividir blocos de linhas ou criar seeds adicionais para chamá-los de cenários externos.

O [FANET Dataset NS-3.40](https://zenodo.org/records/19373220) contém cenários, traços e código, mas sua descrição é de QoS, roteamento e predição de duração de links; não oferece os cinco rótulos de intrusão do UAVIDS-2025. Não há mapeamento justificado para medir a mesma tarefa, e um F1 de classificação treinada separadamente nele não seria transferência. Outros conjuntos exigem uma tabela de correspondência de classes e atributos antes de qualquer teste.

**Decisão:** publicar, se houver tese suficiente, como auditoria de um único benchmark simulado. Uma afirmação de generalização para outros voos, simuladores, redes ou ataques requer dados novos com metadados de cenário e protocolo congelado antes de inspecionar os rótulos. Para o teste prospectivo, conservar a hipótese A0 versus A3 como pós-hoc do benchmark atual e executar somente em uma população independente adequadamente identificada.
