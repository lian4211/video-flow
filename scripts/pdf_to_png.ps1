param(
  [Parameter(Mandatory=$true)][string]$PdfPath,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [int]$Width = 1920,
  [int]$Height = 1080
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime]
$null = [Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
})[0]

function AwaitOp($op, $type) {
  $m = $asTaskGeneric.MakeGenericMethod($type)
  $t = $m.Invoke($null, @($op))
  $t.Wait(-1) | Out-Null
  return $t.Result
}
function AwaitAction($action) {
  $t = $asTaskAction.Invoke($null, @($action))
  $t.Wait(-1) | Out-Null
}

if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$bytes = [System.IO.File]::ReadAllBytes($PdfPath)
$stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
$outStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForWrite($stream)
$outStream.Write($bytes, 0, $bytes.Length)
$outStream.Flush()
$stream.Seek(0) | Out-Null

$doc = AwaitOp ([Windows.Data.Pdf.PdfDocument]::LoadFromStreamAsync($stream)) ([Windows.Data.Pdf.PdfDocument])
for ($i = 0; $i -lt $doc.PageCount; $i++) {
  $page = $doc.GetPage($i)
  $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
  $opts.DestinationWidth = $Width
  $opts.DestinationHeight = $Height
  $rendered = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
  AwaitAction ($page.RenderToStreamAsync($rendered, $opts))
  $rendered.Seek(0) | Out-Null
  $net = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($rendered)
  $out = Join-Path $OutDir ("page-{0:D2}.png" -f ($i + 1))
  $fs = [System.IO.File]::Create($out)
  $net.CopyTo($fs)
  $fs.Close(); $net.Dispose(); $rendered.Dispose()
  Write-Output ("wrote " + $out)
}
$outStream.Dispose(); $stream.Dispose()
