param([Parameter(Mandatory=$true)][string]$Directory)
$ErrorActionPreference = 'Stop'
$fixturePath = [IO.Path]::GetFullPath($Directory)
$projectPath = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$allowedPath = Join-Path $projectPath '.preview/production-drills'
if (-not $fixturePath.StartsWith($allowedPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Certificate destination must be a private production-drill directory.' }
if (-not $env:MEDISCAN_DRILL_CERT_PASSWORD) { throw 'A temporary certificate password is required.' }
[IO.Directory]::CreateDirectory($fixturePath) | Out-Null
$rsa = [Security.Cryptography.RSA]::Create(2048)
try {
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=localhost', $rsa, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $names = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $names.AddDnsName('localhost'); $names.AddIpAddress([Net.IPAddress]::Loopback)
    $request.CertificateExtensions.Add($names.Build())
    $certificate = $request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5), [DateTimeOffset]::UtcNow.AddDays(1))
    try {
        [IO.File]::WriteAllBytes((Join-Path $fixturePath 'server.pfx'), $certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $env:MEDISCAN_DRILL_CERT_PASSWORD))
        $publicBytes = [Convert]::ToBase64String($certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert), [Base64FormattingOptions]::InsertLineBreaks)
        [IO.File]::WriteAllText((Join-Path $fixturePath 'public.pem'), "-----BEGIN CERTIFICATE-----`n$publicBytes`n-----END CERTIFICATE-----`n")
    } finally { $certificate.Dispose() }
} finally { $rsa.Dispose() }
Write-Output 'Private drill certificate created. No system trust store was changed.'
