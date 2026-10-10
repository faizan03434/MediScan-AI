"""Run against local preview only; creates synthetic scan records in the dev database."""
import io
import requests
from PIL import Image

BASE = "http://127.0.0.1:5000"


def login(email, password):
    response = requests.post(BASE + "/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
    response.raise_for_status()
    return {"Authorization": "Bearer " + response.json()["data"]["accessToken"]}


patient = login("patient@mediscan.ai", "Patient@1234")
other = login("doctor@mediscan.ai", "Doctor@1234")
image = io.BytesIO()
Image.new("RGB", (96, 96), "#aabbcc").save(image, "PNG")
scans = []
for module in ("Anemia", "SkinDisease", "Posture", "EyeDisease", "Wound", "TongueDiagnosis"):
    response = requests.post(BASE + "/api/v1/scan", headers=patient, data={"scanType": module},
        files={"image": ("synthetic.png", image.getvalue(), "image/png")}, timeout=30)
    response.raise_for_status()
    scan = response.json()["data"]
    assert scan["scanType"] == module and scan["status"] == "Completed", scan
    assert scan["detectionResult"].startswith("Inconclusive") and scan["nextScanDate"] is None
    photo = BASE + scan["imageUrl"]
    assert requests.get(photo, timeout=10).status_code == 401
    assert requests.get(photo, headers=other, timeout=10).status_code == 404
    owner = requests.get(photo, headers=patient, timeout=10)
    assert owner.status_code == 200 and owner.headers["Content-Type"].startswith("image/png")
    assert requests.get(BASE + "/uploads/" + scan["imageUrl"].split("/media/")[1], timeout=10).status_code == 404
    assert requests.get(BASE + "/api/v1/scan/" + scan["id"], headers=other, timeout=10).status_code == 404
    scans.append(scan)
print("PASS: six captures, saved history, enum contract, no medical inference, owner-only images")
assert requests.post(BASE + "/api/v1/scan", headers=patient, data={"scanType": "Anemia"},
    files={"image": ("empty.png", b"", "image/png")}, timeout=10).status_code == 400
assert requests.get(BASE + "/api/v1/scan/compare", headers=patient,
    params={"scan1Id": scans[0]["id"], "scan2Id": scans[1]["id"]}, timeout=10).status_code == 400
record = scans[-1]
assert requests.delete(BASE + "/api/v1/scan/" + record["id"], headers=patient, timeout=10).status_code == 200
assert requests.get(BASE + record["imageUrl"], headers=patient, timeout=10).status_code == 404
print("PASS: empty capture rejection, cross-module comparison rejection, removed record image inaccessible")
