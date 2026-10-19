using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Services;

public sealed class AccountStorageService(IStorageService inner, AppDbContext db) : IStorageService
{
    public async Task<(string Url, string BlobName)> UploadAsync(Stream stream, string name, string type, string folder = "scans")
    {
        var parts = folder.Split('/');
        if (parts.Length != 2 || parts[0] is not ("scans" or "prescriptions") || string.IsNullOrWhiteSpace(parts[1]))
            throw new ArgumentException("An account-owned upload folder is required.");
        var owner = parts[1];
        await using var transaction = await db.Database.BeginTransactionAsync();
        // Hold an owner row write lock until inventory commit; deletion cannot pass an upload.
        var active = await db.Users.Where(u => u.Id == owner && u.IsActive)
            .ExecuteUpdateAsync(update => update.SetProperty(u => u.UpdatedAt, u => u.UpdatedAt));
        if (active != 1) throw new UnauthorizedAccessException("Account is inactive.");
        var stored = await inner.UploadAsync(stream, name, type, folder);
        try
        {
            db.StoredMedia.Add(new StoredMedia { BlobName = stored.BlobName, UserId = owner });
            await db.SaveChangesAsync();
            await transaction.CommitAsync();
            return stored;
        }
        catch
        {
            // Best-effort compensation; provider inventory/backup reconciliation remains operational work.
            try { await inner.DeleteAsync(stored.BlobName); } catch { }
            throw;
        }
    }
    public Task<Stream> DownloadAsync(string name) => inner.DownloadAsync(name);
    public async Task DeleteAsync(string name)
    {
        await inner.DeleteAsync(name);
        await db.StoredMedia.Where(m => m.BlobName == name).ExecuteDeleteAsync();
    }
}
