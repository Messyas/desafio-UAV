# Reprodução limpa concluída em 27-09-2026

Foi criado um clone local sem resultados em `C:/Users/User/Documents/projects/desafio-UAV-repro-20260927`, a partir do commit `b829c2ab225bd4ca3e41a27ce3aff3329b9b0f3f`. Um ambiente novo Python 3.12.14 foi instalado com `requirements-research.txt`. O CSV foi baixado novamente do Zenodo e verificado; a auditoria regenerou partições com o mesmo SHA-256 original `352d1966e2dda8060a7a59d69eafa49c461e4c2415db292319e0e1526d2996cc`.

As configurações mantiveram todos os parâmetros e receberam somente novos `experiment_id`. Nenhum treinamento foi anexado aos manifestos originais.

| Reprodução | Jobs | Hashes de predição idênticos | Maior diferença numérica após leitura | Maior diferença de F1 por fold |
|---|---:|---:|---:|---:|
| reproduction_v4_b829c2a | 150/150 | 149/150 | 0 | 0 |
| reproduction_v5_b829c2a | 150/150 | 149/150 | 4,44 × 10⁻¹⁶ | 0 |
| reproduction_v6_b829c2a | 10/10 | 10/10 | 0 | 0 |

Os dois arquivos comprimidos não idênticos foram comparados campo a campo. Nenhuma categoria mudou; diferenças numéricas não ultrapassaram a tolerância absoluta `1e-12`. O comparador preserva as divergências de hash: isso é equivalência numérica, não igualdade binária total. Dados, partições e ambiente coincidem. Os arquivos de treino no clone diferem apenas por conversão CRLF/LF do Git; cada versão foi primeiro conferida contra seu hash congelado e só depois comparada com normalização das quebras de linha. Nenhuma outra diferença de fonte foi aceita.

As análises v4/v5 e a sensibilidade v6 foram reconstruídas, assim como os relatórios gráficos v4/v5. Treze tabelas CSV coincidiram em esquema e valores dentro de tolerância absoluta `1e-12`, sem tolerância relativa. Registros detalhados: `research_artifacts/reproduction/reproduction_v*_b829c2a.json` e `analysis_table_comparison.csv`; logs completos e manifestos das novas grades estão no clone.

Testes locais originais: 54 executados, sem falhas. No clone após a reprodução: 54 descobertos, 47 executados e 7 ignorados porque verificam nomes/artefatos históricos que não foram copiados. A verificação explícita dos novos 310 jobs e 13 tabelas complementa esses testes; não tratar skips como aprovações de artefatos inexistentes.

Os três ZIPs originais foram reconstruídos com a documentação revista e verificados contra manifestos externos/internos e SHA-256 de todas as entradas por `tools/verify_research_bundle.py`. O CSV bruto não integra os pacotes. A licença específica do CSV foi confirmada como CC BY 4.0 na API do Zenodo; licença do código próprio e direitos de materiais terceiros ainda devem ser definidos antes de depósito público.

Esta reprodução valida a implementação sobre **o mesmo benchmark**. Não é validação externa, experimento confirmatório nem nova população de UAVs. Não resolve a falta de IDs de run/cenário, a disponibilidade temporal das variáveis ou a contribuição limitada frente à literatura recente.
