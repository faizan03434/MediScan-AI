using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using MediScan.API.Controllers;
using MediScan.API.Services;
using MediScan.Core.Entities;
using MediScan.Infra.Repositories;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Tests;

public partial class AccountAccessTests
{
    private static AdminController Admin(Fixture f, ApplicationUser actor) => new(f.Db, f.Users, new AuditService(f.Db)) {
        ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext {
            User = new ClaimsPrincipal(new ClaimsIdentity([
                new Claim(ClaimTypes.NameIdentifier, actor.Id), new Claim("sst", actor.SecurityStamp!)
            ], "test")) } } };

    private static async Task<ApplicationUser> Promote(Fixture f, string id)
    {
        if (!await f.Db.Roles.AnyAsync(r => r.Name == "Admin"))
        {
            f.Db.Roles.Add(new IdentityRole("Admin") { NormalizedName = "ADMIN" });
            await f.Db.SaveChangesAsync();
        }
        var user = (await f.Users.FindByIdAsync(id))!; user.Role = "Admin";
        Assert.True((await f.Users.UpdateAsync(user)).Succeeded);
        Assert.True((await f.Users.AddToRoleAsync(user, "Admin")).Succeeded);
        return user;
    }

    [Fact]
    public async Task RefreshSecretsAreHashedAndOldStampsCannotResumeASession()
    {
        await using var f = new Fixture(); await f.Initialize();
        var response = await f.Auth.RegisterAsync(Registration());
        var stored = await f.Db.RefreshTokens.AsNoTracking().SingleAsync();
        Assert.NotEqual(response.RefreshToken, stored.Token);
        Assert.Equal(Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(response.RefreshToken))), stored.Token);
        Assert.False(string.IsNullOrEmpty(stored.SecurityStamp));
        await f.Db.Users.Where(u => u.Id == response.User.Id).ExecuteUpdateAsync(u => u.SetProperty(x => x.SecurityStamp, "new-session-stamp"));
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(response.RefreshToken));
        Assert.Single(await f.Db.RefreshTokens.ToListAsync());
    }

    [Fact]
    public async Task AdminStatusTransitionsInvalidateEveryOldSessionAndCannotReviveDeletedAccount()
    {
        await using var f = new Fixture(); await f.Initialize();
        var actor = await Promote(f, (await f.Auth.RegisterAsync(Registration("admin@example.com"))).User.Id);
        var member = await f.Auth.RegisterAsync(Registration());
        var oldStamp = (await f.Users.FindByIdAsync(member.User.Id))!.SecurityStamp;
        var controller = Admin(f, actor);
        Assert.IsType<OkObjectResult>(await controller.UpdateUserStatus(member.User.Id, new() { IsActive = false }));
        var disabled = await f.Db.Users.AsNoTracking().SingleAsync(u => u.Id == member.User.Id);
        Assert.NotEqual(oldStamp, disabled.SecurityStamp); Assert.False(disabled.IsActive);
        Assert.IsType<OkObjectResult>(await controller.UpdateUserStatus(member.User.Id, new() { IsActive = true }));
        var active = await f.Db.Users.AsNoTracking().SingleAsync(u => u.Id == member.User.Id);
        Assert.NotEqual(disabled.SecurityStamp, active.SecurityStamp);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(member.RefreshToken));
        f.Db.AccountDeletionJobs.Add(new() { UserId = member.User.Id, ReceiptHash = new string('A', 64), RequestedAt = DateTime.UtcNow, NextAttemptAt = DateTime.UtcNow });
        await f.Db.SaveChangesAsync();
        Assert.IsType<ConflictObjectResult>(await controller.UpdateUserStatus(member.User.Id, new() { IsActive = true }));
    }

    [Fact]
    public async Task AdminDemotionInvalidatesTokensAndQueuedPrivilegesAndProtectsLastAdmin()
    {
        await using var f = new Fixture(); await f.Initialize();
        var first = await Promote(f, (await f.Auth.RegisterAsync(Registration("first@example.com"))).User.Id);
        var firstController = Admin(f, first);
        Assert.IsType<ConflictObjectResult>(await firstController.UpdateUserRole(first.Id, new() { Role = "User" }));
        Assert.IsType<ConflictObjectResult>(await firstController.UpdateUserStatus(first.Id, new() { IsActive = false }));
        var second = await Promote(f, (await f.Auth.RegisterAsync(Registration("second@example.com"))).User.Id);
        var secondController = Admin(f, second);
        var session = await f.Auth.IssueTokensAsync(second.Id);
        Assert.IsType<OkObjectResult>(await firstController.UpdateUserRole(second.Id, new() { Role = "User" }));
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => f.Auth.RefreshTokenAsync(session.RefreshToken));
        Assert.IsType<UnauthorizedResult>(await secondController.UpdateUserStatus(first.Id, new() { IsActive = false }));
        Assert.True(await f.Db.Users.AsNoTracking().AnyAsync(u => u.Id == first.Id && u.IsActive && u.Role == "Admin"));
    }
}
