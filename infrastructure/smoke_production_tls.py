"""Synthetic Production-mode TLS/bootstrap drill; never reads the development database."""
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import ssl
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener
import uuid


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / '.preview/production-drills' / uuid.uuid4().hex
    application = directory / 'application'
    application.mkdir(parents=True)
    api = root / 'backend/MediScan.API/bin/Release/net9.0/MediScan.API.dll'
    if not api.exists():
        raise RuntimeError('Build the backend solution in Release mode before running this Windows drill.')
    hidden = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    private_prefixes = ('connectionstrings__', 'database__', 'jwt__', 'aiserver__', 'allowedorigins__', 'kestrel__',
                        'authentication__', 'email__', 'azure__', 'google__', 'mediscan_bootstrap_')
    environment = {k: v for k, v in os.environ.items() if not k.lower().startswith(private_prefixes)}
    certificate_password = secrets.token_urlsafe(32)
    environment['MEDISCAN_DRILL_CERT_PASSWORD'] = certificate_password
    powershell = 'pwsh' if os.name == 'nt' else 'pwsh'
    certificate = subprocess.run([powershell, '-NoProfile', '-File', str(root / 'infrastructure/create_drill_certificate.ps1'),
                                  '-Directory', str(directory)], env=environment, capture_output=True, text=True, timeout=30, **hidden)
    if certificate.returncode:
        (directory / 'certificate.log').write_text(certificate.stdout + certificate.stderr)
        raise RuntimeError('Certificate fixture failed; inspect private drill logs.')
    (application / 'appsettings.json').write_text(json.dumps({
        'Database': {'Provider': 'sqlite'}, 'ConnectionStrings': {'DefaultConnection': 'Data Source=main.db'},
        'Jwt': {'Issuer': 'ProductionDrill', 'Audience': 'ProductionDrillUsers', 'ExpiryMinutes': 15},
        'AllowedOrigins': ['https://localhost'], 'AllowedHosts': 'localhost;127.0.0.1',
        'AiServer': {'Url': 'http://127.0.0.1:9'}}))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    base = f'https://127.0.0.1:{port}'
    environment.update(ASPNETCORE_ENVIRONMENT='Production', ASPNETCORE_URLS=base,
                       Jwt__Secret=secrets.token_urlsafe(64), AiServer__ApiKey=secrets.token_urlsafe(32),
                       Kestrel__Endpoints__Https__Url=base,
                       Kestrel__Certificates__Default__Path=str(directory / 'server.pfx'),
                       Kestrel__Certificates__Default__Password=certificate_password,
                       Authentication__DataProtection__CertificatePath=str(directory / 'server.pfx'),
                       Authentication__DataProtection__CertificatePassword=certificate_password,
                       Email__Smtp__Username='', Email__Smtp__Password='', Azure__StorageConnectionString='')

    def command(name, arguments, success=True):
        result = subprocess.run(['dotnet', str(api), '--contentRoot', str(application), *arguments], cwd=application,
                                env=environment, capture_output=True, text=True, timeout=60, **hidden)
        (directory / (name + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        if (result.returncode == 0) != success:
            raise RuntimeError(f'{name} produced an unexpected outcome; inspect private drill logs.')

    command('initialize', ['--initialize-database'])
    with sqlite3.connect(application / 'main.db') as database:
        assert database.execute('SELECT COUNT(*) FROM AspNetUsers').fetchone()[0] == 0
        assert database.execute('SELECT COUNT(*) FROM AspNetRoles').fetchone()[0] == 3
    password = 'Aa1!' + secrets.token_urlsafe(32)
    environment.update(MEDISCAN_BOOTSTRAP_ADMIN_EMAIL='operator@fixture.invalid', MEDISCAN_BOOTSTRAP_ADMIN_PASSWORD=password,
                       MEDISCAN_BOOTSTRAP_EMAIL_VERIFIED='false')
    command('unverified-bootstrap', ['--provision-admin'], success=False)
    environment['MEDISCAN_BOOTSTRAP_EMAIL_VERIFIED'] = 'true'
    command('provision', ['--provision-admin'])
    command('repeat-bootstrap', ['--provision-admin'], success=False)
    for key in ('MEDISCAN_BOOTSTRAP_ADMIN_EMAIL', 'MEDISCAN_BOOTSTRAP_ADMIN_PASSWORD', 'MEDISCAN_BOOTSTRAP_EMAIL_VERIFIED', 'MEDISCAN_DRILL_CERT_PASSWORD'):
        environment.pop(key, None)
    context = ssl.create_default_context(cafile=str(directory / 'public.pem'))
    client = build_opener(ProxyHandler({}), HTTPSHandler(context=context))

    def request(path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(base + '/api/v1' + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with client.open(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            payload = error.read()
            return error.code, json.loads(payload) if payload else None

    with (directory / 'server.log').open('wb') as logs:
        process = subprocess.Popen(['dotnet', str(api), '--contentRoot', str(application)], cwd=application,
                                   env=environment, stdout=logs, stderr=logs, **hidden)
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError('Production fixture exited; inspect private server log.')
                try:
                    if request('/health')[0] == 200:
                        break
                except URLError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError('Production fixture never became live.')
            assert request('/admin/stats')[0] == 401
            status, auth = request('/auth/login', {'email': 'operator@fixture.invalid', 'password': password})
            assert status == 200 and auth['data']['user']['role'] == 'Admin'
            status, stats = request('/admin/stats', token=auth['data']['accessToken'])
            assert status == 200 and stats['data']['totalUsers'] == 1
            status, readiness = request('/health/ready')
            assert status == 503 and readiness['database'] is True and readiness['imageService'] is False
            assert readiness['clinicalInferenceEnabled'] is False
            result = {'synthetic_only': True, 'production_environment': True, 'bootstrap_demo_users': 0,
                      'initial_roles': 3, 'unverified_bootstrap_rejected': True, 'repeat_bootstrap_rejected': True,
                      'https_certificate_verified_with_fixture_ca': True, 'system_trust_unchanged': True,
                      'unauthorized_admin_rejected': True, 'admin_login_and_endpoint_verified': True,
                      'missing_image_dependency_returns_503': True, 'clinical_inference_enabled': False,
                      'public_cloud_deployment_tested': False}
            (directory / 'result.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result), flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
