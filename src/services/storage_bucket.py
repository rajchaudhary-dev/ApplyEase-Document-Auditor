import os
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
from src.config import BUCKET_DIR

logger = logging.getLogger("ApplyEase.StorageBucket")

class StorageBucketService:
    """Mock/Local S3-compatible Object Storage Bucket service for candidate assets."""

    def __init__(self, bucket_dir: Path = BUCKET_DIR):
        self.bucket_dir = Path(bucket_dir)
        self.bucket_dir.mkdir(parents=True, exist_ok=True)

    def upload_asset(self, candidate_id: str, file_path: Path, asset_type: str, custom_filename: str = None) -> Dict[str, Any]:
        """Store asset file in the candidate's bucket folder and generate storage metadata."""
        candidate_folder = self.bucket_dir / candidate_id
        candidate_folder.mkdir(parents=True, exist_ok=True)

        filename = custom_filename or file_path.name
        dest_path = candidate_folder / filename

        shutil.copy2(file_path, dest_path)

        file_bytes = dest_path.read_bytes()
        md5_checksum = hashlib.md5(file_bytes).hexdigest()
        file_size_kb = round(len(file_bytes) / 1024.0, 2)

        metadata = {
            "candidate_id": candidate_id,
            "asset_type": asset_type,
            "original_filename": file_path.name,
            "stored_filename": filename,
            "stored_bucket_path": str(dest_path.resolve()),
            "relative_bucket_path": f"{candidate_id}/{filename}",
            "file_size_kb": file_size_kb,
            "checksum_md5": md5_checksum
        }

        logger.info("Uploaded asset [%s] for candidate %s to %s (%s KB)", 
                    asset_type, candidate_id, dest_path, file_size_kb)
        return metadata

    def get_asset_path(self, candidate_id: str, filename: str) -> Path:
        """Get path to candidate stored asset."""
        return self.bucket_dir / candidate_id / filename
