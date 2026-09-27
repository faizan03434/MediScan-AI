using MediScan.Core.Entities;
using MediScan.Core.Services;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Infra.Data;

public class AppDbContext : IdentityDbContext<ApplicationUser>, IAppDbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<ScanRecord> ScanRecords => Set<ScanRecord>();
    public DbSet<MedicationRecord> MedicationRecords => Set<MedicationRecord>();
    public DbSet<AuditLog> AuditLogs => Set<AuditLog>();
    public DbSet<RefreshToken> RefreshTokens => Set<RefreshToken>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        // ApplicationUser
        builder.Entity<ApplicationUser>(e =>
        {
            e.Property(u => u.FullName).HasMaxLength(100).IsRequired();
            e.Property(u => u.Gender).HasMaxLength(20);
            e.Property(u => u.BloodGroup).HasMaxLength(5);
            e.Property(u => u.Role).HasMaxLength(20).HasDefaultValue("User");
        });

        // ScanRecord
        builder.Entity<ScanRecord>(e =>
        {
            e.HasKey(s => s.Id);
            e.Property(s => s.ScanType).HasConversion<string>();
            e.Property(s => s.Status).HasConversion<string>();
            e.HasOne(s => s.User)
             .WithMany(u => u.ScanRecords)
             .HasForeignKey(s => s.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(s => new { s.UserId, s.ScanType });
            e.HasIndex(s => s.CreatedAt);
            // Soft delete filter
            e.HasQueryFilter(s => !s.IsDeleted);
        });

        // MedicationRecord
        builder.Entity<MedicationRecord>(e =>
        {
            e.HasKey(m => m.Id);
            e.Property(m => m.InputMethod).HasConversion<string>();
            e.Property(m => m.DrugName).HasMaxLength(200).IsRequired();
            e.HasOne(m => m.User)
             .WithMany(u => u.MedicationRecords)
             .HasForeignKey(m => m.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasQueryFilter(m => !m.IsDeleted);
        });

        // AuditLog
        builder.Entity<AuditLog>(e =>
        {
            e.HasKey(a => a.Id);
            e.Property(a => a.Action).HasMaxLength(100).IsRequired();
            e.Property(a => a.EntityType).HasMaxLength(100).IsRequired();
            e.HasIndex(a => new { a.UserId, a.CreatedAt });
            e.HasIndex(a => a.Action);
        });

        // RefreshToken
        builder.Entity<RefreshToken>(e =>
        {
            e.HasKey(r => r.Id);
            e.Property(r => r.Token).HasMaxLength(500).IsRequired();
            e.HasOne(r => r.User)
             .WithMany()
             .HasForeignKey(r => r.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(r => r.Token).IsUnique();
        });
    }
}
