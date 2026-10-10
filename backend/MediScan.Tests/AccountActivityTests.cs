using System.Security.Claims;
using System.Text.Json;
using MediScan.API.Controllers;
using MediScan.Core.DTOs.Common;
using MediScan.Core.Entities;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Tests;

public class AccountActivityTests
{
    [Fact]
    public async Task ActivityIsOwnerScopedPaginatedAndExcludesSensitiveAuditFields()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        db.AuditLogs.AddRange(new AuditLog { UserId = "owner", Action = "Scan.Create", EntityType = "Scan",
            NewValues = "private medical payload", IpAddress = "private IP", ErrorMessage = "private error" },
            new AuditLog { UserId = "other", Action = "Other.Account", EntityType = "User" },
            new AuditLog { UserId = "owner", Action = "Auth.Login", EntityType = "User" });
        await db.SaveChangesAsync();
        var controller = new AccountActivityController(db) { ControllerContext = new ControllerContext {
            HttpContext = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, "owner")], "test")) } } };
        var ok = Assert.IsType<OkObjectResult>(await controller.Get(pageSize: 1));
        var response = Assert.IsType<ApiResponse<PagedResponse<AccountActivityItem>>>(ok.Value);
        Assert.Equal(2, response.Data!.TotalCount);
        Assert.Single(response.Data.Items); Assert.True(response.Data.HasNextPage);
        var json = JsonSerializer.Serialize(response);
        Assert.DoesNotContain("Other.Account", json); Assert.DoesNotContain("private", json);
        Assert.Equal("private, no-store", controller.Response.Headers.CacheControl.ToString());
        Assert.IsType<BadRequestObjectResult>(await controller.Get(page: 0));
        Assert.IsType<BadRequestObjectResult>(await controller.Get(pageSize: 100));
        controller.HttpContext.User = new ClaimsPrincipal();
        Assert.IsType<UnauthorizedResult>(await controller.Get());
    }
}
