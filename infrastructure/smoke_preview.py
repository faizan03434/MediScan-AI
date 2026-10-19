"""Run against local preview only; creates synthetic scan records in the dev database."""
import io
import requests
from PIL import Image, PngImagePlugin

BASE = "http://127.0.0.1:5000"
requests = requests.Session()
requests.trust_env = False


def login(email, password):
    response = requests.post(BASE + "/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
    response.raise_for_status()
    return {"Authorization": "Bearer " + response.json()["data"]["accessToken"]}


patient = login("patient@mediscan.ai", "Patient@1234")
other = login("doctor@mediscan.ai", "Doctor@1234")
image = io.BytesIO()
source = Image.new("RGB", (96, 64), "#aabbcc")
exif = source.getexif()
exif[274] = 6
exif[315] = "synthetic private identity"
metadata = PngImagePlugin.PngInfo()
metadata.add_text("patient", "synthetic private identity")
source.save(image, "PNG", exif=exif, pnginfo=metadata, dpi=(300, 300))
scans = []
try:
    for module in ("Anemia", "SkinDisease", "Posture", "EyeDisease", "Wound", "TongueDiagnosis"):
        response = requests.post(BASE + "/api/v1/scan", headers=patient, data={"scanType": module},
            files={"image": ("synthetic.png", image.getvalue(), "image/png")}, timeout=30)
        response.raise_for_status()
        scan = response.json()["data"]
        scans.append(scan)
        assert scan["scanType"] == module and scan["status"] == "Completed", scan
        assert scan["detectionResult"].startswith("Inconclusive") and scan["nextScanDate"] is None
        photo = BASE + scan["imageUrl"]
        assert requests.get(photo, timeout=10).status_code == 401
        assert requests.get(photo, headers=other, timeout=10).status_code == 404
        owner = requests.get(photo, headers=patient, timeout=10)
        assert owner.status_code == 200 and owner.headers["Content-Type"].startswith("image/png")
        with Image.open(io.BytesIO(owner.content)) as stored:
            assert stored.size == (64, 96) and not stored.info and not stored.getexif()
            assert stored.getpixel((0, 0)) == (170, 187, 204)
        assert b"synthetic private identity" not in owner.content
        assert requests.get(BASE + "/uploads/" + scan["imageUrl"].split("/media/")[1], timeout=10).status_code == 404
        assert requests.get(BASE + "/api/v1/scan/" + scan["id"], headers=other, timeout=10).status_code == 404
    print("PASS: six captures, saved history, no medical inference, owner-only metadata-free oriented PNGs")
    for invalid in (b"", b"not an image"):
        assert requests.post(BASE + "/api/v1/scan", headers=patient, data={"scanType": "Anemia"},
            files={"image": ("invalid.png", invalid, "image/png")}, timeout=10).status_code == 400
    assert requests.get(BASE + "/api/v1/scan/compare", headers=patient,
        params={"scan1Id": scans[0]["id"], "scan2Id": scans[1]["id"]}, timeout=10).status_code == 400
    print("PASS: empty/corrupt capture rejection and cross-module comparison rejection")
finally:
    for record in scans:
        response = requests.delete(BASE + "/api/v1/scan/" + record["id"], headers=patient, timeout=10)
        assert response.status_code == 200
        assert requests.get(BASE + record["imageUrl"], headers=patient, timeout=10).status_code == 404
    print(f"Cleanup: {len(scans)} synthetic scan records deleted; photos inaccessible")
