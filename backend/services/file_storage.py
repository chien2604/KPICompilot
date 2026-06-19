from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.config import get_settings


class FileStorage:
    def __init__(self) -> None:
        self.upload_dir = get_settings().upload_dir

    def save_upload(self, file: UploadFile) -> tuple[str, str]:
        safe_name = Path(file.filename or "evidence.bin").name
        stored_name = f"{uuid4().hex}_{safe_name}"
        target = self.upload_dir / stored_name
        with target.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                output.write(chunk)
        return safe_name, str(target)
