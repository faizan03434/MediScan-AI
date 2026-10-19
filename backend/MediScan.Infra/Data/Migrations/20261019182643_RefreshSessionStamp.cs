using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace MediScan.Infra.Data.Migrations
{
    /// <inheritdoc />
    public partial class RefreshSessionStamp : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Legacy rows contain bearer secrets and have no session stamp. Require a fresh sign-in.
            migrationBuilder.Sql("DELETE FROM \"RefreshTokens\"");
            migrationBuilder.AddColumn<string>(
                name: "SecurityStamp",
                table: "RefreshTokens",
                type: "TEXT",
                maxLength: 128,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "SecurityStamp",
                table: "RefreshTokens");
        }
    }
}
