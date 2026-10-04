import cv2
import numpy as np
import logging
import io
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image

from src.config import PHOTO_CONSTRAINTS, SIGNATURE_CONSTRAINTS, DOCUMENT_CONSTRAINTS
from src.services.storage_bucket import StorageBucketService

logger = logging.getLogger("ApplyEase.AssetTransformer")

class AssetTransformerEngine:
    """OpenCV and Pillow image transformation & compression pipeline for candidate photos, signatures, and document scans."""

    def __init__(self, bucket_service: Optional[StorageBucketService] = None):
        self.bucket_service = bucket_service or StorageBucketService()

    def process_and_bucket_photo(self, candidate_id: str, input_path: Path) -> Dict[str, Any]:
        """Auto-crop, resize (200x230), pad, and compress Passport Photo to 20KB-50KB limit using OpenCV & Pillow."""
        input_path = Path(input_path)
        img_cv = cv2.imread(str(input_path))

        if img_cv is None:
            # Fallback to Pillow if OpenCV fails to read directly
            pil_img = Image.open(input_path).convert("RGB")
            img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # 1. Face/Subject Crop attempt using OpenCV Haar Cascade or Center Bounding Crop
        cropped_cv = self._crop_photo_subject(img_cv)

        # Convert to Pillow for fine color and JPEG compression control
        cropped_rgb = cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cropped_rgb)

        target_w = PHOTO_CONSTRAINTS["width"]
        target_h = PHOTO_CONSTRAINTS["height"]
        min_kb = PHOTO_CONSTRAINTS["min_kb"]
        max_kb = PHOTO_CONSTRAINTS["max_kb"]

        # 2. Resize & Aspect Ratio Pad to exact portal specs (200x230)
        resized_pil = self._resize_and_pad(pil_img, target_w, target_h)

        # 3. Dynamic Iterative JPEG Compression within [min_kb, max_kb]
        compressed_bytes, final_quality, size_kb = self._compress_to_kb_target(resized_pil, min_kb, max_kb)

        # Save to temp file and upload to Bucket
        temp_out = input_path.parent / f"{candidate_id}_photo_compressed.jpg"
        temp_out.write_bytes(compressed_bytes)

        metadata = self.bucket_service.upload_asset(
            candidate_id=candidate_id,
            file_path=temp_out,
            asset_type="passport_photo",
            custom_filename="passport_photo.jpg"
        )
        metadata["width"] = target_w
        metadata["height"] = target_h

        if temp_out.exists():
            temp_out.unlink()

        return metadata

    def process_and_bucket_signature(self, candidate_id: str, input_path: Path) -> Dict[str, Any]:
        """Auto-crop signature bounds using OpenCV contours, resize to 140x60, and compress to 10KB-20KB limit."""
        input_path = Path(input_path)
        img_cv = cv2.imread(str(input_path))

        if img_cv is None:
            pil_img = Image.open(input_path).convert("RGB")
            img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # 1. Signature Bounding Contour Detection via OpenCV
        cropped_cv = self._crop_signature_contours(img_cv)

        cropped_rgb = cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cropped_rgb)

        target_w = SIGNATURE_CONSTRAINTS["width"]
        target_h = SIGNATURE_CONSTRAINTS["height"]
        min_kb = SIGNATURE_CONSTRAINTS["min_kb"]
        max_kb = SIGNATURE_CONSTRAINTS["max_kb"]

        # 2. Resize & Pad
        resized_pil = self._resize_and_pad(pil_img, target_w, target_h, pad_color=(255, 255, 255))

        # 3. Dynamic Compression
        compressed_bytes, final_quality, size_kb = self._compress_to_kb_target(resized_pil, min_kb, max_kb)

        temp_out = input_path.parent / f"{candidate_id}_sig_compressed.jpg"
        temp_out.write_bytes(compressed_bytes)

        metadata = self.bucket_service.upload_asset(
            candidate_id=candidate_id,
            file_path=temp_out,
            asset_type="signature",
            custom_filename="signature.jpg"
        )
        metadata["width"] = target_w
        metadata["height"] = target_h

        if temp_out.exists():
            temp_out.unlink()

        return metadata

    def process_and_bucket_document(self, candidate_id: str, input_path: Path, doc_type_name: str) -> Dict[str, Any]:
        """Compress document scans (PDF/Image) under portal threshold (300KB) and dump to bucket."""
        input_path = Path(input_path)
        
        # If already image or PDF, normalize image compression
        if input_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
            pil_img = Image.open(input_path).convert("RGB")
            compressed_bytes, _, size_kb = self._compress_to_kb_target(pil_img, min_kb=20, max_kb=DOCUMENT_CONSTRAINTS["max_kb"])
            temp_out = input_path.parent / f"{candidate_id}_{doc_type_name}.jpg"
            temp_out.write_bytes(compressed_bytes)
            
            metadata = self.bucket_service.upload_asset(
                candidate_id=candidate_id,
                file_path=temp_out,
                asset_type=f"doc_{doc_type_name}",
                custom_filename=f"{doc_type_name}.jpg"
            )
            metadata["width"] = pil_img.width
            metadata["height"] = pil_img.height
            if temp_out.exists():
                temp_out.unlink()
            return metadata
        else:
            # Upload directly if PDF or raw file
            return self.bucket_service.upload_asset(
                candidate_id=candidate_id,
                file_path=input_path,
                asset_type=f"doc_{doc_type_name}",
                custom_filename=input_path.name
            )

    def _crop_photo_subject(self, img: np.ndarray) -> np.ndarray:
        """Crop central area of passport photo assuming face centered."""
        h, w, _ = img.shape
        # Try OpenCV Haar Cascade face detection if available
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.2, 5)

            if len(faces) > 0:
                # Take largest face and pad around shoulders/head
                (x, y, fw, fh) = max(faces, key=lambda b: b[2] * b[3])
                pad_top = int(fh * 0.6)
                pad_bot = int(fh * 1.2)
                pad_side = int(fw * 0.7)

                y1 = max(0, y - pad_top)
                y2 = min(h, y + fh + pad_bot)
                x1 = max(0, x - pad_side)
                x2 = min(w, x + fw + pad_side)
                return img[y1:y2, x1:x2]
        except Exception as e:
            logger.debug("Haar cascade face detection skipped: %s", str(e))

        # Fallback: Central 85% crop
        cy1, cy2 = int(h * 0.05), int(h * 0.95)
        cx1, cx2 = int(w * 0.05), int(w * 0.95)
        return img[cy1:cy2, cx1:cx2]

    def _crop_signature_contours(self, img: np.ndarray) -> np.ndarray:
        """Use OpenCV contours to crop tight bounding box around signature strokes."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Threshold: assume signature strokes are darker than background
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Get bounding box around all dark stroke contours
            x_min, y_min = img.shape[1], img.shape[0]
            x_max, y_max = 0, 0
            found = False

            for c in contours:
                if cv2.contourArea(c) > 25: # filter noise
                    x, y, w, h = cv2.boundingRect(c)
                    x_min = min(x_min, x)
                    y_min = min(y_min, y)
                    x_max = max(x_max, x + w)
                    y_max = max(y_max, y + h)
                    found = True

            if found:
                # Add slight padding
                pad = 10
                y1 = max(0, y_min - pad)
                y2 = min(img.shape[0], y_max + pad)
                x1 = max(0, x_min - pad)
                x2 = min(img.shape[1], x_max + pad)
                return img[y1:y2, x1:x2]

        return img

    def _resize_and_pad(self, pil_img: Image.Image, target_w: int, target_h: int, pad_color=(255, 255, 255)) -> Image.Image:
        """Resize image keeping aspect ratio and pad centered to target dimensions."""
        pil_img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        new_img = Image.new("RGB", (target_w, target_h), pad_color)
        upper_left = ((target_w - pil_img.width) // 2, (target_h - pil_img.height) // 2)
        new_img.paste(pil_img, upper_left)
        return new_img

    def _compress_to_kb_target(self, pil_img: Image.Image, min_kb: float, max_kb: float) -> Tuple[bytes, int, float]:
        """Binary search for JPEG quality setting to hit target KB bounds."""
        low_q, high_q = 20, 95
        best_bytes = None
        best_q = 85
        best_size = 0.0

        for _ in range(7):
            mid_q = (low_q + high_q) // 2
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=mid_q, optimize=True)
            data = buf.getvalue()
            kb = len(data) / 1024.0

            best_bytes = data
            best_q = mid_q
            best_size = kb

            if kb > max_kb:
                high_q = mid_q - 1
            elif kb < min_kb and mid_q < 95:
                low_q = mid_q + 1
            else:
                break

        return best_bytes, best_q, round(best_size, 2)
