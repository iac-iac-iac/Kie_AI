$html = (Invoke-WebRequest -Uri "https://kie.ai/market" -UseBasicParsing).Content
$pattern = '/_next/static/chunks/[^"]+\.js'
$chunks = [regex]::Matches($html, $pattern) | ForEach-Object { $_.Value } | Select-Object -Unique
Write-Host "chunks: $($chunks.Count)"
$apis = New-Object System.Collections.Generic.HashSet[string]
foreach ($ch in $chunks) {
    try {
        $js = (Invoke-WebRequest -Uri "https://kie.ai$ch" -UseBasicParsing -TimeoutSec 10).Content
        [regex]::Matches($js, '/api/v1/[a-zA-Z/]+') | ForEach-Object {
            $v = $_.Value
            if ($v -match 'playground|model|market') { [void]$apis.Add($v) }
        }
    } catch {}
}
$apis | Sort-Object
