using System.ComponentModel.DataAnnotations;
using MediScan.Core.Entities;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Services;

public static class InitialAdministratorProvisioner
{
    public static async Task<string> ProvisionAsync(AppDbContext db, UserManager<ApplicationUser> users,
        string email, string password, bool emailVerified)
    {
        if (!emailVerified) throw new InvalidOperationException("Verify administrator email ownership out of band before provisioning.");
        if (!new EmailAddressAttribute().IsValid(email) || password.Length < 16)
            throw new InvalidOperationException("A valid administrator email and password of at least 16 characters are required.");
        await using var transaction = await AccountMutationLock.AcquireAsync(db);
        if (await db.Users.AnyAsync(u => u.Role == "Admin"))
            throw new InvalidOperationException("Initial administrator already exists. Use authenticated administrator transfer.");
        if (await users.FindByEmailAsync(email) != null)
            throw new InvalidOperationException("Bootstrap cannot promote or replace an existing account.");
        if (!await db.Roles.AnyAsync(r => r.Name == "Admin"))
            throw new InvalidOperationException("Initialize the database roles before provisioning.");
        var user = new ApplicationUser { Email = email, UserName = email, FullName = "MediScan administrator",
            Role = "Admin", EmailConfirmed = true, IsActive = true, LockoutEnabled = true };
        if (!(await users.CreateAsync(user, password)).Succeeded)
            throw new InvalidOperationException("Administrator creation failed its identity validation.");
        if (!(await users.AddToRoleAsync(user, "Admin")).Succeeded)
            throw new InvalidOperationException("Administrator role provisioning failed.");
        await transaction.CommitAsync();
        return user.Id;
    }
}
