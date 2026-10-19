using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using MediScan.Operations;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;

if (args.Length != 4 || args[0] is not ("backup" or "restore"))
{
    Console.Error.WriteLine("backup <application-root> <relative-sqlite-file> <new-archive> | restore <archive> <current-application-root> <new-empty-root>");
    Console.Error.WriteLine("Requires MEDISCAN_BACKUP_KEY (Base64 random 32-byte key). Stop API workers before maintenance.");
    return 2;
}
byte[]? key = null;
try
{
    key = BackupCrypto.ReadKey(Environment.GetEnvironmentVariable("MEDISCAN_BACKUP_KEY"));
    var certificatePath = Environment.GetEnvironmentVariable("MEDISCAN_DATA_PROTECTION_CERTIFICATE");
    using var certificate = string.IsNullOrEmpty(certificatePath) ? null : X509CertificateLoader.LoadPkcs12FromFile(certificatePath,
        Environment.GetEnvironmentVariable("MEDISCAN_DATA_PROTECTION_CERTIFICATE_PASSWORD"), X509KeyStorageFlags.EphemeralKeySet);
    IDataProtectionProvider Protection(string root) => DataProtectionProvider.Create(new DirectoryInfo(Path.Combine(root, ".auth", "keys")), builder => {
        builder.SetApplicationName("MediScan.Auth");
        if (certificate != null) builder.UnprotectKeysWithAnyCertificate(certificate);
        if (OperatingSystem.IsWindows()) builder.ProtectKeysWithDpapi();
    });
    var snapshots = new SnapshotArchive(Protection);
    if (args[0] == "backup")
    {
        snapshots.Backup(args[1], args[2], args[3], key);
        Console.WriteLine(JsonSerializer.Serialize(new { operation = "backup", success = true }));
    }
    else
    {
        var result = snapshots.Restore(args[1], args[2], args[3], key);
        Console.WriteLine(JsonSerializer.Serialize(new { operation = "restore", success = true, erasedAccounts = result.ErasedAccounts,
            sessionsInvalidated = true, configurationRequiresReview = true }));
    }
    return 0;
}
catch (CryptographicException) { Console.Error.WriteLine("Authentication or encryption-key validation failed. No restore was published."); return 1; }
catch (Exception error) when (error is ArgumentException or IOException or InvalidOperationException or SqliteException)
{ Console.Error.WriteLine("Maintenance failed: " + error.Message); return 1; }
finally { if (key != null) CryptographicOperations.ZeroMemory(key); }
