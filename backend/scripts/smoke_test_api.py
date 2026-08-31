"""Run lightweight HTTP checks against a running backend."""

import sys
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.config import get_settings  # noqa: E402


def request_access_token(base_url: str, email: str, password: str) -> str:
    """Authenticate the configured smoke-test account and return its token."""

    response = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    """Check health and selected authenticated read-only API endpoints."""

    settings = get_settings()
    health_response = requests.get(f"{settings.smoke_test_base_url}/health", timeout=10)
    health_response.raise_for_status()
    print(f"{health_response.status_code} /health")

    if not settings.smoke_test_email or not settings.smoke_test_password:
        print(
            "Bỏ qua API có xác thực vì chưa cấu hình SMOKE_TEST_EMAIL/SMOKE_TEST_PASSWORD."
        )
        return

    access_token = request_access_token(
        settings.smoke_test_base_url,
        settings.smoke_test_email,
        settings.smoke_test_password,
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    for api_path in ("/api/users", "/api/kpi/dashboard", "/api/tasks/stats"):
        response = requests.get(
            f"{settings.smoke_test_base_url}{api_path}",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        print(f"{response.status_code} {api_path}")


if __name__ == "__main__":
    main()
