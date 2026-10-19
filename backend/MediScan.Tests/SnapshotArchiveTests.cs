using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using MediScan.API.Services;
using MediScan.Core.Entities;
using MediScan.Infra.Data;
using MediScan.Operations;
using MediScan.Operations.Privacy;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Tests;

public sealed class SnapshotArchiveTests : IDisposable
{
    private readonly string directory = Path.Combine(Path.GetTempPath(), "mediscan-backup-tests-" + Guid.NewGuid().ToString("N"));
    private readonly byte[] key = RandomNumberGenerator.GetBytes(32);
    private string Root => Path.Combine(directory, "application");
    private string Archive => Path.Combine(directory, "snapshot.msb");
    private string Restored => Path.Combine(directory, "restored");
    private static IDataProtectionProvider Protection(string root) => DataProtectionProvider.Create(new DirectoryInfo(Path.Combine(root, ".auth", "keys")), b => b.SetApplicationName("MediScan.Auth"));
    private DeletionLedger Ledger() => new(Path.Combine(Root, ".privacy", "deletions.db"), Protection(Root));
    private SnapshotArchive Service() => new(Protection);
    public void Dispose() { SqliteConnection.ClearAllPools(); if (Directory.Exists(directory)) Directory.Delete(directory, true); CryptographicOperations.ZeroMemory(key); }

    private async Task Initialize()
    {
        Directory.CreateDirectory(Root);
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite($"Data Source={Path.Combine(Root, "main.db")};Pooling=False").Options);
        await db.Database.EnsureCreatedAsync();
        db.Users.AddRange(new ApplicationUser { Id = "deleted-subject", FullName = "Private erased name", Email = "erased@example.com", SecurityStamp = "old-stamp" },
            new ApplicationUser { Id = "survivor", FullName = "Keep account", Email = "keep@example.com", SecurityStamp = "old-stamp" });
        db.ScanRecords.AddRange(new ScanRecord { UserId = "deleted-subject", ImageBlobName = "scans/deleted-subject/photo.png" },
            new ScanRecord { UserId = "survivor", ImageBlobName = "scans/deleted-subject/shared.png" });
        db.StoredMedia.Add(new StoredMedia { UserId = "deleted-subject", BlobName = "scans/deleted-subject/inventory.png" });
        db.RefreshTokens.Add(new RefreshToken { UserId = "survivor", Token = "old-private-session", ExpiresAt = DateTime.UtcNow.AddDays(1) });
        await db.SaveChangesAsync();
        foreach (var name in new[] { "photo.png", "shared.png", "inventory.png", "interrupted.tmp" })
        {
            var path = Path.Combine(Root, "wwwroot/uploads/scans/deleted-subject", name); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, "synthetic private photo");
        }
        File.WriteAllText(Path.Combine(Root, ".env"), "private-smtp-value");
        Ledger().Snapshot();
    }

    [Fact]
    public async Task EncryptedRestoreAppliesNewerDeletionLedgerAndInvalidatesAllOldSessions()
    {
        await Initialize();
        var otp = new PersistentEmailOtpStore(Path.Combine(Root, ".auth/verification.db"), TimeProvider.System, Protection(Root));
        var issued = otp.Issue("keep@example.com", "password_reset", "survivor");
        Service().Backup(Root, "main.db", Archive, key);
        var bytes = Encoding.UTF8.GetString(File.ReadAllBytes(Archive));
        Assert.DoesNotContain("Private erased name", bytes); Assert.DoesNotContain("private-smtp-value", bytes);
        Assert.DoesNotContain("synthetic private photo", bytes);
        Ledger().Record("deleted-subject", DateTime.UtcNow); // Authorized AFTER this backup was made.
        var result = Service().Restore(Archive, Root, Restored, key);
        Assert.Equal(1, result.ErasedAccounts);
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite($"Data Source={Path.Combine(Restored, "main.db")};Pooling=False").Options);
        var remaining = Assert.Single(await db.Users.ToListAsync()); Assert.Equal("survivor", remaining.Id); Assert.NotEqual("old-stamp", remaining.SecurityStamp);
        Assert.Empty(await db.RefreshTokens.ToListAsync()); Assert.Empty(await db.StoredMedia.ToListAsync()); Assert.Single(await db.ScanRecords.ToListAsync());
        Assert.False(File.Exists(Path.Combine(Restored, "wwwroot/uploads/scans/deleted-subject/photo.png")));
        Assert.False(File.Exists(Path.Combine(Restored, "wwwroot/uploads/scans/deleted-subject/inventory.png")));
        Assert.False(File.Exists(Path.Combine(Restored, "wwwroot/uploads/scans/deleted-subject/interrupted.tmp")));
        Assert.True(File.Exists(Path.Combine(Restored, "wwwroot/uploads/scans/deleted-subject/shared.png")));
        Assert.False(File.Exists(Path.Combine(Restored, ".env"))); Assert.True(File.Exists(Path.Combine(Restored, "restore-configuration/.env")));
        var restoredOtp = new PersistentEmailOtpStore(Path.Combine(Restored, ".auth/verification.db"), TimeProvider.System, Protection(Restored));
        Assert.Throws<ArgumentException>(() => restoredOtp.Consume(issued.ChallengeId, "keep@example.com", "password_reset", issued.Code));
        Assert.Equal("survivor", otp.Consume(issued.ChallengeId, "keep@example.com", "password_reset", issued.Code));
        Assert.True(File.Exists(Path.Combine(Root, "wwwroot/uploads/scans/deleted-subject/photo.png"))); // Source was not modified.
    }

    [Theory]
    [InlineData("wrong-key")] [InlineData("tamper")] [InlineData("truncate")]
    public async Task AuthenticationFailureNeverPublishesRestoredData(string failure)
    {
        await Initialize(); Service().Backup(Root, "main.db", Archive, key);
        if (failure == "tamper") { var bytes = File.ReadAllBytes(Archive); bytes[45] ^= 1; File.WriteAllBytes(Archive, bytes); }
        if (failure == "truncate") { using var file = File.OpenWrite(Archive); file.SetLength(file.Length - 10); }
        var supplied = failure == "wrong-key" ? RandomNumberGenerator.GetBytes(32) : key;
        Assert.Throws<CryptographicException>(() => Service().Restore(Archive, Root, Restored, supplied));
        Assert.False(Directory.Exists(Restored)); Assert.Empty(Directory.EnumerateDirectories(directory, ".mediscan-stage-*"));
    }

    [Fact]
    public async Task RestoreRejectsAuthenticatedZipTraversalAndExistingDestination()
    {
        await Initialize();
        BackupCrypto.Encrypt(Archive, key, stream => {
            using var zip = new ZipArchive(stream, ZipArchiveMode.Create, true);
            using (var metadata = zip.CreateEntry(".mediscan-backup.json").Open())
                JsonSerializer.Serialize(metadata, new BackupManifest(1, DateTime.UtcNow, "main.db", Ledger().Snapshot()));
            using var escape = zip.CreateEntry("wwwroot/uploads/../../../escape.txt").Open(); escape.Write("bad"u8);
        });
        Assert.Throws<InvalidDataException>(() => Service().Restore(Archive, Root, Restored, key));
        Assert.False(File.Exists(Path.Combine(directory, "escape.txt"))); Assert.False(Directory.Exists(Restored));
        Directory.CreateDirectory(Restored); File.WriteAllText(Path.Combine(Restored, "keep.txt"), "existing");
        Assert.Throws<InvalidOperationException>(() => Service().Restore(Archive, Root, Restored, key));
        Assert.Equal("existing", File.ReadAllText(Path.Combine(Restored, "keep.txt")));
    }

    [Fact]
    public async Task BackupCannotRunDuringApiActivityOrWriteIntoItsOwnSourceTree()
    {
        await Initialize(); using (var lease = RuntimeLease.Shared(Root))
            Assert.Throws<InvalidOperationException>(() => Service().Backup(Root, "main.db", Archive, key));
        Assert.Throws<ArgumentException>(() => Service().Backup(Root, "main.db", Path.Combine(Root, "self.msb"), key));
    }

    [Fact]
    public void PatchedNativeSqliteIsActuallyLoaded()
    {
        using var connection = new SqliteConnection("Data Source=:memory:"); connection.Open();
        using var command = connection.CreateCommand(); command.CommandText = "SELECT sqlite_version()";
        Assert.True(Version.Parse((string)command.ExecuteScalar()!) >= new Version(3, 50, 2));
    }
}
