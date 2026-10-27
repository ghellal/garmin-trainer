from fastapi.testclient import TestClient
from firebase_admin import auth

from app import main
from app.main import AuthenticatedUser, app, get_current_user


client = TestClient(app)


def test_health_check_is_public_and_minimal() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_me_requires_authentication() -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_verified_user_from_auth_dependency() -> None:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        uid="test-user",
        email="runner@example.com",
    )
    try:
        response = client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer test-firebase-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"uid": "test-user", "email": "runner@example.com"}


def test_me_accepts_only_the_configured_verified_email(monkeypatch) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("ALLOWED_USER_EMAIL", "runner@example.com")
    monkeypatch.setattr(main, "_firebase_app", lambda: object())
    monkeypatch.setattr(
        auth,
        "verify_id_token",
        lambda token, app: {
            "uid": "test-user",
            "email": "Runner@example.com",
            "email_verified": True,
        },
    )

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer simulated-token"},
    )

    assert response.status_code == 200
    assert response.json()["uid"] == "test-user"


def test_me_rejects_unverified_email(monkeypatch) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("ALLOWED_USER_EMAIL", "runner@example.com")
    monkeypatch.setattr(main, "_firebase_app", lambda: object())
    monkeypatch.setattr(
        auth,
        "verify_id_token",
        lambda token, app: {
            "uid": "test-user",
            "email": "runner@example.com",
            "email_verified": False,
        },
    )

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer simulated-token"},
    )

    assert response.status_code == 403


def test_me_rejects_a_different_verified_email(monkeypatch) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("ALLOWED_USER_EMAIL", "runner@example.com")
    monkeypatch.setattr(main, "_firebase_app", lambda: object())
    monkeypatch.setattr(
        auth,
        "verify_id_token",
        lambda token, app: {
            "uid": "other-user",
            "email": "other@example.com",
            "email_verified": True,
        },
    )

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer simulated-token"},
    )

    assert response.status_code == 403


def test_me_rejects_an_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("ALLOWED_USER_EMAIL", "runner@example.com")
    monkeypatch.setattr(main, "_firebase_app", lambda: object())

    def reject_token(token, app):
        raise ValueError("invalid token")

    monkeypatch.setattr(auth, "verify_id_token", reject_token)

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer simulated-token"},
    )

    assert response.status_code == 401
