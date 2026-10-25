using MediScan.API.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using MediScan.Core.Entities;

namespace MediScan.Tests;

public partial class AccountAccessTests
{
    private static async Task InitializeAdminRole(Fixture f)
    {
        f.Db.Roles.Add(new IdentityRole("Admin") { NormalizedName = "ADMIN" });
        await f.Db.SaveChangesAsync();
    }

    [Fact]
    public async Task OperatorBootstrapRequiresVerifiedIdentityAndNeverUpgradesPublicAccount()
    {
        await using var f = new Fixture(); await f.Initialize(); await InitializeAdminRole(f);
        await Assert.ThrowsAsync<InvalidOperationException>(() => InitialAdministratorProvisioner.ProvisionAsync(f.Db, f.Users, "admin@example.com", "LongBootstrapPassword123!", false));
        Assert.Empty(await f.Db.Users.ToListAsync());
        var regular = await f.Auth.RegisterAsync(Registration("existing@example.com"));
        await Assert.ThrowsAsync<InvalidOperationException>(() => InitialAdministratorProvisioner.ProvisionAsync(f.Db, f.Users, "existing@example.com", "LongBootstrapPassword123!", true));
        Assert.Equal("User", (await f.Users.FindByIdAsync(regular.User.Id))!.Role);
    }

    [Fact]
    public async Task BootstrapCreatesOnlyOneConfirmedAdminWithHashedPasswordAndLogin()
    {
        await using var f = new Fixture(); await f.Initialize(); await InitializeAdminRole(f);
        var id = await InitialAdministratorProvisioner.ProvisionAsync(f.Db, f.Users, "admin@example.com", "LongBootstrapPassword123!", true);
        var user = (await f.Users.FindByIdAsync(id))!;
        Assert.True(user.EmailConfirmed); Assert.Equal("Admin", user.Role); Assert.True(await f.Users.IsInRoleAsync(user, "Admin"));
        Assert.NotEqual("LongBootstrapPassword123!", user.PasswordHash);
        Assert.Equal(id, (await f.Auth.LoginAsync(new() { Email = "admin@example.com", Password = "LongBootstrapPassword123!" })).User.Id);
        await Assert.ThrowsAsync<InvalidOperationException>(() => InitialAdministratorProvisioner.ProvisionAsync(f.Db, f.Users, "second@example.com", "LongBootstrapPassword123!", true));
        Assert.Single(await f.Db.Users.ToListAsync());
    }
}
