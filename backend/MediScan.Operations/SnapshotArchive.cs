using System.IO.Compression;
using System.Text.Json;
using MediScan.Operations.Privacy;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;

namespace MediScan.Operations;

public sealed record BackupManifest(int Version, DateTime CreatedAt, string DatabasePath, LedgerSnapshot Ledger);
public sealed record RestoreResult(string Directory, int ErasedAccounts);

// Offline, same-layout SQLite snapshots. The current ledger is required separately on restore.
public sealed class SnapshotArchive
{
    public const long MaximumBytes = 10L * 1024 * 1024 * 1024;
    private const string ManifestName = ".mediscan-backup.json";
    private readonly Func<string, IDataProtectionProvider> protection;
    public SnapshotArchive(Func<string, IDataProtectionProvider> protection) => this.protection = protection;

    public void Backup(string root, string databaseRelativePath, string destination, byte[] key)
    {
        root = Path.GetFullPath(root);
        destination = Path.GetFullPath(destination);
        if (destination.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar,
            OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
            throw new ArgumentException("Backup destination must be outside the application data root.");
        if (!Directory.Exists(root)) throw new DirectoryNotFoundException("Application data root is missing.");
        var database = SafePath(root, databaseRelativePath);
        if (!File.Exists(database)) throw new FileNotFoundException("Application SQLite database is missing.");
        using var maintenance = RuntimeLease.Maintenance(root);
        var ledger = OpenLedger(root); var ledgerSnapshot = ledger.Snapshot();
        var temporary = CreateStage(Path.Combine(root, ".auth", "maintenance"));
        try
        {
            SnapshotDatabase(database, Path.Combine(temporary, "main.db"));
            var auth = Path.Combine(root, ".auth", "verification.db");
            if (File.Exists(auth)) SnapshotDatabase(auth, Path.Combine(temporary, "verification.db"));
            BackupCrypto.Encrypt(destination, key, encrypted => {
                using var archive = new ZipArchive(encrypted, ZipArchiveMode.Create, leaveOpen: true);
                using (var entry = archive.CreateEntry(ManifestName).Open())
                    JsonSerializer.Serialize(entry, new BackupManifest(1, DateTime.UtcNow, databaseRelativePath.Replace('\\', '/'), ledgerSnapshot));
                long bytes = 0; var files = 0;
                void Add(string source, string relative)
                {
                    var size = new FileInfo(source).Length;
                    bytes = checked(bytes + size);
                    if (bytes > MaximumBytes || ++files > 100000) throw new InvalidOperationException("Backup exceeds the configured local archive budget.");
                    using var input = File.OpenRead(source); using var output = archive.CreateEntry(relative, CompressionLevel.Fastest).Open(); input.CopyTo(output);
                }
                Add(Path.Combine(temporary, "main.db"), databaseRelativePath.Replace('\\', '/'));
                if (File.Exists(Path.Combine(temporary, "verification.db"))) Add(Path.Combine(temporary, "verification.db"), ".auth/verification.db");
                foreach (var folder in new[] { ".auth/keys", "wwwroot/uploads" })
                    if (Directory.Exists(SafePath(root, folder)))
                        foreach (var file in SafeFiles(SafePath(root, folder))) Add(file, Path.GetRelativePath(root, file).Replace('\\', '/'));
                foreach (var file in new[] { ".env", "appsettings.Local.json", "appsettings.json" })
                    if (File.Exists(SafePath(root, file))) Add(SafePath(root, file), "restore-configuration/" + file);
            });
        }
        finally { RemoveStage(temporary, Path.Combine(root, ".auth", "maintenance")); }
    }

    public RestoreResult Restore(string source, string currentRoot, string destinationRoot, byte[] key)
    {
        currentRoot = Path.GetFullPath(currentRoot); destinationRoot = Path.GetFullPath(destinationRoot);
        if (Directory.Exists(destinationRoot) || File.Exists(destinationRoot)) throw new InvalidOperationException("Restore requires a new, empty destination path.");
        if (new FileInfo(source).Length > MaximumBytes) throw new InvalidOperationException("Encrypted backup exceeds archive budget.");
        using var maintenance = RuntimeLease.Maintenance(currentRoot);
        var current = OpenLedger(currentRoot).Snapshot();
        var parent = Path.GetDirectoryName(destinationRoot) ?? throw new ArgumentException("Invalid restore destination.");
        Directory.CreateDirectory(parent);
        var temporary = CreateStage(parent);
        try
        {
            var zip = Path.Combine(temporary, "verified.zip"); BackupCrypto.DecryptTo(source, zip, key);
            var stage = Path.Combine(temporary, "application"); Directory.CreateDirectory(stage);
            BackupManifest manifest;
            using (var archive = ZipFile.OpenRead(zip))
            {
                var metadata = archive.GetEntry(ManifestName) ?? throw new InvalidDataException("Backup manifest is missing.");
                if (metadata.Length > 2 * 1024 * 1024) throw new InvalidDataException("Backup manifest exceeds budget.");
                using (var input = metadata.Open()) manifest = JsonSerializer.Deserialize<BackupManifest>(input) ?? throw new InvalidDataException("Invalid backup manifest.");
                if (manifest.Version != 1) throw new InvalidDataException("Unsupported backup version.");
                DeletionLedger.RequireCurrentLedger(manifest.Ledger, current);
                SafePath(stage, manifest.DatabasePath);
                var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase); long total = 0;
                if (archive.Entries.Count > 100001) throw new InvalidDataException("Too many archived files.");
                foreach (var entry in archive.Entries)
                {
                    if (entry.FullName == ManifestName) continue;
                    var name = entry.FullName;
                    if (name != manifest.DatabasePath && name != ".auth/verification.db" && !name.StartsWith(".auth/keys/", StringComparison.Ordinal)
                        && !name.StartsWith("wwwroot/uploads/", StringComparison.Ordinal) && !name.StartsWith("restore-configuration/", StringComparison.Ordinal))
                        throw new InvalidDataException("Unexpected archive entry.");
                    if (!seen.Add(name) || name.Contains('\\')) throw new InvalidDataException("Duplicate or ambiguous archive entry.");
                    total = checked(total + entry.Length); if (total > MaximumBytes) throw new InvalidDataException("Expanded backup exceeds budget.");
                    var path = SafePath(stage, name); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                    using var input = entry.Open(); using var output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                    var buffer = new byte[81920]; long written = 0; int count;
                    while ((count = input.Read(buffer)) > 0) { written += count; if (written > entry.Length) throw new InvalidDataException("Invalid archive entry length."); output.Write(buffer, 0, count); }
                    if (written != entry.Length) throw new InvalidDataException("Truncated archive entry.");
                }
            }
            var keys = SafePath(currentRoot, ".auth/keys");
            foreach (var file in SafeFiles(keys))
            {
                var target = SafePath(stage, ".auth/keys/" + Path.GetRelativePath(keys, file).Replace('\\', '/'));
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                if (File.Exists(target))
                {
                    if (!File.ReadAllBytes(target).AsSpan().SequenceEqual(File.ReadAllBytes(file))) throw new InvalidDataException("Conflicting encryption key files.");
                }
                else File.Copy(file, target);
            }
            // Copy the CURRENT ledger, never the old application-backup copy.
            var ledgerPath = SafePath(stage, ".privacy/deletions.db"); Directory.CreateDirectory(Path.GetDirectoryName(ledgerPath)!);
            SnapshotDatabase(SafePath(currentRoot, ".privacy/deletions.db"), ledgerPath);
            var erased = RestoreErasure.Apply(stage, manifest.DatabasePath, current.SubjectHashes);
            File.WriteAllText(Path.Combine(stage, "RESTORE_MANIFEST.json"), JsonSerializer.Serialize(manifest));
            Directory.Move(stage, destinationRoot);
            return new(destinationRoot, erased);
        }
        finally { RemoveStage(temporary, parent); }
    }

    private DeletionLedger OpenLedger(string root)
    {
        var path = SafePath(root, ".privacy/deletions.db");
        if (!File.Exists(path)) throw new InvalidOperationException("An independently retained current deletion ledger is required.");
        return new(path, protection(root));
    }
    internal static void SnapshotDatabase(string source, string target)
    {
        using var original = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = source, Mode = SqliteOpenMode.ReadOnly, Pooling = false }.ToString()); original.Open();
        using var copy = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = target, Pooling = false }.ToString()); copy.Open();
        original.BackupDatabase(copy);
        using var command = copy.CreateCommand(); command.CommandText = "VACUUM"; command.ExecuteNonQuery();
    }
    internal static string SafePath(string root, string relative)
    {
        var parts = relative.Replace('\\', '/').Split('/');
        if (Path.IsPathRooted(relative) || parts.Any(p => p is "" or "." or ".." || p.Contains(':') || p.Contains('\0')))
            throw new InvalidDataException("Unsafe archive or media path.");
        var current = Path.GetFullPath(root);
        if ((Directory.Exists(current) || File.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
            throw new InvalidDataException("Reparse points are not supported.");
        foreach (var part in parts)
        {
            current = Path.Combine(current, part);
            if ((File.Exists(current) || Directory.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("Reparse points are not supported.");
        }
        return current;
    }
    private static IEnumerable<string> SafeFiles(string folder)
    {
        foreach (var path in Directory.EnumerateFileSystemEntries(folder))
        {
            if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("Reparse points are not supported in snapshots.");
            if (Directory.Exists(path)) { foreach (var file in SafeFiles(path)) yield return file; }
            else yield return path;
        }
    }
    private static string CreateStage(string parent)
    {
        Directory.CreateDirectory(parent); var path = Path.Combine(parent, ".mediscan-stage-" + Guid.NewGuid().ToString("N"));
        if (OperatingSystem.IsWindows()) Directory.CreateDirectory(path);
        else Directory.CreateDirectory(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        return path;
    }
    private static void RemoveStage(string path, string expectedParent)
    {
        var full = Path.GetFullPath(path);
        if (!Path.GetFileName(full).StartsWith(".mediscan-stage-", StringComparison.Ordinal)
            || !string.Equals(Path.GetDirectoryName(full), Path.GetFullPath(expectedParent), OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)
            || Directory.Exists(full) && (File.GetAttributes(full) & FileAttributes.ReparsePoint) != 0)
            throw new InvalidOperationException("Unsafe staging cleanup target.");
        if (Directory.Exists(full)) Directory.Delete(full, recursive: true);
    }
}
