using MediScan.Infra.Data;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace MediScan.Migrations.Postgres.Migrations;

[DbContext(typeof(AppDbContext)), Migration("20261019183000_PostgresOtpStore")]
public sealed class PostgresOtpStore : Migration
{
    protected override void Up(MigrationBuilder builder) => builder.Sql("""
        CREATE TABLE email_verification (
          scope varchar(64) PRIMARY KEY, challenge varchar(32), payload text, expires bigint NOT NULL,
          window_end bigint NOT NULL, sends integer NOT NULL, failures integer NOT NULL, cooldown bigint NOT NULL);
        CREATE INDEX ix_email_verification_challenge ON email_verification(challenge);
        """);
    protected override void Down(MigrationBuilder builder) => builder.Sql("DROP TABLE email_verification");
}
