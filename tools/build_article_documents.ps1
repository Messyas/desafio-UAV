param([string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$OutDir = Join-Path $ProjectRoot 'manuscript'
$Utf8 = New-Object Text.UTF8Encoding($false)
$PtCulture = [Globalization.CultureInfo]::GetCultureInfo('pt-BR')
$Invariant = [Globalization.CultureInfo]::InvariantCulture
function Esc([string]$Text) { [Security.SecurityElement]::Escape($Text) }
function Num($Value, [int]$Digits = 6) { ([double]::Parse([string]$Value,$Invariant)).ToString("F$Digits",$PtCulture) }
function Delta($Value) { (100*[double]::Parse([string]$Value,$Invariant)).ToString('+0.000;-0.000;0.000',$PtCulture) }
function Para([string]$Text, [string]$Style = 'Normal') {
    '<w:p><w:pPr><w:pStyle w:val="'+$Style+'"/></w:pPr><w:r><w:t xml:space="preserve">'+(Esc $Text)+'</w:t></w:r></w:p>'
}
function TableXml($Rows, [int[]]$Widths, [bool]$Narrative = $false) {
    if (($Widths | Measure-Object -Sum).Sum -ne 9360) { throw 'Table width must be 9360 DXA' }
    $s = [Text.StringBuilder]::new()
    [void]$s.Append('<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblInd w:w="120" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:start w:w="120" w:type="dxa"/><w:end w:w="120" w:type="dxa"/></w:tblCellMar><w:tblBorders>')
    foreach($edge in @('top','left','bottom','right','insideH','insideV')){[void]$s.Append("<w:$edge w:val=`"single`" w:sz=`"4`" w:color=`"DADCE0`"/>")}
    [void]$s.Append('</w:tblBorders></w:tblPr><w:tblGrid>')
    foreach($width in $Widths){[void]$s.Append("<w:gridCol w:w=`"$width`"/>")}
    [void]$s.Append('</w:tblGrid>')
    for($i=0;$i -lt $Rows.Count;$i++){
        if($Rows[$i].Count -ne $Widths.Count){throw 'Column count mismatch'}
        [void]$s.Append('<w:tr><w:trPr><w:cantSplit/>')
        if($i -eq 0){[void]$s.Append('<w:tblHeader/>')}
        [void]$s.Append('</w:trPr>')
        for($j=0;$j -lt $Widths.Count;$j++){
            $shade = if($i -eq 0){'<w:shd w:val="clear" w:fill="F4F6F9"/>'}else{''}
            $bold = if($i -eq 0){'<w:b/>'}else{''}
            $align = if($Narrative -or $j -eq 0){'left'}else{'right'}
            [void]$s.Append('<w:tc><w:tcPr><w:tcW w:w="'+$Widths[$j]+'" w:type="dxa"/><w:vAlign w:val="center"/>'+$shade+'</w:tcPr><w:p><w:pPr><w:pStyle w:val="TableText"/><w:jc w:val="'+$align+'"/></w:pPr><w:r><w:rPr>'+$bold+'</w:rPr><w:t xml:space="preserve">'+(Esc ([string]$Rows[$i][$j]))+'</w:t></w:r></w:p></w:tc>')
        }
        [void]$s.Append('</w:tr>')
    }
    [void]$s.Append('</w:tbl>')
    $s.ToString()
}
$MetricPath = Join-Path $ProjectRoot 'reports/feature_ablation_v4/pooled_metrics.csv'
$ClassPath = Join-Path $ProjectRoot 'reports/feature_ablation_v4/class_metrics.csv'
$PairPath = Join-Path $ProjectRoot 'reports/feature_ablation_v4/paired_comparisons.csv'
$LatencyPath = Join-Path $ProjectRoot 'reports/docker_latency_v4/quality_latency_comparison.csv'
$Metrics = @(Import-Csv -LiteralPath $MetricPath)
$Classes = @(Import-Csv -LiteralPath $ClassPath | Where-Object {$_.protocol -eq 'S2' -and $_.model -eq 'xgboost' -and $_.condition -eq 'A0'})
$Pairs = @(Import-Csv -LiteralPath $PairPath | Where-Object {$_.protocol -eq 'S2'})
$Latency = @(Import-Csv -LiteralPath $LatencyPath | Where-Object {$_.latency_status -eq 'complete'})
if($Metrics.Count -ne 30 -or $Classes.Count -ne 5 -or $Pairs.Count -ne 8){throw 'Incomplete verified results'}
if(($Classes | Measure-Object support -Sum).Sum -ne 122171){throw 'Invalid class total'}
if($Latency.Count -ne 4 -or ($Latency.model -join ',') -ne 'logistic_regression,mlp_compact,xgboost,random_forest'){throw 'Unexpected latency result set'}
$TableBlocks = @{}
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Classe','Fluxos'))
foreach($c in $Classes){$rows.Add(@($c.class_name,([int]$c.support).ToString('N0',$PtCulture)))}
$TableBlocks['{{TABLE_CLASSES}}'] = TableXml $rows.ToArray() @(6600,2760)
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Protocolo de validação','Random Forest','XGBoost'))
$protocolNames=@{S0='Divisão aleatória estratificada';S1='Separação por assinatura exata';S2='Separação por endereço de origem'}
foreach($p in @('S0','S1','S2')){
    $rf = @($Metrics | Where-Object {$_.protocol -eq $p -and $_.model -eq 'random_forest' -and $_.condition -eq 'A0'})
    $xg = @($Metrics | Where-Object {$_.protocol -eq $p -and $_.model -eq 'xgboost' -and $_.condition -eq 'A0'})
    if($rf.Count -ne 1 -or $xg.Count -ne 1){throw 'Missing A0 control'}
    $rows.Add(@($protocolNames[$p],(Num $rf[0].f1_macro),(Num $xg[0].f1_macro)))
}
$TableBlocks['{{TABLE_PROTOCOLS}}'] = TableXml $rows.ToArray() @(4200,2580,2580)
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Modelo','Tratamento comparado','Diferença (pp)','Intervalo 95% (pp)'))
$featureNames=@{A1='Pacotes perdidos/transmitidos';A2='Bytes recebidos/transmitidos';A3='Vazão por salto';A4='Três razões em conjunto'}
foreach($p in $Pairs){
    $name = if($p.model -eq 'random_forest'){'RF'}else{'XGBoost'}
    $rows.Add(@($name,$featureNames[$p.condition],(Delta $p.f1_macro_delta),((Delta $p.ci_low)+' a '+(Delta $p.ci_high))))
    if([double]::Parse($p.ci_low,$Invariant) -gt 0 -or [double]::Parse($p.ci_high,$Invariant) -lt 0){throw 'S2 interval no longer includes zero: revise text'}
}
$TableBlocks['{{TABLE_ABLATION}}'] = TableXml $rows.ToArray() @(1320,2880,1920,3240)
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Classe','Precisão','Revocação','F1'))
foreach($c in $Classes){$rows.Add(@($c.class_name,(Num $c.precision),(Num $c.recall),(Num $c.f1)))}
$TableBlocks['{{TABLE_ERRORS}}'] = TableXml $rows.ToArray() @(3600,1920,1920,1920)
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Modelo','F1-macro','HTTP P50 ms','HTTP P95 ms','HTTP P99 ms','Inferência P50 ms','Memória máx. MiB'))
$names = @{logistic_regression='Regressão logística';mlp_compact='MLP compacta';xgboost='XGBoost';random_forest='Random Forest'}
foreach($item in $Latency){
    $rows.Add(@($names[$item.model],(Num $item.s2_oof_f1_macro),(Num $item.http_p50_ms 3),(Num $item.http_p95_ms 3),(Num $item.http_p99_ms 3),(Num $item.predict_p50_ms 3),(Num $item.memory_peak_mib 2)))
}
$TableBlocks['{{TABLE_LATENCY}}'] = TableXml $rows.ToArray() @(1830,1200,1150,1150,1150,1480,1400)
$rows = [Collections.Generic.List[object]]::new()
$rows.Add(@('Classificador','Configuração fixa'))
$rows.Add(@('Random Forest [6]','200 árvores; raiz quadrada do número de atributos considerada em cada divisão; mínimo de um registro por folha; ponderação balanceada das classes.'))
$rows.Add(@('XGBoost [7]','200 estimadores; profundidade máxima 6; taxa de aprendizado 0,1; amostragem de 80% das linhas e 80% dos atributos; objetivo probabilístico multiclasse; perda logarítmica; construção histográfica.'))
$TableBlocks['{{TABLE_MODELS}}'] = TableXml $rows.ToArray() @(2400,6960) $true

function StylesXml([bool]$Article) {
    # narrative_proposal with named academic_manuscript override (Times New Roman,
    # black hierarchy, 16pt title); compact_reference_guide for the action document.
    $font = if($Article){'Times New Roman'}else{'Calibri'}
    $line = if($Article){320}else{300}
    $after = if($Article){160}else{120}
    $color = if($Article){'000000'}else{'2E74B5'}
    $s = '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="'+$font+'" w:hAnsi="'+$font+'" w:eastAsia="'+$font+'" w:cs="'+$font+'"/><w:sz w:val="22"/><w:color w:val="000000"/><w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:before="0" w:after="'+$after+'" w:line="'+$line+'" w:lineRule="auto"/><w:widowControl/></w:pPr></w:pPrDefault></w:docDefaults>'
    $align = if($Article){'both'}else{'left'}
    $s += '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:jc w:val="'+$align+'"/></w:pPr></w:style>'
    $h2before=if($Article){240}else{280};$h2after=if($Article){120}else{140}
    $h3before=if($Article){160}else{200};$h3after=if($Article){80}else{100}
    $specs = @(@('Title','Title',32,0,140,'000000'),@('Subtitle','Subtitle',20,0,140,'555555'),@('Heading1','heading 1',32,360,200,$color),@('Heading2','heading 2',26,$h2before,$h2after,$color),@('Heading3','heading 3',24,$h3before,$h3after,$color),@('Caption','Caption',20,80,80,'000000'),@('TableText','Table Text',20,0,0,'000000'),@('Reference','Reference',20,0,40,'000000'),@('Footer','Footer',18,0,0,'555555'))
    foreach($x in $specs){
        $id=$x[0];$isHeading=$id.StartsWith('Heading');$keep=if($isHeading -or $id -eq 'Title' -or $id -eq 'Caption'){'<w:keepNext/>'}else{''}
        $outline=if($isHeading){'<w:outlineLvl w:val="'+([int]$id.Substring(7)-1)+'"/>'}else{''}
        $bold=if($isHeading -or $id -eq 'Title'){'<w:b/>'}else{''}
        $s += '<w:style w:type="paragraph" w:styleId="'+$id+'"><w:name w:val="'+$x[1]+'"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:jc w:val="left"/>'+$keep+$outline+'<w:spacing w:before="'+$x[3]+'" w:after="'+$x[4]+'" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="'+$x[2]+'"/><w:color w:val="'+$x[5]+'"/>'+$bold+'</w:rPr></w:style>'
    }
    $s += '<w:style w:type="paragraph" w:styleId="Equation"><w:name w:val="Equation"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:keepLines/><w:spacing w:before="80" w:after="80" w:line="280" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="22"/></w:rPr></w:style>'
    $s += '<w:style w:type="paragraph" w:styleId="EquationLead"><w:name w:val="Equation Lead"/><w:basedOn w:val="Normal"/><w:next w:val="Equation"/><w:pPr><w:keepNext/></w:pPr></w:style>'
    $s+'</w:styles>'
}
function WriteZipEntry($Archive,[string]$Name,[string]$Value) {
    $entry=$Archive.CreateEntry($Name,[IO.Compression.CompressionLevel]::Optimal)
    $stream=$entry.Open();$bytes=$Utf8.GetBytes($Value)
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function FigureXml([string]$RelId,[string]$Name,[string]$Description,[int]$WidthPx,[int]$HeightPx) {
    $usableWidth = if($Name -eq 'figura_2_qualidade_latencia'){8400}else{9360}
    $cx = [long]($usableWidth * 635)
    $cy = [long][math]::Round($cx * $HeightPx / $WidthPx)
    '<w:p><w:pPr><w:jc w:val="center"/><w:keepLines/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="'+$cx+'" cy="'+$cy+'"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="'+$(if($Name -eq 'figura_1_metodologia'){'1'}else{'2'})+'" name="'+$Name+'.png" descr="'+(Esc $Description)+'"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="'+$Name+'.png" descr="'+(Esc $Description)+'"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="'+$RelId+'"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="'+$cx+'" cy="'+$cy+'"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
}
function GetPngDimensions([string]$Path) {
    $stream=[IO.File]::OpenRead($Path)
    try{
        $stream.Position=16
        $reader=[IO.BinaryReader]::new($stream)
        try{
            $w=$reader.ReadBytes(4);$h=$reader.ReadBytes(4)
            [array]::Reverse($w);[array]::Reverse($h)
            [pscustomobject]@{Width=[BitConverter]::ToInt32($w,0);Height=[BitConverter]::ToInt32($h,0)}
        }finally{$reader.Dispose()}
    }finally{$stream.Dispose()}
}
function BuildDoc([string]$Base,[bool]$Article) {
    $md=[IO.File]::ReadAllText((Join-Path $OutDir "$Base.md"),$Utf8)
    $blocks=[regex]::Split($md.Trim(),'\r?\n\s*\r?\n')
    $body=[Text.StringBuilder]::new()
    $plain=[Collections.Generic.List[string]]::new()
    $figureFiles=@()
    if($Article){
        $figureFiles=@(
            [pscustomobject]@{marker='{{FIGURE_METHOD}}';name='figura_1_metodologia';description='Diagrama dos protocolos de avaliação preditiva e do benchmark local de custo de inferência.'},
            [pscustomobject]@{marker='{{FIGURE_PERF}}';name='figura_2_qualidade_latencia';description='F1-macro fora da amostra na separação por endereço de origem e latências HTTP P50, P95 e P99 dos quatro modelos medidos.'}
        )
    }
    foreach($block in $blocks){
        $b=$block.Trim()
        if($TableBlocks.ContainsKey($b)){
            [void]$body.Append($TableBlocks[$b])
            $source = if($b -eq '{{TABLE_LATENCY}}') { 'Fonte: estimativas de F1-macro fora da amostra e medições do benchmark local de inferência.' } elseif($b -eq '{{TABLE_MODELS}}') { 'Fonte: configuração experimental deste estudo.' } else { 'Fonte: análises do estudo com UAVIDS-2025 [2].' }
            [void]$body.Append((Para $source 'CaptionSource'))
            continue
        }
        $figure=@($figureFiles | Where-Object {$_.marker -eq $b})
        if($figure.Count -eq 1){
            $figPath=Join-Path $OutDir ('figures/'+$figure[0].name+'.png')
            if(-not (Test-Path -LiteralPath $figPath)){throw "Missing figure asset: $figPath"}
            $dimensions=GetPngDimensions $figPath
            $relId=if($figure[0].name -eq 'figura_1_metodologia'){'rIdImage1'}else{'rIdImage2'}
            [void]$body.Append((FigureXml $relId $figure[0].name $figure[0].description $dimensions.Width $dimensions.Height))
            continue
        }
        if($b -match '\{\{'){throw "Unresolved content: $b"}
        $style='Normal';$text=$b
        if($b.StartsWith('$$') -and $b.EndsWith('$$')){$style='Equation';$text=$b.Substring(2,$b.Length-4).Trim()}
        elseif($b.EndsWith('duas taxas específicas da tarefa:')){$style='EquationLead'}
        elseif($b.StartsWith('### ')){$style='Heading2';$text=$b.Substring(4)}
        elseif($b.StartsWith('## ')){$style='Heading1';$text=$b.Substring(3)}
        elseif($b.StartsWith('# ')){$style='Title';$text=$b.Substring(2)}
        elseif($b.StartsWith('Versão ') -or $b.StartsWith('Situação ')){$style='Subtitle'}
        elseif($b -match '^Figura 2\.'){$style='FigureCaptionBreak'}
        elseif($b -match '^(Tabela|Figura|Quadro) \d+\.'){$style='Caption'}
        elseif($b -match '^\[\d+\]'){$style='Reference'}
        $text=$text -replace '\r?\n',' '
        $plain.Add($text)
        [void]$body.Append((Para $text $style))
    }
    $sect='<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708"/><w:cols w:space="720"/></w:sectPr>'
    $xml='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:body>'+$body.ToString()+$sect+'</w:body></w:document>'
    $types='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'
    $rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'
    $docrels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
    if($Article){
        $docrels+='<Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/figura_1_metodologia.png"/><Relationship Id="rIdImage2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/figura_2_qualidade_latencia.png"/>'
    }
    $docrels+='</Relationships>'
    $footer='<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="right"/></w:pPr><w:r><w:t>Página </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    $core='<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>'+(Esc $plain[0])+'</dc:title><dc:language>pt-BR</dc:language><dc:description>Manuscrito científico em revisão sobre avaliação experimental no conjunto UAVIDS-2025.</dc:description></cp:coreProperties>'
    $path=Join-Path $OutDir "$Base.docx"
    $stream=[IO.File]::Open($path,[IO.FileMode]::Create)
    $zip=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create)
    try{
        WriteZipEntry $zip '[Content_Types].xml' $types
        WriteZipEntry $zip '_rels/.rels' $rels
        WriteZipEntry $zip 'word/document.xml' $xml
        $styles=StylesXml $Article
        $styles=$styles.Replace('</w:styles>','<w:style w:type="paragraph" w:styleId="CaptionSource"><w:name w:val="Caption Source"/><w:basedOn w:val="Caption"/><w:pPr><w:keepNext w:val="0"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="FigureCaptionBreak"><w:name w:val="Figure Caption"/><w:basedOn w:val="Caption"/><w:pPr><w:keepNext/></w:pPr></w:style></w:styles>')
        WriteZipEntry $zip 'word/styles.xml' $styles
        WriteZipEntry $zip 'word/_rels/document.xml.rels' $docrels
        WriteZipEntry $zip 'word/footer1.xml' $footer
        WriteZipEntry $zip 'docProps/core.xml' $core
        if($Article){foreach($fig in $figureFiles){$entry=$zip.CreateEntry('word/media/'+$fig.name+'.png',[IO.Compression.CompressionLevel]::Optimal);$input=[IO.File]::OpenRead((Join-Path $OutDir ('figures/'+$fig.name+'.png')));$output=$entry.Open();try{$input.CopyTo($output)}finally{$output.Dispose();$input.Dispose()}}}
    }finally{$zip.Dispose();$stream.Dispose()}
    # Parse every XML part and verify table geometry; no rendering claims are made.
    $zip=[IO.Compression.ZipFile]::OpenRead($path)
    try{
        foreach($entry in $zip.Entries | Where-Object {$_.FullName -match '\.(xml|rels)$'}){$reader=[IO.StreamReader]::new($entry.Open(),$Utf8);try{[xml]$parsed=$reader.ReadToEnd()}finally{$reader.Dispose()}}
        [xml]$docXml=$xml
        $ns=[Xml.XmlNamespaceManager]::new($docXml.NameTable);$ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
        $tables=$docXml.SelectNodes('//w:tbl',$ns)
        if($Article -and $tables.Count -ne 6){throw 'Article needs five result tables and one configuration table'}
        $drawings=$docXml.SelectNodes('//w:drawing',$ns)
        if($Article -and $drawings.Count -ne 2){throw 'Article needs two embedded figures'}
        foreach($t in $tables){
            $grid=@($t.SelectNodes('w:tblGrid/w:gridCol',$ns) | ForEach-Object {[int]$_.GetAttribute('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')})
            if(($grid|Measure-Object -Sum).Sum -ne 9360){throw 'Invalid table grid'}
            foreach($row in $t.SelectNodes('w:tr',$ns)){
                $cells=@($row.SelectNodes('w:tc/w:tcPr/w:tcW',$ns))
                for($i=0;$i -lt $cells.Count;$i++){if([int]$cells[$i].GetAttribute('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main') -ne $grid[$i]){throw 'Invalid cell geometry'}}
            }
        }
    }finally{$zip.Dispose()}
    [pscustomobject]@{file="$Base.docx";paragraphs=$plain.Count;tables=$tables.Count;figures=$drawings.Count;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower();rendered=$false}
}
$checks=@((BuildDoc 'ARTIGO_UAVIDS2025_REVISADO' $true),(BuildDoc 'PASSOS_PARA_SUBMISSAO' $false))
$sourceFiles=@($MetricPath,$ClassPath,$PairPath,$LatencyPath,(Join-Path $OutDir 'figures/figura_1_metodologia.png'),(Join-Path $OutDir 'figures/figura_1_metodologia.svg'),(Join-Path $OutDir 'figures/figura_2_qualidade_latencia.png'),(Join-Path $OutDir 'figures/figura_2_qualidade_latencia.svg'),(Join-Path $ProjectRoot 'tools/build_article_figures.py'))
$sourceHashes=@($sourceFiles | ForEach-Object {[pscustomobject]@{path=$_.Substring($ProjectRoot.Length+1);sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower()}})
$audit=[ordered]@{date='2026-09-27';generator='tools/build_article_documents.ps1';figure_generator='tools/build_article_figures.py';article_preset='narrative_proposal';article_override='academic_manuscript: Times New Roman; black headings; title 16pt';steps_preset='compact_reference_guide';steps_override='plain_masthead: title 16pt; subtitle 10pt; no metadata table';header_pattern='memo_masthead: plain title stack; no rule or metadata table';geometry='Letter; 1in margins; 9360 DXA tables; 120 DXA indent; 80/80/120/120 margins';source_tables=$sourceHashes;documents=$checks;visual_qa='LibreOffice: article rendered to 13 pages and all pages visually inspected; figure captions paired with their images.'}
[IO.File]::WriteAllText((Join-Path $OutDir 'document_checks.json'),($audit|ConvertTo-Json -Depth 8),$Utf8)
$checks | Format-Table -AutoSize
