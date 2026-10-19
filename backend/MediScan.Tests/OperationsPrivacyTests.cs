using System.Security.Cryptography;
using MediScan.Operations;
using MediScan.Operations.Privacy;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Data.Sqlite;

namespace MediScan.Tests;

public sealed class OperationsPrivacyTests : IDisposable
{
    private readonly string root = Path.Combine(Path.GetTempPath(), "mediscan-operations-" + Guid.NewGuid().ToString("N"));
    private string PathToLedger => Path.Combine(root, "privacy", "deletions.db");
    private DeletionLedger Ledger() => new(PathToLedger, DataProtectionProvider.Create(new DirectoryInfo(Path.Combine(root, "keys"))));
    public void Dispose() { if (Directory.Exists(root)) Directory.Delete(root, true); }

    [Fact]
    public void LedgerSurvivesRestartAndNeverStoresRawIdentity()
    {
        var ledger = Ledger(); ledger.Record("private-subject-id", DateTime.UtcNow);
        ledger.Record("private-subject-id", DateTime.UtcNow);
        var reopened = Ledger().Snapshot(); Assert.Single(reopened.SubjectHashes);
        Assert.DoesNotContain("private-subject-id", System.Text.Encoding.UTF8.GetString(File.ReadAllBytes(PathToLedger)));
        Assert.Equal(DeletionLedger.SubjectHash("private-subject-id"), reopened.SubjectHashes[0]);
    }
    [Fact]
    public void TamperedLedgerFailsIntegrityValidation()
    {
        var ledger = Ledger(); ledger.Record("subject", DateTime.UtcNow);
        using var connection = new SqliteConnection($"Data Source={PathToLedger};Pooling=False"); connection.Open();
        using var command = connection.CreateCommand(); command.CommandText = "UPDATE Deletions SET RequestedTicks=RequestedTicks+1"; command.ExecuteNonQuery();
        Assert.Throws<CryptographicException>(() => ledger.Snapshot());
    }
    [Fact]
    public void RestoreRejectsUnrelatedOrOlderLedger()
    {
        var ledger = Ledger(); var old = ledger.Snapshot(); ledger.Record("subject", DateTime.UtcNow); var current = ledger.Snapshot();
        DeletionLedger.RequireCurrentLedger(old, current);
        Assert.Throws<InvalidOperationException>(() => DeletionLedger.RequireCurrentLedger(current, old));
        Assert.Throws<InvalidOperationException>(() => DeletionLedger.RequireCurrentLedger(old, new("wrong-id", [])));
    }
    [Fact]
    public void WrongKeyCannotResetLedger()
    {
        Ledger().Record("subject", DateTime.UtcNow);
        Assert.Throws<CryptographicException>(() => new DeletionLedger(PathToLedger, new EphemeralDataProtectionProvider()));
        Assert.Single(Ledger().Snapshot().SubjectHashes);
    }
    [Fact]
    public void MaintenanceCannotOverlapApiWorkers()
    {
        using (var first = RuntimeLease.Shared(root))
        using (var second = RuntimeLease.Shared(root))
            Assert.Throws<InvalidOperationException>(() => RuntimeLease.Maintenance(root));
        using (var maintenance = RuntimeLease.Maintenance(root))
            Assert.Throws<InvalidOperationException>(() => RuntimeLease.Shared(root));
        using var restored = RuntimeLease.Shared(root);
    }
}
