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
    public DbSet<PrescriptionRecord> PrescriptionRecords => Set<PrescriptionRecord>();
    public DbSet<DrugCache> DrugCaches => Set<DrugCache>();
    public DbSet<PatientConsent> PatientConsents => Set<PatientConsent>();
    public DbSet<AuditLog> AuditLogs => Set<AuditLog>();
    public DbSet<RefreshToken> RefreshTokens => Set<RefreshToken>();
    public DbSet<AccountDeletionJob> AccountDeletionJobs => Set<AccountDeletionJob>();
    public DbSet<StoredMedia> StoredMedia => Set<StoredMedia>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);
        builder.Entity<AccountDeletionJob>(e => {
            e.HasKey(j => j.Id);
            e.Property(j => j.UserId).HasMaxLength(450);
            e.Property(j => j.ReceiptHash).HasMaxLength(64).IsRequired();
            e.Property(j => j.LeaseToken).HasMaxLength(32);
            e.HasIndex(j => j.ReceiptHash).IsUnique();
            e.HasIndex(j => j.UserId).IsUnique();
            e.HasIndex(j => new { j.CompletedAt, j.NextAttemptAt });
        });
        builder.Entity<StoredMedia>(e => {
            e.HasKey(m => m.BlobName);
            e.Property(m => m.BlobName).HasMaxLength(450);
            e.Property(m => m.UserId).HasMaxLength(450).IsRequired();
            e.HasIndex(m => m.UserId);
        });

        // ── ApplicationUser ────────────────────────────────────
        builder.Entity<ApplicationUser>(e =>
        {
            e.Property(u => u.FullName).HasMaxLength(100).IsRequired();
            e.Property(u => u.Gender).HasMaxLength(20);
            e.Property(u => u.BloodGroup).HasMaxLength(5);
            e.Property(u => u.Role).HasMaxLength(20).HasDefaultValue("User");
        });

        // ── ScanRecord ─────────────────────────────────────────
        builder.Entity<ScanRecord>(e =>
        {
            e.HasKey(s => s.Id);
            e.Property(s => s.ScanType).HasConversion<string>().HasMaxLength(30);
            e.Property(s => s.Status).HasConversion<string>().HasMaxLength(20);
            e.HasOne(s => s.User)
             .WithMany(u => u.ScanRecords)
             .HasForeignKey(s => s.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(s => new { s.UserId, s.ScanType });
            e.HasIndex(s => s.CreatedAt);
            e.HasQueryFilter(s => !s.IsDeleted);
        });

        // ── MedicationRecord ───────────────────────────────────
        builder.Entity<MedicationRecord>(e =>
        {
            e.HasKey(m => m.Id);
            e.Property(m => m.InputMethod).HasConversion<string>().HasMaxLength(30);
            e.Property(m => m.DrugName).HasMaxLength(200).IsRequired();
            e.Property(m => m.GenericName).HasMaxLength(200);
            e.Property(m => m.Manufacturer).HasMaxLength(200);
            e.Property(m => m.DosageForm).HasMaxLength(50);
            e.Property(m => m.Strength).HasMaxLength(50);
            e.HasOne(m => m.User)
             .WithMany(u => u.MedicationRecords)
             .HasForeignKey(m => m.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasOne(m => m.PrescriptionRecord)
             .WithMany(p => p.Medications)
             .HasForeignKey(m => m.PrescriptionRecordId)
             .OnDelete(DeleteBehavior.SetNull)
             .IsRequired(false);
            e.HasIndex(m => new { m.UserId, m.CreatedAt });
            e.HasIndex(m => m.Barcode);
            e.HasQueryFilter(m => !m.IsDeleted);
        });

        // ── PrescriptionRecord ─────────────────────────────────
        builder.Entity<PrescriptionRecord>(e =>
        {
            e.HasKey(p => p.Id);
            e.Property(p => p.Status).HasConversion<string>().HasMaxLength(20);
            e.Property(p => p.DoctorName).HasMaxLength(100);
            e.Property(p => p.DoctorSpecialty).HasMaxLength(100);
            e.Property(p => p.ClinicName).HasMaxLength(200);
            e.HasOne(p => p.User)
             .WithMany(u => u.PrescriptionRecords)
             .HasForeignKey(p => p.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(p => new { p.UserId, p.CreatedAt });
            e.HasQueryFilter(p => !p.IsDeleted);
        });

        // ── DrugCache ──────────────────────────────────────────
        builder.Entity<DrugCache>(e =>
        {
            e.HasKey(d => d.Id);
            e.Property(d => d.NormalizedName).HasMaxLength(200).IsRequired();
            e.Property(d => d.BrandName).HasMaxLength(200).IsRequired();
            e.Property(d => d.Source).HasMaxLength(50);
            e.Property(d => d.CountryOfOrigin).HasMaxLength(5);
            e.HasIndex(d => d.NormalizedName).IsUnique(false); // multiple brands per generic
            e.HasIndex(d => d.Barcode);
        });

        // ── AuditLog ───────────────────────────────────────────
        builder.Entity<AuditLog>(e =>
        {
            e.HasKey(a => a.Id);
            e.Property(a => a.Action).HasMaxLength(100).IsRequired();
            e.Property(a => a.EntityType).HasMaxLength(100).IsRequired();
            e.HasIndex(a => new { a.UserId, a.CreatedAt });
            e.HasIndex(a => a.Action);
        });

        // ── RefreshToken ───────────────────────────────────────
        builder.Entity<RefreshToken>(e =>
        {
            e.HasKey(r => r.Id);
            e.Property(r => r.Token).HasMaxLength(500).IsRequired();
            e.Property(r => r.SecurityStamp).HasMaxLength(128);
            e.HasOne(r => r.User)
             .WithMany()
             .HasForeignKey(r => r.UserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(r => r.Token).IsUnique();
        });

        // ── PatientConsent ─────────────────────────────────────
        builder.Entity<PatientConsent>(e =>
        {
            e.HasKey(c => c.Id);
            e.Property(c => c.Status).HasConversion<string>().HasMaxLength(20);
            e.Property(c => c.PatientUserId).IsRequired();
            e.Property(c => c.DoctorUserId).IsRequired();
            e.HasOne(c => c.Patient)
             .WithMany(u => u.GrantedConsents)
             .HasForeignKey(c => c.PatientUserId)
             .OnDelete(DeleteBehavior.Cascade);
            e.HasOne(c => c.Doctor)
             .WithMany(u => u.ReceivedConsents)
             .HasForeignKey(c => c.DoctorUserId)
             .OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(c => new { c.PatientUserId, c.DoctorUserId });
            e.HasIndex(c => c.Status);
        });
    }
}
