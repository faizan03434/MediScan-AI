using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace MediScan.Infra.Data.Migrations
{
    /// <inheritdoc />
    public partial class DoctorRolePatientConsent : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "PatientConsents",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    PatientUserId = table.Column<string>(type: "text", nullable: false),
                    DoctorUserId = table.Column<string>(type: "text", nullable: false),
                    Status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    AllowedScanTypesJson = table.Column<string>(type: "text", nullable: true),
                    ConsentMessage = table.Column<string>(type: "text", nullable: true),
                    PatientNote = table.Column<string>(type: "text", nullable: true),
                    RequestedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    RespondedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    ExpiresAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    RevokedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_PatientConsents", x => x.Id);
                    table.ForeignKey(
                        name: "FK_PatientConsents_AspNetUsers_DoctorUserId",
                        column: x => x.DoctorUserId,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_PatientConsents_AspNetUsers_PatientUserId",
                        column: x => x.PatientUserId,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_PatientConsents_DoctorUserId",
                table: "PatientConsents",
                column: "DoctorUserId");

            migrationBuilder.CreateIndex(
                name: "IX_PatientConsents_PatientUserId_DoctorUserId",
                table: "PatientConsents",
                columns: new[] { "PatientUserId", "DoctorUserId" });

            migrationBuilder.CreateIndex(
                name: "IX_PatientConsents_Status",
                table: "PatientConsents",
                column: "Status");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "PatientConsents");
        }
    }
}
