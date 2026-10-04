import os
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
import requests
from src.config import BUCKET_DIR, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ASSETS_BUCKET

logger = logging.getLogger("ApplyEase.StorageBucket")

class StorageBucketService:
    """Hybrid Local and Supabase Cloud Object Storage Bucket service for candidate assets."""

    def __init__(self, bucket_dir: Path = BUCKET_DIR):
        self.bucket_dir = Path(bucket_dir)
        self.bucket_dir.mkdir(parents=True, exist_ok=True)
        self.sb_url = SUPABASE_URL
        self.sb_key = SUPABASE_SERVICE_ROLE_KEY
        self.sb_bucket = SUPABASE_ASSETS_BUCKET

    def upload_asset(self, candidate_id: str, file_path: Path, asset_type: str, custom_filename: str = None) -> Dict[str, Any]:
        """Store asset file in local bucket and sync to Supabase Cloud Storage bucket."""
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
            "checksum_md5": md5_checksum,
            "supabase_cdn_url": None
        }

        # Sync to Supabase Object Storage if configured
        if self.sb_url and self.sb_key:
            try:
                storage_object_path = f"{candidate_id}/{filename}"
                upload_url = f"{self.sb_url}/storage/v1/object/{self.sb_bucket}/{storage_object_path}"
                
                content_type = "image/jpeg"
                if filename.lower().endswith(".png"):
                    content_type = "image/png"
                elif filename.lower().endswith(".pdf"):
                    content_type = "application/pdf"

                resp = requests.post(
                    upload_url,
                    headers={
                        "apikey": self.sb_key,
                        "Authorization": f"Bearer {self.sb_key}",
                        "Content-Type": content_type,
                        "x-upsert": "true"
                    },
                    data=file_bytes,
                    timeout=20
                )
                if resp.status_code in [200, 201]:
                    cdn_url = f"{self.sb_url}/storage/v1/object/public/{self.sb_bucket}/{storage_object_path}"
                    metadata["supabase_cdn_url"] = cdn_url
                    logger.info("Synced asset to Supabase Storage: %s", cdn_url)
                else:
                    logger.warning("Supabase Storage upload returned status %s: %s", resp.status_code, resp.text)
            except Exception as e:
                logger.warning("Failed to sync asset to Supabase Storage: %s", str(e))

        logger.info("Uploaded asset [%s] for candidate %s to %s (%s KB)", 
                    asset_type, candidate_id, dest_path, file_size_kb)
        return metadata

    def get_asset_path(self, candidate_id: str, filename: str) -> Path:
        """Get path to candidate stored asset."""
        return self.bucket_dir / candidate_id / filename
