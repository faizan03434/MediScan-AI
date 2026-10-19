using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace MediScan.Infra.Data.Migrations
{
    /// <inheritdoc />
    public partial class AccountDeletionAndMediaInventory : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            var sqlite = ActiveProvider == "Microsoft.EntityFrameworkCore.Sqlite";
            migrationBuilder.CreateTable(
                name: "AccountDeletionJobs",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: sqlite ? "TEXT" : "uuid", nullable: false),
                    UserId = table.Column<string>(type: sqlite ? "TEXT" : "character varying(450)", maxLength: 450, nullable: true),
                    ReceiptHash = table.Column<string>(type: sqlite ? "TEXT" : "character varying(64)", maxLength: 64, nullable: false),
                    RequestedAt = table.Column<DateTime>(type: sqlite ? "TEXT" : "timestamp with time zone", nullable: false),
                    NextAttemptAt = table.Column<DateTime>(type: sqlite ? "TEXT" : "timestamp with time zone", nullable: false),
                    LeaseUntil = table.Column<DateTime>(type: sqlite ? "TEXT" : "timestamp with time zone", nullable: true),
                    LeaseToken = table.Column<string>(type: sqlite ? "TEXT" : "character varying(32)", maxLength: 32, nullable: true),
                    CompletedAt = table.Column<DateTime>(type: sqlite ? "TEXT" : "timestamp with time zone", nullable: true),
                    Attempts = table.Column<int>(type: sqlite ? "INTEGER" : "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AccountDeletionJobs", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "StoredMedia",
                columns: table => new
                {
                    BlobName = table.Column<string>(type: sqlite ? "TEXT" : "character varying(450)", maxLength: 450, nullable: false),
                    UserId = table.Column<string>(type: sqlite ? "TEXT" : "character varying(450)", maxLength: 450, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: sqlite ? "TEXT" : "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_StoredMedia", x => x.BlobName);
                });

            migrationBuilder.CreateIndex(
                name: "IX_AccountDeletionJobs_CompletedAt_NextAttemptAt",
                table: "AccountDeletionJobs",
                columns: new[] { "CompletedAt", "NextAttemptAt" });

            migrationBuilder.CreateIndex(
                name: "IX_AccountDeletionJobs_ReceiptHash",
                table: "AccountDeletionJobs",
                column: "ReceiptHash",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_AccountDeletionJobs_UserId",
                table: "AccountDeletionJobs",
                column: "UserId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_StoredMedia_UserId",
                table: "StoredMedia",
                column: "UserId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "AccountDeletionJobs");

            migrationBuilder.DropTable(
                name: "StoredMedia");
        }
    }
}
