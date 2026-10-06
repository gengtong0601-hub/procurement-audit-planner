import io
import zipfile

from fastapi.testclient import TestClient

from procurement_audit.web import create_app


def test_browser_api_workflow_and_download(tmp_path):
    client = TestClient(create_app(tmp_path))
    assert client.get("/").status_code == 200
    assert "Plan with evidence" in client.get("/").text
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/api/cases/demo")
    assert response.status_code == 201
    case = response.json()
    base = "/api/cases/" + case["case_id"]
    assert case["stage"] == "risk_review"
    assert client.post(base + "/plan").status_code == 409
    decisions = {
        "reviewer": "Synthetic API test auditor",
        "decisions": [
            {"risk_id": r["risk_id"], "decision": "approve", "comment": "Automated test only."}
            for r in case["register"]["risks"]
        ],
    }
    assert client.post(base + "/decisions", json=decisions).status_code == 200
    response = client.post(base + "/plan")
    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "signoff"
    assert len(response.json()["checks"]) == 4
    review = {
        "reviewer": "Synthetic API test auditor",
        "decision": "return_for_revision",
        "comment": "Test-only request for more evidence.",
    }
    response = client.post(base + "/sign-off", json=review)
    assert response.status_code == 200
    assert response.json()["stage"] == "revision_requested"
    archive = zipfile.ZipFile(io.BytesIO(client.get(base + "/download").content))
    assert "outputs/audit-program.md" in archive.namelist()
    assert "outputs/review.md" in archive.namelist()
    assert "inputs/" not in " ".join(archive.namelist())
    assert client.get(base + "/files/audit-program.md").status_code == 200


def test_cross_origin_writes_are_blocked(tmp_path):
    client = TestClient(create_app(tmp_path))
    response = client.post("/api/cases/demo", headers={"Origin": "https://unrelated.example"})
    assert response.status_code == 403
    assert list(tmp_path.iterdir()) == []


def test_untrusted_host_and_unknown_case_are_blocked(tmp_path):
    client = TestClient(create_app(tmp_path))
    assert client.get("/", headers={"Host": "unrelated.example"}).status_code == 400
    assert client.get("/api/cases/unknown").status_code == 409
