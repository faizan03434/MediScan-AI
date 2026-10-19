using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

namespace MediScan.Infra.Data;

// Serialize administrator membership decisions, including last-admin deletion.
public static class AccountMutationLock
{
    public static async Task<IDbContextTransaction> AcquireAsync(AppDbContext db)
    {
        var transaction = await db.Database.BeginTransactionAsync();
        try
        {
            if (db.Database.IsNpgsql())
                await db.Database.ExecuteSqlRawAsync("SELECT pg_advisory_xact_lock(5571871320559866961)");
            else
                await db.Database.ExecuteSqlRawAsync("UPDATE \"AspNetUsers\" SET \"Id\" = \"Id\" WHERE 1 = 0");
            return transaction;
        }
        catch { await transaction.DisposeAsync(); throw; }
    }
}
