using MediScan.Core.Entities;

namespace MediScan.Core.Interfaces;

public interface IAuditService
{
    Task LogAsync(string action, string entityType, string? entityId = null,
        string? userId = null, string? oldValues = null, string? newValues = null,
        bool success = true, string? errorMessage = null,
        string? ipAddress = null, string? userAgent = null);

    Task<List<AuditLog>> GetLogsAsync(string? userId = null, string? action = null,
        DateTime? from = null, DateTime? to = null, int page = 1, int pageSize = 50);
}
