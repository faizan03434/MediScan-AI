"""Local preview only. Creates and deletes one synthetic account; never prints tokens/receipts.

Requires local seeded demo user, matching API/database, Pillow and requests. Copies only
the known demo password hash into a synthetic fixture. No SMTP bypass is added to the API.
"""
import datetime
import io
import sqlite3
import time
import uuid
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'backend/MediScan.API/mediscan_dev.db'
UPLOADS = (ROOT / 'backend/MediScan.API/wwwroot/uploads').resolve()
BASE = 'http://127.0.0.1:5000'
session = requests.Session()
session.trust_env = False
assert DATABASE.is_file(), 'Existing local development database required'
assert session.get(BASE + '/preview', timeout=10).status_code == 200, 'Development-only preview required'
assert session.get(BASE + '/api/v1/health/ready', timeout=10).status_code == 200
demo_response = session.post(BASE + '/api/v1/auth/login', json={'email': 'patient@mediscan.ai', 'password': 'Patient@1234'}, timeout=20)
demo_response.raise_for_status()
with sqlite3.connect(DATABASE) as db:
    db.row_factory = sqlite3.Row
    demo = db.execute('SELECT * FROM AspNetUsers WHERE Email=?', ('patient@mediscan.ai',)).fetchone()
    assert demo and demo['Id'] == demo_response.json()['data']['user']['id'], 'API must use this exact local fixture database'
    fixture = dict(demo)
    subject = uuid.uuid4().hex
    email = 'deletion-fixture-' + subject + '@example.invalid'
    fixture.update(Id=subject, Email=email, UserName=email, NormalizedEmail=email.upper(), NormalizedUserName=email.upper(),
                   FullName='Synthetic deletion fixture', SecurityStamp=uuid.uuid4().hex, ConcurrencyStamp=uuid.uuid4().hex,
                   MedicalHistory=None, PhoneNumber=None, Gender=None, DateOfBirth=None, WeightKg=None, HeightCm=None,
                   BloodGroup=None, Role='User', IsActive=1, LockoutEnd=None, AccessFailedCount=0, LockoutEnabled=1,
                   EmailConfirmed=1, TwoFactorEnabled=0, PhoneNumberConfirmed=0,
                   CreatedAt=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(sep=' '), UpdatedAt=None)
    columns = ','.join('"' + name + '"' for name in fixture)
    db.execute(f'INSERT INTO AspNetUsers ({columns}) VALUES ({",".join("?" for _ in fixture)})', tuple(fixture.values()))
    role = db.execute('SELECT Id FROM AspNetRoles WHERE Name=?', ('User',)).fetchone()
    assert role
    db.execute('INSERT INTO AspNetUserRoles (UserId,RoleId) VALUES (?,?)', (subject, role['Id']))

accepted = False
try:
    response = session.post(BASE + '/api/v1/auth/login', json={'email': email, 'password': 'Patient@1234'}, timeout=20)
    response.raise_for_status()
    auth = response.json()['data']
    headers = {'Authorization': 'Bearer ' + auth['accessToken']}
    photo = io.BytesIO()
    Image.new('RGB', (96, 64), '#aabbcc').save(photo, 'PNG')
    response = session.post(BASE + '/api/v1/scan', headers=headers, data={'scanType': 'SkinDisease'},
                            files={'image': ('synthetic.png', photo.getvalue(), 'image/png')}, timeout=35)
    response.raise_for_status()
    scan = response.json()['data']
    with sqlite3.connect(DATABASE) as db:
        blob = db.execute('SELECT BlobName FROM StoredMedia WHERE UserId=?', (subject,)).fetchone()[0]
    physical = (UPLOADS / blob).resolve()
    assert physical.is_relative_to(UPLOADS) and physical.is_file()
    wrong = session.post(BASE + '/api/v1/account/deletion', headers=headers,
                         json={'confirmation': 'DELETE', 'password': 'incorrect'}, timeout=20)
    assert wrong.status_code == 400
    response = session.post(BASE + '/api/v1/account/deletion', headers=headers,
                            json={'confirmation': 'DELETE', 'password': 'Patient@1234'}, timeout=20)
    assert response.status_code == 202, response.status_code
    accepted = True
    receipt = response.json()['data']['receipt']
    assert session.get(BASE + '/api/v1/auth/profile', headers=headers, timeout=10).status_code == 401
    assert session.post(BASE + '/api/v1/auth/refresh', json={'refreshToken': auth['refreshToken']}, timeout=10).status_code == 401
    status = session.post(BASE + '/api/v1/account/deletion/status', json={'receipt': receipt}, timeout=10)
    assert status.json()['data']['status'] == 'pending'
    print('PASS: synthetic upload inventoried; deletion re-authenticates and immediately invalidates account access', flush=True)
    # Advance only this synthetic job to exercise the actual background worker without a two-minute delay.
    with sqlite3.connect(DATABASE) as db:
        db.execute('UPDATE AccountDeletionJobs SET NextAttemptAt=? WHERE UserId=?',
                   ('2000-01-01 00:00:00', subject))
    deadline = time.monotonic() + 80
    while time.monotonic() < deadline:
        time.sleep(5)
        response = session.post(BASE + '/api/v1/account/deletion/status', json={'receipt': receipt}, timeout=10)
        response.raise_for_status()
        if response.json()['data']['status'] == 'completed':
            break
    else:
        raise AssertionError('Worker did not finish synthetic deletion within 80 seconds')
    with sqlite3.connect(DATABASE) as db:
        assert db.execute('SELECT COUNT(*) FROM AspNetUsers WHERE Id=?', (subject,)).fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM ScanRecords WHERE UserId=?', (subject,)).fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM StoredMedia WHERE UserId=?', (subject,)).fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM AuditLogs WHERE UserId=?', (subject,)).fetchone()[0] == 0
    assert not physical.exists()
    print('PASS: real worker removed synthetic identity, rows, inventory and physical photo; receipt reports completion')
finally:
    # After acceptance, durable cleanup owns the fixture and keeps retrying if the check failed.
    if not accepted:
        with sqlite3.connect(DATABASE) as db:
            assert db.execute('SELECT Email FROM AspNetUsers WHERE Id=?', (subject,)).fetchone()[0] == email
            blobs = db.execute('SELECT BlobName FROM StoredMedia WHERE UserId=?', (subject,)).fetchall()
            for (name,) in blobs:
                path = (UPLOADS / name).resolve()
                assert path.is_relative_to(UPLOADS)
                path.unlink(missing_ok=True)
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('DELETE FROM StoredMedia WHERE UserId=?', (subject,))
            db.execute('DELETE FROM AuditLogs WHERE UserId=?', (subject,))
            db.execute('DELETE FROM AspNetUsers WHERE Id=?', (subject,))
