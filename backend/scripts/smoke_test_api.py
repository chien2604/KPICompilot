import requests


BASE_URL = "http://localhost:8001"


def main() -> None:
    for path in ["/health", "/api/users", "/api/kpi/dashboard?month=2026-06", "/api/tasks/stats"]:
        response = requests.get(f"{BASE_URL}{path}", timeout=10)
        response.raise_for_status()
        print(path, response.status_code)


if __name__ == "__main__":
    main()
