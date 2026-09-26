"""
scratch/test_media_service.py — Test MediaService with real images from assets folder
"""
import os
import sys
import base64
from pathlib import Path

# Setup Django environment
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from common.services.media_service import MediaService
from PIL import Image
from io import BytesIO

import glob

ASSETS_DIR = BACKEND_DIR.parent / "tossatale-canvas-main" / "src" / "assets"

print("=== STARTING MEDIA SERVICE ASSET TESTS ===")
print(f"Cloudinary configured: {MediaService.is_cloudinary_configured()}")

all_files = sorted(glob.glob(str(ASSETS_DIR / "*.*")))
image_files = [f for f in all_files if not f.endswith(".asset.json")]

print(f"Total image files found in assets: {len(image_files)}")

passed_count = 0
for filepath_str in image_files:
    filepath = Path(filepath_str)
    filename = filepath.name
    file_size_kb = filepath.stat().st_size / 1024
    print(f"\n--- Testing file: {filename} ({file_size_kb:.1f} KB) ---")

    # 1. Check original image
    try:
        orig_img = Image.open(filepath)
        orig_w, orig_h = orig_img.size
        print(f"Original: {orig_w}x{orig_h}, mode={orig_img.mode}, format={orig_img.format}")
    except Exception as e:
        print(f"[SKIP] Non-image file: {filename} ({e})")
        continue

    # 2. Test upload
    with open(filepath, "rb") as f:
        res = MediaService.upload_image(f, folder="blogs", max_dim=1400)

    storage_type = res.get("storage_type")
    url = res.get("url", "")
    is_cdn = res.get("is_cdn", False)
    print(f"Result storage_type: {storage_type}, is_cdn: {is_cdn}")

    if is_cdn and url.startswith("http"):
        public_id = res.get("public_id", "N/A")
        fmt = res.get("format", "N/A")
        w = res.get("width", "N/A")
        h = res.get("height", "N/A")
        print(f"✨ Cloudinary CDN URL: {url}")
        print(f"   Public ID: {public_id}, Format: {fmt}, Dimensions: {w}x{h}")
        passed_count += 1
        print(f"[PASS] {filename} successfully uploaded to Cloudinary!")
    elif url.startswith("data:image"):
        data_len_kb = len(url) / 1024
        header, encoded = url.split(",", 1)
        decoded_bytes = base64.b64decode(encoded)
        dec_img = Image.open(BytesIO(decoded_bytes))
        dec_w, dec_h = dec_img.size
        print(f"⚠️ Base64 Fallback: {dec_w}x{dec_h}, format={dec_img.format}, payload={data_len_kb:.1f} KB")

        assert dec_w <= 1400 and dec_h <= 1400, f"Image exceeds max dimension 1400: {dec_w}x{dec_h}"
        assert dec_img.mode == "RGB", f"Decoded mode must be RGB, got {dec_img.mode}"
        passed_count += 1
        print(f"[PASS] {filename} successfully stored via Base64 fallback.")
    else:
        raise AssertionError(f"Unexpected URL output: {url[:100]}")

print(f"\n========================================================")
print(f"=== COMPLETED: {passed_count}/{len(image_files)} ASSETS PROCESSED SUCCESSFULLY! ===")
print(f"========================================================")
