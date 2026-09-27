using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace MediScan.Infra.Data.Migrations
{
    /// <inheritdoc />
    public partial class MedicationPrescriptionDrugCache : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_MedicationRecords_UserId",
                table: "MedicationRecords");

            migrationBuilder.AlterColumn<string>(
                name: "Status",
                table: "ScanRecords",
                type: "character varying(20)",
                maxLength: 20,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "text");

            migrationBuilder.AlterColumn<string>(
                name: "ScanType",
                table: "ScanRecords",
                type: "character varying(30)",
                maxLength: 30,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "text");

            migrationBuilder.AlterColumn<string>(
                name: "Strength",
                table: "MedicationRecords",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true,
                oldClrType: typeof(string),
                oldType: "text",
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "Manufacturer",
                table: "MedicationRecords",
                type: "character varying(200)",
                maxLength: 200,
                nullable: true,
                oldClrType: typeof(string),
                oldType: "text",
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "InputMethod",
                table: "MedicationRecords",
                type: "character varying(30)",
                maxLength: 30,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "text");

            migrationBuilder.AlterColumn<string>(
                name: "GenericName",
                table: "MedicationRecords",
                type: "character varying(200)",
                maxLength: 200,
                nullable: true,
                oldClrType: typeof(string),
                oldType: "text",
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "DosageForm",
                table: "MedicationRecords",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true,
                oldClrType: typeof(string),
                oldType: "text",
                oldNullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Contraindications",
                table: "MedicationRecords",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "HasSafetyWarning",
                table: "MedicationRecords",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<string>(
                name: "ImageBlobName",
                table: "MedicationRecords",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "PrescriptionRecordId",
                table: "MedicationRecords",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "StorageInfo",
                table: "MedicationRecords",
                type: "text",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "DrugCaches",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    NormalizedName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    Barcode = table.Column<string>(type: "text", nullable: true),
                    BrandName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    GenericName = table.Column<string>(type: "text", nullable: true),
                    Manufacturer = table.Column<string>(type: "text", nullable: true),
                    DosageForm = table.Column<string>(type: "text", nullable: true),
                    Strength = table.Column<string>(type: "text", nullable: true),
                    Indication = table.Column<string>(type: "text", nullable: true),
                    SideEffectsJson = table.Column<string>(type: "text", nullable: true),
                    WarningsJson = table.Column<string>(type: "text", nullable: true),
                    InteractionsJson = table.Column<string>(type: "text", nullable: true),
                    ContraindicationsJson = table.Column<string>(type: "text", nullable: true),
                    StorageInfo = table.Column<string>(type: "text", nullable: true),
                    CountryOfOrigin = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: true),
                    Source = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    RawResponseJson = table.Column<string>(type: "text", nullable: true),
                    FetchedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    ExpiresAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DrugCaches", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "PrescriptionRecords",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<string>(type: "text", nullable: false),
                    DoctorName = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    DoctorSpecialty = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    ClinicName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    PrescribedDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    ExpiryDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    Diagnosis = table.Column<string>(type: "text", nullable: true),
                    Notes = table.Column<string>(type: "text", nullable: true),
                    ImageUrl = table.Column<string>(type: "text", nullable: true),
                    ImageBlobName = table.Column<string>(type: "text", nullable: true),
                    OcrRawText = table.Column<string>(type: "text", nullable: true),
                    AiParsedJson = table.Column<string>(type: "text", nullable: true),
                    AiAnalysis = table.Column<string>(type: "text", nullable: true),
                    HasSafetyWarnings = table.Column<bool>(type: "boolean", nullable: false),
                    Status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    IsDeleted = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_PrescriptionRecords", x => x.Id);
                    table.ForeignKey(
                        name: "FK_PrescriptionRecords_AspNetUsers_UserId",
                        column: x => x.UserId,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_MedicationRecords_Barcode",
                table: "MedicationRecords",
                column: "Barcode");

            migrationBuilder.CreateIndex(
                name: "IX_MedicationRecords_PrescriptionRecordId",
                table: "MedicationRecords",
                column: "PrescriptionRecordId");

            migrationBuilder.CreateIndex(
                name: "IX_MedicationRecords_UserId_CreatedAt",
                table: "MedicationRecords",
                columns: new[] { "UserId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_DrugCaches_Barcode",
                table: "DrugCaches",
                column: "Barcode");

            migrationBuilder.CreateIndex(
                name: "IX_DrugCaches_NormalizedName",
                table: "DrugCaches",
                column: "NormalizedName");

            migrationBuilder.CreateIndex(
                name: "IX_PrescriptionRecords_UserId_CreatedAt",
                table: "PrescriptionRecords",
                columns: new[] { "UserId", "CreatedAt" });

            migrationBuilder.AddForeignKey(
                name: "FK_MedicationRecords_PrescriptionRecords_PrescriptionRecordId",
                table: "MedicationRecords",
                column: "PrescriptionRecordId",
                principalTable: "PrescriptionRecords",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_MedicationRecords_PrescriptionRecords_PrescriptionRecordId",
                table: "MedicationRecords");

            migrationBuilder.DropTable(
                name: "DrugCaches");

            migrationBuilder.DropTable(
                name: "PrescriptionRecords");

            migrationBuilder.DropIndex(
                name: "IX_MedicationRecords_Barcode",
                table: "MedicationRecords");

            migrationBuilder.DropIndex(
                name: "IX_MedicationRecords_PrescriptionRecordId",
                table: "MedicationRecords");

            migrationBuilder.DropIndex(
                name: "IX_MedicationRecords_UserId_CreatedAt",
                table: "MedicationRecords");

            migrationBuilder.DropColumn(
                name: "Contraindications",
                table: "MedicationRecords");

            migrationBuilder.DropColumn(
                name: "HasSafetyWarning",
                table: "MedicationRecords");

            migrationBuilder.DropColumn(
                name: "ImageBlobName",
                table: "MedicationRecords");

            migrationBuilder.DropColumn(
                name: "PrescriptionRecordId",
                table: "MedicationRecords");

            migrationBuilder.DropColumn(
                name: "StorageInfo",
                table: "MedicationRecords");

            migrationBuilder.AlterColumn<string>(
                name: "Status",
                table: "ScanRecords",
                type: "text",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "character varying(20)",
                oldMaxLength: 20);

            migrationBuilder.AlterColumn<string>(
                name: "ScanType",
                table: "ScanRecords",
                type: "text",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "character varying(30)",
                oldMaxLength: 30);

            migrationBuilder.AlterColumn<string>(
                name: "Strength",
                table: "MedicationRecords",
                type: "text",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "character varying(50)",
                oldMaxLength: 50,
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "Manufacturer",
                table: "MedicationRecords",
                type: "text",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "character varying(200)",
                oldMaxLength: 200,
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "InputMethod",
                table: "MedicationRecords",
                type: "text",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "character varying(30)",
                oldMaxLength: 30);

            migrationBuilder.AlterColumn<string>(
                name: "GenericName",
                table: "MedicationRecords",
                type: "text",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "character varying(200)",
                oldMaxLength: 200,
                oldNullable: true);

            migrationBuilder.AlterColumn<string>(
                name: "DosageForm",
                table: "MedicationRecords",
                type: "text",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "character varying(50)",
                oldMaxLength: 50,
                oldNullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_MedicationRecords_UserId",
                table: "MedicationRecords",
                column: "UserId");
        }
    }
}
