"""Exercise compiled operator commands on a disposable, synthetic SQLite application.

Run after `dotnet build backend/MediScan.sln`. Never copies the development database.
Private drill artifacts are retained under ignored .preview/maintenance-drills/.
"""
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import uuid


def main():
    project = Path(__file__).resolve().parents[1]
    drill = project / ".preview" / "maintenance-drills" / uuid.uuid4().hex
    application = drill / "application"
    application.mkdir(parents=True)
    shutil.copyfile(project / "backend/MediScan.API/appsettings.json", application / "appsettings.json")
    api = project / "backend/MediScan.API/bin/Debug/net9.0/MediScan.API.dll"
    tool = project / "backend/MediScan.Tools/bin/Debug/net9.0/MediScan.Tools.dll"
    if not api.exists() or not tool.exists():
        raise RuntimeError("Build the backend solution before running this drill.")
    environment = dict(os.environ, ASPNETCORE_ENVIRONMENT="Development", Database__Provider="sqlite",
                       ConnectionStrings__DefaultConnection="Data Source=main.db", Jwt__Secret=secrets.token_urlsafe(64),
                       MEDISCAN_BACKUP_KEY=base64.b64encode(secrets.token_bytes(32)).decode())

    def run(name, arguments):
        result = subprocess.run(["dotnet", *map(str, arguments)], cwd=application, env=environment,
                                capture_output=True, text=True, timeout=90, check=False)
        (drill / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect private drill logs.")
        return result.stdout

    run("initialize", [api, "--contentRoot", application, "--initialize-database"])
    database = application / "main.db"
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM "AspNetUsers"').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM "AspNetRoles"').fetchone()[0] == 3
        connection.execute('''INSERT INTO "AspNetUsers" (Id,FullName,Role,IsActive,CreatedAt,EmailConfirmed,
            PhoneNumberConfirmed,TwoFactorEnabled,LockoutEnabled,AccessFailedCount,SecurityStamp)
            VALUES ('synthetic-owner','Synthetic fixture','User',1,'2026-10-19 00:00:00',0,0,0,0,0,'before-restore')''')
        connection.execute('''INSERT INTO "RefreshTokens" (Id,UserId,Token,ExpiresAt,CreatedAt,SecurityStamp)
            VALUES (1,'synthetic-owner','synthetic-session','2027-01-01','2026-10-19','before-restore')''')
    photo = application / "wwwroot/uploads/scans/synthetic-owner/fixture.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"synthetic-file-only")
    archive = drill / "snapshot.msb"
    restored = drill / "restored"
    run("backup", [tool, "backup", application, "main.db", archive])
    restore_output = run("restore", [tool, "restore", archive, application, restored])
    assert '"success":true' in restore_output
    with sqlite3.connect(restored / "main.db") as connection:
        assert connection.execute('SELECT COUNT(*) FROM "AspNetUsers"').fetchone()[0] == 1
        assert connection.execute('SELECT COUNT(*) FROM "RefreshTokens"').fetchone()[0] == 0
        assert connection.execute('SELECT SecurityStamp FROM "AspNetUsers"').fetchone()[0] != "before-restore"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert (restored / photo.relative_to(application)).read_bytes() == b"synthetic-file-only"
    assert not (restored / "appsettings.json").exists()
    assert (restored / "restore-configuration/appsettings.json").exists()
    report = {"synthetic_only": True, "bootstrap_demo_accounts": 0, "bootstrap_roles": 3,
              "cli_backup": True, "cli_restore": True, "old_sessions_invalidated": True,
              "restored_sqlite_integrity": "ok", "configuration_requires_review": True}
    (drill / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
