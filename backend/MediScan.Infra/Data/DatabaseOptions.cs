using Microsoft.EntityFrameworkCore;
using Microsoft.Data.Sqlite;

namespace MediScan.Infra.Data;

public static class DatabaseOptions
{
    public static bool Configure(DbContextOptionsBuilder options, string connection, string? provider, string contentRoot)
    {
        var sqlite = IsSqlite(connection, provider);
        if (sqlite)
        {
            var settings = new SqliteConnectionStringBuilder(connection);
            if (string.IsNullOrWhiteSpace(settings.DataSource)) throw new InvalidOperationException("A SQLite database path is required.");
            if (settings.DataSource != ":memory:" && !Path.IsPathRooted(settings.DataSource))
                settings.DataSource = Path.GetFullPath(Path.Combine(contentRoot, settings.DataSource));
            options.UseSqlite(settings.ToString());
        }
        else
            options.UseNpgsql(connection, pg => pg.MigrationsAssembly("MediScan.Migrations.Postgres"));
        return sqlite;
    }
    public static bool IsSqlite(string connection, string? provider) => provider?.ToLowerInvariant() switch {
            "sqlite" => true, "postgres" or "postgresql" => false,
            null or "" => connection.TrimStart().StartsWith("Data Source=", StringComparison.OrdinalIgnoreCase),
            _ => throw new InvalidOperationException("Database provider must be sqlite or postgresql.")
        };
}
