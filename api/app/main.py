"""Small authenticated API foundation for the Garmin Trainer PWA."""

from __future__ import annotations

import os
from typing import Annotated, Any

import firebase_admin
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class AuthenticatedUser(BaseModel):
    uid: str
    email: str


class HealthResponse(BaseModel):
    status: str


def _cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


app = FastAPI(
    title="Garmin Trainer API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def _firebase_app() -> firebase_admin.App:
    project_id = (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GCP_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )

    try:
        return firebase_admin.get_app()
    except ValueError:
        # On Cloud Run, the Admin SDK uses Application Default Credentials from
        # the dedicated runtime service account. No service-account key is used.
        return firebase_admin.initialize_app(options={"projectId": project_id})


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Firebase ID token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    allowed_email = os.getenv("ALLOWED_USER_EMAIL", "").strip().casefold()
    if not allowed_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )

    try:
        claims: dict[str, Any] = auth.verify_id_token(
            credentials.credentials,
            app=_firebase_app(),
        )
    except (ValueError, firebase_admin.exceptions.FirebaseError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Firebase ID token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    email = claims.get("email")
    if not isinstance(email, str) or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified account is required.",
        )

    if email.strip().casefold() != allowed_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not authorized to use Garmin Trainer.",
        )

    uid = claims.get("uid") or claims.get("sub")
    if not isinstance(uid, str) or not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Firebase ID token has no user identity.",
        )

    return AuthenticatedUser(uid=uid, email=email)


@app.get("/healthz", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Unauthenticated liveness probe; returns no user or infrastructure data."""
    return HealthResponse(status="ok")


@app.get("/api/v1/me", response_model=AuthenticatedUser)
def who_am_i(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Return the identity verified from the Firebase ID token."""
    return current_user
