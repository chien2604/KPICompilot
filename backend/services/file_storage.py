from pathlib import Path
from uuid import uuid4

from core.config import get_settings
from fastapi import UploadFile


class FileStorage:
    """Represent file storage data and behavior."""

    def __init__(self) -> None:
        """Initialize the file storage."""

        self.upload_dir = get_settings().upload_dir

    def save_upload(self, file: UploadFile) -> tuple[str, str]:
        """Save the upload."""

        safe_name = Path(file.filename or "evidence.bin").name
        stored_name = f"{uuid4().hex}_{safe_name}"
        target = self.upload_dir / stored_name
        with target.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                output.write(chunk)
        return safe_name, str(target)
