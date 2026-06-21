"""
services/pdf_client.py – Client gọi sang PDF render microservice (Node.js + Puppeteer).

Backend Python không tự render PDF; nó gửi HTML đã render sẵn sang service Node.js
qua HTTP POST /render và nhận lại bytes PDF.
"""
import requests

from core.config import get_settings


class PDFRenderError(Exception):
    pass


class PDFServiceClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.pdf_service_url.rstrip("/")
        self.api_key = settings.pdf_service_api_key
        self.timeout = 30

    def render_pdf(self, html: str) -> bytes:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        try:
            response = requests.post(
                f"{self.base_url}/render",
                json={"html": html},
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise PDFRenderError(f"Không gọi được PDF service: {exc}") from exc
