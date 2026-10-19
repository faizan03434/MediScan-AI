param([string]$LanAddress)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$previewDir = Join-Path $projectRoot '.preview'
New-Item -ItemType Directory -Force -Path $previewDir | Out-Null
if (-not $LanAddress) {
    $socket = [System.Net.Sockets.UdpClient]::new()
    try { $socket.Connect('8.8.8.8', 80); $LanAddress = $socket.Client.LocalEndPoint.Address.ToString() }
    finally { $socket.Dispose() }
}
function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}
$apiDir = Join-Path $projectRoot 'backend/MediScan.API'
$aiDir = Join-Path $projectRoot 'ai-server'
$mobileDir = Join-Path $projectRoot 'apps/mobile'
$expoCli = Join-Path $mobileDir 'node_modules/expo/bin/cli'
if (-not (Test-Path (Join-Path $mobileDir 'node_modules/expo/bin/cli'))) {
    throw 'Install mobile dependencies first: cd apps/mobile; npm ci --legacy-peer-deps'
}
if (-not (Test-LocalPort 8001)) {
    Start-Process -FilePath (Join-Path $aiDir '.venv/Scripts/python.exe') -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8001' -WorkingDirectory $aiDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $previewDir 'ai.log') -RedirectStandardError (Join-Path $previewDir 'ai-error.log') | Out-Null
}
if (-not (Test-LocalPort 5000)) {
    $env:ASPNETCORE_ENVIRONMENT = 'Development'
    $env:AiServer__Url = 'http://127.0.0.1:8001'
    Start-Process -FilePath 'dotnet' -ArgumentList 'run','--no-build','--no-launch-profile','--urls','http://0.0.0.0:5000' -WorkingDirectory $apiDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $previewDir 'api.log') -RedirectStandardError (Join-Path $previewDir 'api-error.log') | Out-Null
}
if (Test-LocalPort 8081) {
    # A changed Wi-Fi/VPN address can leave a valid QR pointing to a manifest with an old bundle host.
    $manifest = Invoke-RestMethod -Uri 'http://127.0.0.1:8081' -Headers @{
        'expo-platform' = 'ios'; Accept = 'application/expo+json'
    } -TimeoutSec 5
    $bundleHost = ([uri]$manifest.launchAsset.url).Host
    if (-not $bundleHost) { throw 'Port 8081 did not return a usable Expo launch manifest.' }
    if ($bundleHost -and $bundleHost -ne $LanAddress) {
        $listener = Get-NetTCPConnection -LocalPort 8081 -State Listen | Select-Object -First 1
        $expoProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
        $expectedCli = $expoCli.Replace('/', '\')
        $actualCommand = ([string]$expoProcess.CommandLine).Replace('/', '\')
        if ($actualCommand.IndexOf($expectedCli, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw 'Port 8081 is owned by another process; cannot safely restart it for this preview.'
        }
        Stop-Process -Id $listener.OwningProcess
        for ($attempt = 0; $attempt -lt 50 -and (Test-LocalPort 8081); $attempt++) { Start-Sleep -Milliseconds 100 }
        if (Test-LocalPort 8081) { throw 'Previous Expo listener did not stop.' }
        Write-Host "Restarting this project's Expo server for the current network address: $LanAddress"
    }
}
if (-not (Test-LocalPort 8081)) {
    $env:REACT_NATIVE_PACKAGER_HOSTNAME = $LanAddress
    Start-Process -FilePath 'node' -ArgumentList "`"$expoCli`"",'start','--lan','--port','8081' -WorkingDirectory $mobileDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $previewDir 'expo.log') -RedirectStandardError (Join-Path $previewDir 'expo-error.log') | Out-Null
}
& node (Join-Path $PSScriptRoot 'generate_preview_qr.cjs') $LanAddress
Write-Host "Android / iPhone landing page: http://${LanAddress}:5000/preview"
Write-Host "Expo Go link: exp://${LanAddress}:8081"
Write-Host "Browser preview: http://${LanAddress}:8081"
Write-Host "API: http://${LanAddress}:5000/swagger"
Write-Host "Logs: $previewDir"
Write-Host 'Use test data only. Phone and computer must use the same Wi-Fi. Existing listeners are reused; check logs and health endpoints for version conflicts.'
