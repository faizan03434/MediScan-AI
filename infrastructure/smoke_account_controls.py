"""Local development only: exports seeded demo records and revokes demo patient sessions.

Never prints exported health data or tokens. Does not delete records or send emails.
"""
import requests

session = requests.Session()
session.trust_env = False
base = 'http://127.0.0.1:5000/api/v1'


def login(email, password):
    response = session.post(base + '/auth/login', json={'email': email, 'password': password}, timeout=20)
    response.raise_for_status()
    return response.json()['data']


owner = login('patient@mediscan.ai', 'Patient@1234')
other = login('doctor@mediscan.ai', 'Doctor@1234')
headers = {'Authorization': 'Bearer ' + owner['accessToken']}
for section in ('profile', 'scans', 'medications', 'prescriptions', 'consents'):
    response = session.get(base + '/account/export/' + section, headers=headers,
                           params={'pageSize': 1}, timeout=20)
    response.raise_for_status()
    payload = response.json()['data']
    assert len(payload['items']) <= 1
    assert response.headers['Cache-Control'] == 'private, no-store'
    assert not any(secret in response.text for secret in ('passwordHash', 'securityStamp', 'imageBlobName', 'refreshToken'))
    assert session.get(base + '/account/export/' + section, timeout=10).status_code == 401
assert session.get(base + '/account/export/credentials', headers=headers, timeout=10).status_code == 400
print('PASS: authenticated, paginated no-cache exports exclude credentials/internal paths')
response = session.post(base + '/account/sessions/revoke-all', headers=headers, timeout=20)
response.raise_for_status()
assert session.get(base + '/auth/profile', headers=headers, timeout=10).status_code == 401
assert session.post(base + '/auth/refresh', json={'refreshToken': owner['refreshToken']}, timeout=10).status_code == 401
assert session.get(base + '/auth/profile', headers={'Authorization': 'Bearer ' + other['accessToken']}, timeout=10).status_code == 200
assert login('patient@mediscan.ai', 'Patient@1234')['user']['id'] == owner['user']['id']
print('PASS: old access and refresh tokens rejected; other account and fresh login still work')
