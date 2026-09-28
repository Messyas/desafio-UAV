# Manuscrito revisado

- `ARTIGO_UAVIDS2025_REVISADO.docx`: artigo em português, resumo em português e inglês, métodos, um quadro de configuração dos modelos, cinco tabelas de resultados, duas figuras (diagrama metodológico e comparação de qualidade/latência), discussão, conclusão e oito referências.
- `PASSOS_PARA_SUBMISSAO.docx`: sequência para revisão científica, decisão sobre a ablação adicional de A3, escolha da revista, autoria, depósito e submissão.
- Os arquivos Markdown são as fontes editoriais. Os marcadores `{{TABLE_*}}` e `{{FIGURE_*}}` são substituídos no DOCX. As figuras PNG e SVG são geradas por `tools/build_article_figures.py` a partir dos resultados versionados; não têm título interno nem linhas de grade. As legendas ficam no texto do artigo. O artigo inclui regressão logística, MLP, XGBoost e Random Forest.

Geração em Windows, sem adicionar dependências ao ambiente científico:

```powershell
& .venv-research\Scripts\python.exe tools\build_article_figures.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar as figuras do artigo.' }
& tools\build_article_documents.ps1
```

É necessário ter as tabelas verificadas em `reports/feature_ablation_v4/` e `reports/docker_latency_v4/`, reconstruídas pelo fluxo de pesquisa. O gerador usa PowerShell/.NET para criar OOXML, confere completude, suportes de classe, os oito intervalos S2, os quatro modelos medidos e a geometria das tabelas. Os hashes das fontes e dos documentos ficam em `document_checks.json`.

Os documentos usam Letter, margens de 1 polegada, estilos nativos de títulos, tabelas editáveis e numeração de página. O artigo segue `narrative_proposal` com a exceção nomeada `academic_manuscript` (Times New Roman e hierarquia preta); o plano segue `compact_reference_guide` com título simples. Não há template de periódico selecionado.

A conferência estrutural foi concluída: um quadro de configuração, cinco tabelas de resultados e duas figuras incorporadas. O DOCX foi convertido em PDF pelo LibreOffice e as 10 páginas renderizadas foram inspecionadas; as legendas permanecem junto às respectivas figuras. Revisar novamente a paginação após aplicar o template da revista.

O manuscrito deixa autoria, declarações, licença do código e endereço do depósito público explicitamente pendentes. O arquivo Word original na raiz não foi modificado. Os novos documentos não representam submissão, aceitação ou publicação de artefatos.
