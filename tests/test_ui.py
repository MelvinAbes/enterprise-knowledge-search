from fastapi.testclient import TestClient


def test_interface_and_local_assets_are_served_with_security_headers(
    client: TestClient,
) -> None:
    page = client.get("/")
    stylesheet = client.get("/static/styles.css")
    script = client.get("/static/app.js")

    assert page.status_code == 200
    assert "<title>Enterprise Knowledge Search</title>" in page.text
    assert 'data-api-prefix="/api/v1"' in page.text
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["x-frame-options"] == "DENY"
    assert stylesheet.status_code == 200
    assert "text/css" in stylesheet.headers["content-type"]
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
