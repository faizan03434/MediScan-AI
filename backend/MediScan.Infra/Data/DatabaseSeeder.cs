using MediScan.Core.Entities;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace MediScan.Infra.Data;

/// <summary>
/// Seeds initial data: roles, admin user, test users.
/// Runs automatically on startup in Development.
/// </summary>
public static class DatabaseSeeder
{
    public static async Task SeedAsync(
        AppDbContext db,
        UserManager<ApplicationUser> userManager,
        RoleManager<IdentityRole> roleManager,
        ILogger logger)
    {
        // ── Apply pending migrations ────────────────────────
        await db.Database.MigrateAsync();
        logger.LogInformation("Database migrations applied.");

        // ── Seed Roles ──────────────────────────────────────
        string[] roles = { "Admin", "Doctor", "User" };
        foreach (var role in roles)
        {
            if (!await roleManager.RoleExistsAsync(role))
            {
                await roleManager.CreateAsync(new IdentityRole(role));
                logger.LogInformation("Role created: {Role}", role);
            }
        }

        // ── Seed Admin User ─────────────────────────────────
        const string adminEmail    = "admin@mediscan.ai";
        const string adminPassword = "Admin@1234";

        if (await userManager.FindByEmailAsync(adminEmail) == null)
        {
            var admin = new ApplicationUser
            {
                FullName  = "MediScan Admin",
                Email     = adminEmail,
                UserName  = adminEmail,
                Role      = "Admin",
                IsActive  = true,
                CreatedAt = DateTime.UtcNow,
            };
            var result = await userManager.CreateAsync(admin, adminPassword);
            if (result.Succeeded)
            {
                await userManager.AddToRoleAsync(admin, "Admin");
                logger.LogInformation("Admin user created: {Email}", adminEmail);
            }
            else
            {
                logger.LogError("Failed to create admin: {Errors}",
                    string.Join(", ", result.Errors.Select(e => e.Description)));
            }
        }

        // ── Seed Test Doctor ────────────────────────────────
        const string doctorEmail    = "doctor@mediscan.ai";
        const string doctorPassword = "Doctor@1234";

        if (await userManager.FindByEmailAsync(doctorEmail) == null)
        {
            var doctor = new ApplicationUser
            {
                FullName      = "Dr. Ali Hassan",
                Email         = doctorEmail,
                UserName      = doctorEmail,
                Role          = "Doctor",
                Gender        = "Male",
                IsActive      = true,
                CreatedAt     = DateTime.UtcNow,
            };
            var result = await userManager.CreateAsync(doctor, doctorPassword);
            if (result.Succeeded)
            {
                await userManager.AddToRoleAsync(doctor, "Doctor");
                logger.LogInformation("Doctor user created: {Email}", doctorEmail);
            }
        }

        // ── Seed Test Patient ───────────────────────────────
        const string patientEmail    = "patient@mediscan.ai";
        const string patientPassword = "Patient@1234";

        if (await userManager.FindByEmailAsync(patientEmail) == null)
        {
            var patient = new ApplicationUser
            {
                FullName    = "Ahmed Khan",
                Email       = patientEmail,
                UserName    = patientEmail,
                Role        = "User",
                Gender      = "Male",
                DateOfBirth = new DateTime(1990, 5, 15),
                WeightKg    = 75,
                HeightCm    = 175,
                BloodGroup  = "O+",
                IsActive    = true,
                CreatedAt   = DateTime.UtcNow,
            };
            var result = await userManager.CreateAsync(patient, patientPassword);
            if (result.Succeeded)
            {
                await userManager.AddToRoleAsync(patient, "User");
                logger.LogInformation("Patient user created: {Email}", patientEmail);
            }
        }

        logger.LogInformation("Database seeding complete.");
        logger.LogInformation("=== TEST CREDENTIALS ===");
        logger.LogInformation("Admin:   admin@mediscan.ai  / Admin@1234");
        logger.LogInformation("Doctor:  doctor@mediscan.ai / Doctor@1234");
        logger.LogInformation("Patient: patient@mediscan.ai / Patient@1234");
        logger.LogInformation("========================");
    }
}
