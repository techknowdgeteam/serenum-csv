from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import logging
import random
from PIL import Image
import calendar
import json
import os
import time
from datetime import datetime, timedelta
import shutil
import pytz
import csv
import re
import requests 
from typing import Tuple, List
import os
import json
import numpy as np
from PIL import Image
from pathlib import Path
from PIL import ImageFilter
import imghdr
import traceback



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_urls() -> list[str]:
    """
    Launch headless Chrome, fetch JPG URLs, save to JSON,
    and PRINT status messages (hardcoded inside).
    """
    # ----- ALL HARDCODED PATHS & URL -----
    TARGET_URL = "https://jpgsvault.rf.gd/loadimagesurl.php?i=1"
    CHROME_BINARY = r"C:\xampp\htdocs\CIPHER\googlechrome\Google\Chrome\Application\chrome.exe"
    OUTPUT_FILE = r"C:\xampp\htdocs\serenum-csv\files\fetchedjpgsurl.json"
    # -------------------------------------

    print("Starting headless Chrome...")
    print(f"Target URL: {TARGET_URL}")
    print(f"Output file: {OUTPUT_FILE}")

    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-autofill")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    if os.path.exists(CHROME_BINARY):
        options.binary_location = CHROME_BINARY
        print("Using custom Chrome binary.")
    else:
        print("Custom Chrome binary not found. Using system default.")

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(driver_version="139.0.7258.128").install()),
            options=options
        )
        driver.set_page_load_timeout(60)
        print("Navigating to page...")
        driver.get(TARGET_URL)
        driver.implicitly_wait(5)

        print("Extracting JPG URLs from <div class=\"url\">...")
        html = driver.page_source
        matches = re.findall(r'<div class="url">([^<]+)</div>', html)

        jpg_urls = []
        for url in matches:
            url = url.strip().replace("\\", "/")
            if url.lower().endswith(('.jpg', '.jpeg')) and url not in jpg_urls:
                jpg_urls.append(url)

        total = len(jpg_urls)
        print(f"Extracted {total} unique JPG URL(s).")

        # Save JSON
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        payload = {
            "source_url": TARGET_URL,
            "fetched_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "total_jpgs": total,
            "jpg_urls": jpg_urls
        }
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


        return jpg_urls

    except Exception as e:
        print("FAILED: An error occurred.")
        print(f"Error: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")


def corruptedjpgs():
    """
    Scans ALL .jpg, .jpeg, .png, .gif files in:
      - files/jpgs/{author}/
      - files/next jpg/{author}/
      - files/uploaded jpgs/{author}/
      - files/downloaded/{author}/        ← NEW: deletes corrupted ones

    - Moves corrupted files from the first 3 → files/corruptedjpgs/{author}/
    - Deletes corrupted files from 'downloaded' folder (they're temporary)
    - Logs results in corrupted_jpgs.json
    """
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'

    # ------------------------------------------------------------------ #
    # 1. Load author from config
    # ------------------------------------------------------------------ #
    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as json_file:
            config = json.load(json_file)
        author = config.get('author', '').strip()
        if not author:
            print("Error: 'author' is missing or empty in config.")
            return
    except Exception as e:
        print(f"Failed to load or parse {JSON_CONFIG_PATH}: {e}")
        return

    # ------------------------------------------------------------------ #
    # 2. Define all directories to scan
    # ------------------------------------------------------------------ #
    base_root = r"C:\xampp\htdocs\serenum-csv\files"
    directories_to_check = [
        os.path.join(base_root, "jpgs", author),
        os.path.join(base_root, "next jpg", author),
        os.path.join(base_root, "uploaded jpgs", author),
        os.path.join(base_root, "downloaded", author)  # ← NEW
    ]
    corrupted_dir = os.path.join(base_root, "corruptedjpgs", author)

    # ------------------------------------------------------------------ #
    # 3. Validate input directories
    # ------------------------------------------------------------------ #
    valid_dirs = []
    for dir_path in directories_to_check:
        if os.path.exists(dir_path):
            valid_dirs.append(dir_path)
        else:
            print(f"Directory not found (skipping): {dir_path}")

    if not valid_dirs:
        print("No valid directories found to scan.")
        return

    # Create corrupted directory (for moved files)
    if not os.path.exists(corrupted_dir):
        try:
            os.makedirs(corrupted_dir)
            print(f"Created corrupted directory: {corrupted_dir}")
        except Exception as e:
            print(f"Failed to create corrupted directory {corrupted_dir}: {e}")
            return

    # ------------------------------------------------------------------ #
    # 4. Supported image extensions
    # ------------------------------------------------------------------ #
    IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')
    moved_files: List[Tuple[str, str, str]] = []  # (filename, source_dir, dest_path)
    deleted_files: List[Tuple[str, str]] = []     # (filename, source_dir)

    print(f"\nScanning {len(valid_dirs)} directories for corrupted images...\n")

    # ------------------------------------------------------------------ #
    # 5. Scan each directory
    # ------------------------------------------------------------------ #
    for directory in valid_dirs:
        is_downloaded_folder = directory.endswith(os.path.join("downloaded", author))
        action = "DELETE" if is_downloaded_folder else "MOVE"

        print(f"Checking ({action}): {directory}")
        try:
            files = os.listdir(directory)
        except Exception as e:
            print(f"Could not read directory {directory}: {e}")
            continue

        image_files = [
            f for f in files
            if f.lower().endswith(IMAGE_EXTENSIONS)
            and os.path.isfile(os.path.join(directory, f))
        ]

        for file in image_files:
            file_path = os.path.join(directory, file)
            is_corrupted = False
            error_msg = ""

            # ------------------- Pillow Double Check -------------------
            try:
                with Image.open(file_path) as img:
                    img.verify()          # Structure check
                with Image.open(file_path) as img:
                    img.load()            # Full decode check
            except Exception as e:
                is_corrupted = True
                error_msg = str(e)

            # ------------------- Handle Corrupted -------------------
            if is_corrupted:
                print(f"  [CORRUPTED] {file} → {error_msg}")

                if is_downloaded_folder:
                    # DELETE from downloaded folder
                    try:
                        os.remove(file_path)
                        print(f"  [DELETED] {file_path}")
                        deleted_files.append((file, directory))
                    except Exception as del_e:
                        print(f"  [FAILED TO DELETE] {file}: {del_e}")
                else:
                    # MOVE to corrupted folder
                    dest_path = os.path.join(corrupted_dir, file)
                    base, ext = os.path.splitext(file)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(corrupted_dir, f"{base}_{counter}{ext}")
                        counter += 1

                    try:
                        shutil.move(file_path, dest_path)
                        print(f"  [MOVED] → {dest_path}")
                        moved_files.append((file, directory, dest_path))
                    except Exception as move_e:
                        print(f"  [FAILED TO MOVE] {file}: {move_e}")
            else:
                print(f"  [OK] {file}")

    # ------------------------------------------------------------------ #
    # 6. Write summary JSON (NO DATETIME!)
    # ------------------------------------------------------------------ #
    json_path = os.path.join(corrupted_dir, 'corrupted_jpgs.json')
    try:
        summary = {
            "author": author,
            "scanned_directories": valid_dirs,
            "total_moved": len(moved_files),
            "total_deleted": len(deleted_files),
            "moved_files": [
                {
                    "filename": orig,
                    "from_directory": src_dir,
                    "moved_to": dest
                }
                for orig, src_dir, dest in moved_files
            ],
            "deleted_files": [
                {
                    "filename": orig,
                    "from_directory": src_dir
                }
                for orig, src_dir in deleted_files
            ],
            "note": (
                "Corrupted files in 'downloaded' folder are DELETED. "
                "Others are MOVED to corruptedjpgs folder. "
                "All .jpg/.jpeg/.png/.gif checked with Pillow verify() + load()."
            )
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

        total_corrupted = len(moved_files) + len(deleted_files)

        print("\n" + "="*80)
        print(f"SUMMARY: {total_corrupted} corrupted file(s) found and cleaned.")
        print(f"   • Moved: {len(moved_files)} → {corrupted_dir}")
        print(f"   • Deleted: {len(deleted_files)} (from downloaded folder)")
        print(f"Log saved: {json_path}")
        print("="*80)

        if moved_files:
            print("\nMoved corrupted files (first 10):")
            for orig, _, dest in moved_files[:10]:
                print(f"   {orig} → {os.path.basename(dest)}")
            if len(moved_files) > 10:
                print(f"   ... and {len(moved_files) - 10} more.")

        if deleted_files:
            print("\nDeleted corrupted files from downloaded (first 10):")
            for orig, _ in deleted_files[:10]:
                print(f"   {orig}")
            if len(deleted_files) > 10:
                print(f"   ... and {len(deleted_files) - 10} more.")

        if total_corrupted == 0:
            print("\nNo corrupted files found. All images are valid!")

    except Exception as e:
        print(f"Failed to write summary JSON: {e}")

def crop_and_moveto_jpgs():
    """
    Moves images from 'downloaded' to 'jpgfolders'.
    If borders detected → crop them + fixed 10/40px top/bottom.
    If no borders → move as-is.
    Always MOVES (not copies) to save space.
    Detailed logs.
    """
    # === CONFIGURATION ===
    json_path = r"C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json"
    base_dir = r"C:\xampp\htdocs\serenum-csv\files"
    threshold = 40
    crop_top = 10
    crop_bottom = 40
    # =====================

    import os
    import json
    import numpy as np
    from PIL import Image
    import shutil

    def process_image(src_path, dst_path, threshold):
        try:
            print(f"[OPEN] Loading: {os.path.basename(src_path)}")
            img = Image.open(src_path).convert("RGB")
            img_array = np.array(img)
            h, w = img_array.shape[:2]
            print(f"[INFO] Original size: {w}x{h}")

            gray = np.mean(img_array, axis=2)
            mask = (gray > threshold) & (gray < (255 - threshold))
            coords = np.argwhere(mask)

            # Case 1: No content at all
            if coords.size == 0:
                print(f"[CHECK] No content (all near black/white). Moving as-is.")
                shutil.move(src_path, dst_path)
                print(f"[MOVED] As-is → {os.path.basename(dst_path)}")
                return True, "no_content"

            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0)

            # Case 2: Content fills entire image → no border
            if x0 == 0 and y0 == 0 and x1 == w - 1 and y1 == h - 1:
                print(f"[CHECK] No borders detected. Moving as-is.")
                shutil.move(src_path, dst_path)
                print(f"[MOVED] As-is → {os.path.basename(dst_path)}")
                return True, "no_border"

            # === BORDERS DETECTED ===
            removed = {'L': x0, 'T': y0, 'R': w - 1 - x1, 'B': h - 1 - y1}
            content_w = x1 - x0 + 1
            content_h = y1 - y0 + 1
            print(f"[BORDER] Removed: L={removed['L']}, T={removed['T']}, R={removed['R']}, B={removed['B']}")
            print(f"[BORDER] Content: {content_w}x{content_h}")

            cropped = img.crop((x0, y0, x1 + 1, y1 + 1))

            # Apply fixed crop only if enough height
            if content_h <= crop_top + crop_bottom:
                print(f"[WARN] Too small for fixed crop. Saving border-cropped only.")
                cropped.save(dst_path, quality=95)
                os.remove(src_path)  # delete original
                print(f"[SAVED] Border-only → {os.path.basename(dst_path)}")
                return True, "border_only"

            new_top = crop_top
            new_bottom = content_h - crop_bottom
            if new_bottom <= new_top:
                print(f"[WARN] Fixed crop would remove all. Saving border-cropped only.")
                cropped.save(dst_path, quality=95)
                os.remove(src_path)
                print(f"[SAVED] Border-only → {os.path.basename(dst_path)}")
                return True, "border_only"

            final_cropped = cropped.crop((0, new_top, content_w, new_bottom))
            final_h = new_bottom - new_top
            print(f"[FIXED] Cropped: {crop_top}px top, {crop_bottom}px bottom → {final_h}px tall")
            final_cropped.save(dst_path, quality=95)
            os.remove(src_path)
            print(f"[SAVED] Fully cropped → {os.path.basename(dst_path)}")
            return True, "full_crop"

        except Exception as e:
            print(f"[ERROR] Failed: {e}")
            return False, "error"

    # === MAIN ===
    if not os.path.exists(json_path):
        print(f"JSON not found: {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON error: {e}")
        return

    author = data.get("author", "").strip()
    if not author:
        print("Missing 'author' in JSON")
        return

    source_dir = os.path.join(base_dir, "downloaded", author)
    output_dir = os.path.join(base_dir, "jpgfolders", author)

    if not os.path.exists(source_dir):
        print(f"Source dir not found: {source_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
    image_files = [f for f in os.listdir(source_dir) if f.lower().endswith(image_extensions)]
    image_files.sort()

    if not image_files:
        print(f"No images in {source_dir}")
        return

    print(f"Found {len(image_files)} image(s) in {source_dir}\n")

    stats = {k: 0 for k in ["total", "saved", "no_border", "border_only", "full_crop", "no_content", "error"]}
    stats["total"] = len(image_files)

    for img_file in image_files:
        src_path = os.path.join(source_dir, img_file)
        dst_path = os.path.join(output_dir, img_file)

        print(f"\n{'='*60}")
        print(f"PROCESSING: {img_file}")
        print(f"{'='*60}")

        success, action = process_image(src_path, dst_path, threshold)
        if success:
            stats["saved"] += 1
            stats[action] += 1
        else:
            stats["error"] += 1
            print(f"[FAILED] Keeping original due to error.")

    # === FINAL SUMMARY ===
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY - Author: {author}")
    print(f"{'='*60}")
    print(f"Total images: {stats['total']}")
    print(f"Successfully processed: {stats['saved']}")
    if stats['saved'] > 0:
        print(f"  • Moved as-is (no crop):      {stats['no_border']}")
        print(f"  • Border crop only:           {stats['border_only']}")
        print(f"  • Full crop (border + fixed): {stats['full_crop']}")
        print(f"  • No content (all border):    {stats['no_content']}")
    print(f"Errors: {stats['error']}")
    print(f"{'='*60}")

def check_single_url(
    url: str,
    timeout: int = 30,
    temp_dir: str | None = None,
    final_dir: str | None = None,
) -> Tuple[bool, str]:
    """
    Downloads and verifies image integrity using Pillow.
    Returns (is_valid: bool, debug_info: str)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Request error: {e}"

    if not temp_dir:
        return False, "temp_dir required"

    os.makedirs(temp_dir, exist_ok=True)
    base_name = os.path.basename(url.split("?")[0])
    if not base_name.lower().endswith((".jpg", ".jpeg")):
        base_name += ".jpg"

    temp_path = os.path.join(temp_dir, base_name)
    root, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(temp_path):
        temp_path = os.path.join(temp_dir, f"{root}_{counter}{ext}")
        counter += 1

    try:
        with open(temp_path, "wb") as f:
            resp.raw.decode_content = True
            shutil.copyfileobj(resp.raw, f)
    except Exception as e:
        return False, f"Save failed: {e}"

    try:
        with Image.open(temp_path) as img:
            img.verify()
        with Image.open(temp_path) as img:
            img.load()
    except Exception as e:
        try:
            os.remove(temp_path)
        except:
            pass
        return False, f"Corrupted: {e}"

    final_path = temp_path
    if final_dir and final_dir != temp_dir:
        os.makedirs(final_dir, exist_ok=True)
        dest_name = os.path.basename(temp_path)
        final_path = os.path.join(final_dir, dest_name)
        root, ext = os.path.splitext(dest_name)
        counter = 1
        while os.path.exists(final_path):
            final_path = os.path.join(final_dir, f"{root}_{counter}{ext}")
            counter += 1
        try:
            shutil.move(temp_path, final_path)
        except Exception as e:
            try:
                os.remove(temp_path)
            except:
                pass
            return False, f"Move failed: {e}"

    return True, f"OK → {os.path.getsize(final_path)} bytes"

def markjpgs():
    """
    Ensures:
      1. jpgfolders has EXACTLY cardamount JPG/PNG files
      2. next_jpgcard.json has EXACTLY cardamount valid URLs
      3. 1:1 perfect match between files and URLs
    If ANY mismatch → DELETE ALL + REDOWNLOAD ALL
    """
    # ------------------------------------------------------------------ #
    # 1. Load config
    # ------------------------------------------------------------------ #
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'
    FETCHED_JSON_PATH = r'C:\xampp\htdocs\serenum-csv\files\fetchedjpgsurl.json'

    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        author = config.get('author', '').strip()
        processjpgfrom = config.get('processjpgfrom', 'freshjpgs').strip().lower()
        if not author:
            print("Error: 'author' missing in config.")
            return

        try:
            cardamount = max(1, int(config.get('cardamount', 1)))
        except:
            print("Warning: Invalid cardamount. Using 1.")
            cardamount = 1

        if processjpgfrom not in ['freshjpgs', 'uploadedjpgs']:
            processjpgfrom = 'freshjpgs'

    except Exception as e:
        print(f"Config load failed: {e}")
        return

    # ------------------------------------------------------------------ #
    # 2. Paths
    # ------------------------------------------------------------------ #
    base_path = (
        f"https://jpgsvault.rf.gd/jpgs/{author}_uploaded/"
        if processjpgfrom == 'uploadedjpgs'
        else f"https://jpgsvault.rf.gd/jpgs/{author}/"
    )

    jpgfolders_dir = fr'C:\xampp\htdocs\serenum-csv\files\jpgfolders\{author}'
    next_json_dir = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    next_json_path = os.path.join(next_json_dir, 'next_jpgcard.json')
    download_dir = fr'C:\xampp\htdocs\serenum-csv\files\downloaded\{author}'

    os.makedirs(jpgfolders_dir, exist_ok=True)
    os.makedirs(next_json_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 3. Load fetched URLs
    # ------------------------------------------------------------------ #
    if not os.path.exists(FETCHED_JSON_PATH):
        print(f"fetchedjpgsurl.json not found: {FETCHED_JSON_PATH}")
        return

    try:
        with open(FETCHED_JSON_PATH, 'r', encoding='utf-8') as f:
            all_fetched_urls = set(json.load(f).get("jpg_urls", []))
        print(f"Loaded {len(all_fetched_urls)} URLs from fetched list")
    except Exception as e:
        print(f"Failed to read fetched list: {e}")
        return

    candidate_urls = [
        u for u in all_fetched_urls
        if u.startswith(base_path) and u.lower().endswith(('.jpg', '.jpeg'))
    ]
    print(f"Found {len(candidate_urls)} candidate JPG URLs")

    if len(candidate_urls) < cardamount:
        print(f"Only {len(candidate_urls)} URLs available, but need {cardamount}. Cannot proceed.")
        return

    # ------------------------------------------------------------------ #
    # 4. Load next_jpgcard.json
    # ------------------------------------------------------------------ #
    next_urls = []
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                next_data = json.load(f)
                next_urls = next_data.get("next_jpgcard", [])
            print(f"Loaded {len(next_urls)} URL(s) from next_jpgcard.json")
        except Exception as e:
            print(f"Corrupted next_jpgcard.json → {e}. Will rebuild.")
            next_urls = []

    # ------------------------------------------------------------------ #
    # 5. Count files in jpgfolders
    # ------------------------------------------------------------------ #
    image_exts = ('.jpg', '.jpeg', '.png')
    existing_files = [
        f for f in os.listdir(jpgfolders_dir)
        if f.lower().endswith(image_exts)
    ]
    file_count = len(existing_files)
    print(f"Found {file_count} image(s) in jpgfolders")

    # ------------------------------------------------------------------ #
    # 6. EXACT MATCH VALIDATION (Files + URLs + 1:1 Mapping)
    # ------------------------------------------------------------------ #
    def get_filename_from_url(url):
        return os.path.basename(url.split("?")[0])

    # Extract filenames from URLs
    url_filenames = {get_filename_from_url(u) for u in next_urls}
    file_names = {f for f in existing_files}

    # Check 1:1 mapping
    files_match_urls = file_names == url_filenames
    url_count_ok = len(next_urls) == cardamount
    file_count_ok = file_count == cardamount

    print(f"\nVALIDATION CHECK:")
    print(f"  • Required count       : {cardamount}")
    print(f"  • Files in folder      : {file_count}")
    print(f"  • URLs in JSON         : {len(next_urls)}")
    print(f"  • 1:1 filename match   : {'YES' if files_match_urls else 'NO'}")

    # ------------------------------------------------------------------ #
    # 7. FINAL DECISION
    # ------------------------------------------------------------------ #
    if file_count_ok and url_count_ok and files_match_urls:
        print(f"\nPERFECT MATCH: {cardamount} files + {cardamount} URLs + 1:1 mapping")
        print("SKIPPING DOWNLOAD – All data is valid and complete.")
        return
    else:
        mismatch_reasons = []
        if not file_count_ok:
            mismatch_reasons.append(f"File count ({file_count} ≠ {cardamount})")
        if not url_count_ok:
            mismatch_reasons.append(f"URL count ({len(next_urls)} ≠ {cardamount})")
        if not files_match_urls:
            mismatch_reasons.append("Filename mismatch between files and URLs")

        print(f"\nMISMATCH DETECTED:")
        for r in mismatch_reasons:
            print(f"  → {r}")

        print("DELETING ALL files, downloaded images, and JSON records...")
        
        # Delete all in jpgfolders
        for f in existing_files:
            try:
                os.remove(os.path.join(jpgfolders_dir, f))
                print(f"  [DELETED] {f}")
            except:
                pass

        # Delete all in downloaded
        for f in os.listdir(download_dir):
            try:
                path = os.path.join(download_dir, f)
                if os.path.isfile(path):
                    os.remove(path)
            except:
                pass

        # Reset next_jpgcard.json
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump({"next_jpgcard": []}, f, indent=4, ensure_ascii=False)
        print(f"  [RESET] next_jpgcard.json")

        print(f"\nREDOWNLOADING EXACTLY {cardamount} VALID IMAGES...\n")

    # ------------------------------------------------------------------ #
    # 8. Download exactly cardamount valid images
    # ------------------------------------------------------------------ #
    downloaded = 0
    valid_urls = []

    for url in candidate_urls:
        if downloaded >= cardamount:
            break

        print(f"[{downloaded + 1}/{cardamount}] Downloading: {url}")
        is_valid, debug = check_single_url(
            url,
            temp_dir=download_dir,
            final_dir=download_dir
        )

        if is_valid:
            valid_urls.append(url)
            downloaded += 1
            print(f"  [SUCCESS] {debug}")
        else:
            print(f"  [FAILED] {debug}")

    if downloaded != cardamount:
        print(f"\nFAILED: Only {downloaded}/{cardamount} images downloaded successfully.")
        return

    # ------------------------------------------------------------------ #
    # 9. Save next_jpgcard.json
    # ------------------------------------------------------------------ #
    try:
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump({"next_jpgcard": valid_urls}, f, indent=4, ensure_ascii=False)
        print(f"\nSUCCESS: Saved {len(valid_urls)} valid URLs to next_jpgcard.json")
    except Exception as e:
        print(f"Failed to save JSON: {e}")

    # ------------------------------------------------------------------ #
    # 10. Final Status
    # ------------------------------------------------------------------ #
    print("\n" + "="*80)
    print("FINAL STATUS – PERFECT SYNC ENFORCED")
    print("="*80)
    print(f"Author       : {author}")
    print(f"Required     : {cardamount}")
    print(f"Downloaded   : {downloaded}")
    print(f"jpgfolders   : {jpgfolders_dir}")
    print(f"Download Dir : {download_dir}")
    print(f"JSON Path    : {next_json_path}")
    print(f"Ready for    : crop_and_moveto_jpgs()")
    print("="*80)
    print("All files and records are in perfect 1:1 sync.")
    print("="*80)


def update_calendar():
    """Update the calendar and write to JSON, unconditionally."""

    # Get current date and time
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    current_day = now.day
    current_time_12hour = now.strftime("%I:%M %p").lower()
    current_time_24hour = now.strftime("%H:%M")
    current_date = datetime.strptime(f"{current_day:02d}/{current_month:02d}/{current_year}", "%d/%m/%Y")
    
    print(f"Current date and time: {current_date.strftime('%d/%m/%Y')} {current_time_12hour} ({current_time_24hour})")
    
    # Read pageandgroupauthors.json
    pageauthors_path = r"C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json"
    print(f"Reading pageandgroupauthors.json from {pageauthors_path}")
    try:
        with open(pageauthors_path, 'r') as f:
            pageauthors = json.load(f)
    except FileNotFoundError:
        print(f"Error: pageandgroupauthors.json not found at {pageauthors_path}")
        return
    except json.decoder.JSONDecodeError:
        print(f"Error: pageandgroupauthors.json contains invalid JSON")
        return
    
    author = pageauthors['author']
    type_value = pageauthors['type']
    group_types = pageauthors['group_types']
    print(f"Author: {author}, Type: {type_value}, Group Types: {group_types}")
    
    # Read timeorders.json
    timeorders_path = r"C:\xampp\htdocs\serenum-csv\timeorders.json"
    print(f"Reading timeorders.json from {timeorders_path}")
    try:
        with open(timeorders_path, 'r') as f:
            timeorders_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: timeorders.json not found at {timeorders_path}")
        return
    except json.decoder.JSONDecodeError:
        print(f"Error: timeorders.json contains invalid JSON")
        return
    
    # Select time slots based on type
    if type_value not in timeorders_data:
        print(f"Error: Type '{type_value}' not found in timeorders.json")
        return
    timeorders = timeorders_data[type_value]
    print(f"Time slots loaded from timeorders.json for type '{type_value}':")
    for t in timeorders:
        print(f"  - {t['12hours']} ({t['24hours']})")
    
    # Sort timeorders by 24-hour format for consistent ordering
    sorted_timeorders = sorted(timeorders, key=lambda x: x["24hours"])
    
    # Find ALL time slots after current time for TODAY
    time_ahead_today = []
    current_time = datetime.strptime(current_time_24hour, "%H:%M")
    current_datetime = datetime.combine(current_date, current_time.time())
    
    print(f"Searching for time slots after {current_time_24hour}")
    for t in sorted_timeorders:
        slot_time = datetime.strptime(t["24hours"], "%H:%M")
        delta = slot_time - current_time
        minutes_distance = int(delta.total_seconds() / 60)
        
        # TODAY: Collect all slots >= current time AND before midnight (exclude 00:00)
        if minutes_distance >= 0 and t["24hours"] != "00:00":
            slot = {
                "id": f"{current_day:02d}_{t['24hours'].replace(':', '')}",
                "12hours": t["12hours"],
                "24hours": t["24hours"],
                "minutes_distance": minutes_distance,
                "consideration": f"passed {t['12hours']}" if minutes_distance >= 50 else f"skip {t['12hours']}"
            }
            time_ahead_today.append(slot)
            print(f"Slot TODAY: {t['12hours']} ({t['24hours']}): id={slot['id']}, minutes_distance={minutes_distance}, consideration={slot['consideration']}")
    
    # Calculate next month and year
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1
    
    # Create calendar data structure
    calendar_data = {
        "calendars": [
            {
                "year": current_year,
                "month": calendar.month_name[current_month],
                "days": [
                    {
                        "week": week_idx + 1,
                        "days": [
                            {
                                "day": {
                                    "date": f"{day:02d}/{current_month:02d}/{current_year}" if day != 0 else None,
                                    "time_12hour": current_time_12hour if day == current_day else "00:00 pm" if day != 0 else None,
                                    "time_24hour": current_time_24hour if day == current_day else "00:00" if day != 0 else None,
                                    "time_ahead": (
                                        time_ahead_today if day == current_day else
                                        [
                                            {
                                                "id": f"{day:02d}_{t['24hours'].replace(':', '')}",
                                                "12hours": t["12hours"],
                                                "24hours": t["24hours"],
                                                "minutes_distance": int((
                                                    datetime.strptime(
                                                        f"{day:02d}/{current_month:02d}/{current_year} {t['24hours']}",
                                                        "%d/%m/%Y %H:%M"
                                                    ) - current_datetime
                                                ).total_seconds() / 60),
                                                "consideration": f"passed {t['12hours']}"
                                            } for t in sorted_timeorders
                                        ] if day != 0 else []
                                    )
                                } if day != 0 and day >= current_day else {"day": None}
                            } for day in week
                        ]
                    } for week_idx, week in enumerate(calendar.monthcalendar(current_year, current_month))
                    if any(day >= current_day or day == 0 for day in week)
                ]
            },
            {
                "year": next_year,
                "month": calendar.month_name[next_month],
                "days": [
                    {
                        "week": week_idx + 1,
                        "days": [
                            {
                                "day": {
                                    "date": f"{day:02d}/{next_month:02d}/{next_year}" if day != 0 else None,
                                    "time_12hour": "00:00 pm" if day != 0 else None,
                                    "time_24hour": "00:00" if day != 0 else None,
                                    "time_ahead": [
                                        {
                                            "id": f"{day:02d}_{t['24hours'].replace(':', '')}",
                                            "12hours": t["12hours"],
                                            "24hours": t["24hours"],
                                            "minutes_DISTANCE": int((
                                                datetime.strptime(
                                                    f"{day:02d}/{next_month:02d}/{next_year} {t['24hours']}",
                                                    "%d/%m/%Y %H:%M"
                                                ) - current_datetime
                                            ).total_seconds() / 60),
                                            "consideration": f"passed {t['12hours']}"
                                        } for t in sorted_timeorders
                                    ] if day != 0 else []
                                } if day != 0 else {"day": None}
                            } for day in week
                        ]
                    } for week_idx, week in enumerate(calendar.monthcalendar(next_year, next_month))
                ]
            }
        ]
    }
    
    # Define output path with author, group_types, and type
    output_path = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}\\{type_value}calendar.json"
    print(f"Writing calendar data to {output_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write to JSON file
    with open(output_path, 'w') as f:
        json.dump(calendar_data, f, indent=4)
    print(f"Calendar data successfully written to {output_path}")
    
    # Call schedule_time
    update_timeschedule()

def update_timeschedule():
    """Move next → last (OVERWRITE), generate NEW next_schedule starting AFTER schedule_date."""
    import os
    import json
    from datetime import datetime, timedelta

    # --------------------------------------------------------------------- #
    # 1. Load config
    # --------------------------------------------------------------------- #
    pageauthors_path = r"C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json"
    try:
        with open(pageauthors_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Config error: {e}")
        return

    author        = cfg['author']
    type_value    = cfg['type']
    group_types   = cfg['group_types']
    cardamount    = int(cfg.get('cardamount', 1))
    schedule_date_str = cfg.get('schedule_date', '').strip()

    print(f"Config loaded: author={author}, type={type_value}, cardamount={cardamount}, schedule_date='{schedule_date_str}'")

    # --------------------------------------------------------------------- #
    # 2. Parse schedule_date (must be valid)
    # --------------------------------------------------------------------- #
    base_datetime = None
    if schedule_date_str:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(schedule_date_str.split('.')[0], fmt)  # ignore milliseconds
                if ' ' not in schedule_date_str:
                    dt = dt.replace(hour=0, minute=0)
                base_datetime = dt
                print(f"Using schedule_date: {base_datetime.strftime('%d/%m/%Y %H:%M')}")
                break
            except ValueError:
                continue

    if base_datetime is None:
        base_datetime = datetime.now()
        print(f"Invalid schedule_date. Falling back to now: {base_datetime.strftime('%d/%m/%Y %H:%M')}")

    # --------------------------------------------------------------------- #
    # 3. Load timeorders
    # --------------------------------------------------------------------- #
    timeorders_path = r"C:\xampp\htdocs\serenum-csv\timeorders.json"
    try:
        with open(timeorders_path, 'r', encoding='utf-8') as f:
            timeorders_data = json.load(f)
    except Exception as e:
        print(f"Timeorders error: {e}")
        return

    if type_value not in timeorders_data:
        print(f"Type '{type_value}' not in timeorders.json")
        return

    timeorders = sorted(timeorders_data[type_value], key=lambda x: x["24hours"])
    valid_times_24 = [t["24hours"] for t in timeorders]
    time_map = {t["24hours"]: t["12hours"] for t in timeorders}

    print(f"Valid time slots for '{type_value}': {', '.join(valid_times_24)}")

    # --------------------------------------------------------------------- #
    # 4. Paths
    # --------------------------------------------------------------------- #
    base_dir = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}"
    schedules_path = os.path.join(base_dir, f"{type_value}schedules.json")

    # --------------------------------------------------------------------- #
    # 5. Load existing schedules
    # --------------------------------------------------------------------- #
    old_last_schedule = []
    old_next_schedule = []
    if os.path.exists(schedules_path):
        try:
            with open(schedules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            old_last_schedule = data.get("last_schedule", [])
            old_next_schedule = data.get("next_schedule", [])
            print(f"Loaded: {len(old_last_schedule)} last, {len(old_next_schedule)} next")
        except Exception as e:
            print(f"Error reading schedules.json: {e}")

    # --------------------------------------------------------------------- #
    # 6. STEP 1: Overwrite last_schedule with old_next_schedule
    # --------------------------------------------------------------------- #
    new_last_schedule = []
    for item in old_next_schedule:
        if isinstance(item, dict):
            new_last_schedule.append(item)
        elif isinstance(item, str):
            # Legacy migration
            if '_' not in item:
                continue
            day, time_part = item.split('_', 1)
            time_24 = f"{time_part[:2]}:{time_part[2:]}"
            time_12 = time_map.get(time_24, "12:00 AM")
            migrated = {
                "id": item,
                "date": f"{day.zfill(2)}/{base_datetime.strftime('%m/%Y')}",
                "time_12hour": time_12,
                "time_24hour": time_24
            }
            new_last_schedule.append(migrated)
            print(f"Migrated legacy: {item} → {migrated}")
        else:
            print(f"Skipping invalid schedule item: {item}")

    print(f"last_schedule updated with {len(new_last_schedule)} slot(s)")

    # --------------------------------------------------------------------- #
    # 7. Build used_ids from new_last_schedule
    # --------------------------------------------------------------------- #
    used_ids = {slot.get("id") for slot in new_last_schedule if isinstance(slot, dict)}

    # --------------------------------------------------------------------- #
    # 8. Generate next_schedule: start AFTER base_datetime
    # --------------------------------------------------------------------- #
    next_schedule_list = []
    current_search = base_datetime
    max_days_ahead = 60  # safety
    days_searched = 0

    while len(next_schedule_list) < cardamount and days_searched < max_days_ahead:
        day_searched = current_search.date()
        day_str = day_searched.strftime("%d/%m/%Y")

        for t in timeorders:
            if len(next_schedule_list) >= cardamount:
                break

            slot_time_24 = t["24hours"]
            try:
                slot_datetime = datetime.combine(day_searched, datetime.strptime(slot_time_24, "%H:%M").time())
            except:
                continue

            # Must be AFTER base_datetime
            if slot_datetime <= base_datetime:
                continue

            # Today: apply 50-minute buffer
            if day_searched == base_datetime.date():
                minutes_diff = (slot_datetime - base_datetime).total_seconds() / 60
                if minutes_diff < 50:
                    continue
            # Future days: allow immediate slot (e.g., 00:05)

            slot_id = f"{day_searched.day:02d}_{slot_time_24.replace(':', '')}"

            if slot_id in used_ids:
                continue

            new_slot = {
                "id": slot_id,
                "date": day_str,
                "time_12hour": t["12hours"],
                "time_24hour": slot_time_24
            }
            next_schedule_list.append(new_slot)
            used_ids.add(slot_id)
            print(f"Added to next: {day_str} {slot_time_24} ({slot_id})")

        # Move to next day
        current_search += timedelta(days=1)
        days_searched += 1

    if not next_schedule_list:
        print("No available slots found after schedule_date.")
        return

    # --------------------------------------------------------------------- #
    # 9. Write schedules.json
    # --------------------------------------------------------------------- #
    output_data = {
        "last_schedule": new_last_schedule,
        "next_schedule": next_schedule_list
    }
    os.makedirs(os.path.dirname(schedules_path), exist_ok=True)
    with open(schedules_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"Schedules written to {schedules_path}")

    # --------------------------------------------------------------------- #
    # 10. Update schedule_date to LAST slot in next_schedule
    # --------------------------------------------------------------------- #
    if next_schedule_list:
        last_slot = next_schedule_list[-1]
        try:
            new_schedule_date = datetime.strptime(
                f"{last_slot['date']} {last_slot['time_24hour']}",
                "%d/%m/%Y %H:%M"
            )
            cfg["schedule_date"] = new_schedule_date.strftime("%d/%m/%Y %H:%M")
            with open(pageauthors_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
            print(f"schedule_date updated to: {cfg['schedule_date']}")
        except Exception as e:
            print(f"Failed to update schedule_date: {e}")

    print(f"SUCCESS: {len(next_schedule_list)} new slot(s) scheduled.")
    print(f"         last_schedule: {len(new_last_schedule)} slot(s)")

    # --------------------------------------------------------------------- #
    # 11. Optional: randomize minutes
    # --------------------------------------------------------------------- #
    try:
        randomize_next_schedule_minutes()
    except NameError:
        pass
       
def randomize_next_schedule_minutes():
    """
    Randomize minutes (01–30) for EACH slot in next_schedule using its OWN hour.
    Preserves original hour, only changes minutes.
    """

    # === Load config ===
    pageauthors_path = r"C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json"
    try:
        with open(pageauthors_path, 'r', encoding='utf-8') as f:
            pageauthors = json.load(f)
    except Exception as e:
        print(f"[randomize] Config error: {e}")
        return

    author = pageauthors.get('author')
    type_value = pageauthors.get('type')
    group_types = pageauthors.get('group_types', '')

    if not author or not type_value:
        print("[randomize] Missing author or type in config")
        return

    # === Build path ===
    schedules_path = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}\\{type_value}schedules.json"

    if not os.path.exists(schedules_path):
        print(f"[randomize] schedules.json not found: {schedules_path}")
        return

    # === Read schedule ===
    try:
        with open(schedules_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[randomize] Error reading JSON: {e}")
        return

    if 'next_schedule' not in data or not data['next_schedule']:
        print("[randomize] No next_schedule to randomize.")
        return

    schedule_list = data['next_schedule']
    if isinstance(schedule_list, dict):
        schedule_list = [schedule_list]

    updated_slots = []
    for slot in schedule_list:
        try:
            old_time = slot.get('time_24hour')
            if not old_time or ':' not in old_time:
                print(f"[randomize] Invalid time_24hour in slot: {slot}")
                continue

            hour = int(old_time.split(':')[0])
            new_min = random.randint(1, 30)  # 01 to 30
            new_time_24 = f"{hour:02d}:{new_min:02d}"

            # Format 12-hour time
            dt = datetime.strptime(new_time_24, "%H:%M")
            new_time_12 = dt.strftime("%I:%M %p").lstrip("0").lower()
            new_time_12 = new_time_12.replace(" 0", " ").replace("am", "AM").replace("pm", "PM")
            if new_time_12.startswith("0"):
                new_time_12 = new_time_12[1:]

            # Update slot
            slot["time_24hour"] = new_time_24
            slot["time_12hour"] = new_time_12
            updated_slots.append(f"{slot['date']} {new_time_24}")

        except Exception as e:
            print(f"[randomize] Failed to process slot {slot}: {e}")
            continue

    # === Write back ===
    try:
        with open(schedules_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"[randomize] Successfully randomized {len(updated_slots)} slots (minutes 01–30):")
        for s in sorted(updated_slots):
            print(f"  → {s}")
    except Exception as e:
        print(f"[randomize] Failed to save file: {e}")

def check_schedule_time():
    """Check if the next schedule in schedules.json is behind the current time."""
    # Get current date and time
    now = datetime.now()
    current_time_24hour = now.strftime("%H:%M")
    current_date = now.strftime("%d/%m/%Y")
    current_datetime = datetime.strptime(f"{current_date} {current_time_24hour}", "%d/%m/%Y %H:%M")
    
    print(f"Current date and time: {current_date} {current_time_24hour}")
    
    # Read pageandgroupauthors.json to get author, type, and group_types
    pageauthors_path = r"C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json"
    print(f"Reading pageandgroupauthors.json from {pageauthors_path}")
    try:
        with open(pageauthors_path, 'r') as f:
            pageauthors = json.load(f)
    except FileNotFoundError:
        print(f"Error: pageandgroupauthors.json not found at {pageauthors_path}")
        return
    except json.decoder.JSONDecodeError:
        print(f"Error: pageandgroupauthors.json contains invalid JSON")
        return
    
    author = pageauthors['author']
    type_value = pageauthors['type']
    group_types = pageauthors['group_types']
    print(f"Author: {author}, Type: {type_value}, Group Types: {group_types}")
    
    # Read schedules.json based on new path structure
    schedules_path = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}\\{type_value}schedules.json"
    print(f"Reading schedules.json from {schedules_path}")
    if not os.path.exists(schedules_path):
        print(f"Error: schedules.json not found at {schedules_path}")
        update_calendar()
        return
    
    try:
        with open(schedules_path, 'r') as f:
            schedules_data = json.load(f)
    except json.decoder.JSONDecodeError:
        print(f"Error: schedules.json contains invalid JSON")
        return
    
    # Check for next_schedule
    if 'next_schedule' not in schedules_data:
        print(f"Error: 'next_schedule' field missing in schedules.json")
        update_calendar()
        return
    
    next_schedule = schedules_data['next_schedule']
    if not next_schedule:
        print("No next schedule found in schedules.json")
        return
    
    # Extract next schedule date and time
    try:
        next_schedule_date = next_schedule['date']
        next_schedule_time = next_schedule['time_24hour']
        next_schedule_datetime = datetime.strptime(f"{next_schedule_date} {next_schedule_time}", "%d/%m/%Y %H:%M")
    except (KeyError, ValueError) as e:
        print(f"Error: Invalid date or time format in next_schedule: {next_schedule}. Error: {str(e)}")
        return
    
    # Compare with current time
    if next_schedule_datetime < current_datetime:
        print(f"Next schedule is behind the current time: {next_schedule_date} {next_schedule_time} is earlier than {current_date} {current_time_24hour}")
        update_timeschedule()
    else:
        print(f"Next schedule is valid: {next_schedule_date} {next_schedule_time} is not behind {current_date} {current_time_24hour}")

def generate_final_csv():
    """FINAL JARVEE-COMPATIBLE CSV – EXACT FORMAT AS YOUR WORKING EXAMPLE"""
    
    # ------------------------------------------------------------------ #
    # 1. Load config
    # ------------------------------------------------------------------ #
    CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        author = config.get('author', '').strip()
        group_types = config.get('group_types', '').strip()
        cardamount = int(config.get('cardamount', 1))
        type_value = config.get('type', 'fullorders')
        
        if not author or not group_types:
            print("Error: Missing author or group_types")
            return
        
        print(f"Generating JARVEE-READY CSV → {author} ({group_types}) | {cardamount} posts")
        
    except Exception as e:
        print(f"Config error: {e}")
        return

    # ------------------------------------------------------------------ #
    # 2. Paths
    # ------------------------------------------------------------------ #
    captions_path = rf'C:\xampp\htdocs\serenum-csv\files\captions\{author}({group_types}).json'
    jpg_path = rf'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}\next_jpgcard.json'
    sched_dir = rf'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}\jsons\{group_types}'
    sched_path = os.path.join(sched_dir, f"{type_value}schedules.json")
    
    csv_dir = rf'C:\xampp\htdocs\serenum-csv\files\csv\{author}\{group_types}'
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, f"{author}_posts.csv")
    print(f"Saving → {csv_path}")

    # ------------------------------------------------------------------ #
    # 3. Load captions
    # ------------------------------------------------------------------ #
    if not os.path.exists(captions_path):
        print(f"Captions missing: {captions_path}")
        return

    try:
        with open(captions_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        
        captions = []
        for item in raw:
            if isinstance(item, dict) and 'description' in item:
                desc = str(item['description']).strip()
                if desc:
                    desc = desc.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                    captions.append(desc)
        
        if not captions:
            print("No captions!")
            return
        print(f"Captions loaded: {len(captions)}")
    except Exception as e:
        print(f"Captions error: {e}")
        return

    # ------------------------------------------------------------------ #
    # 4. Load images
    # ------------------------------------------------------------------ #
    if not os.path.exists(jpg_path):
        print(f"next_jpgcard.json missing: {jpg_path}")
        return

    try:
        with open(jpg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            images = data.get("next_jpgcard", [])[:cardamount]
        if not images:
            print("No images!")
            return
        print(f"Images: {len(images)}")
    except Exception as e:
        print(f"Image error: {e}")
        return

    # ------------------------------------------------------------------ #
    # 5. Load schedule
    # ------------------------------------------------------------------ #
    if not os.path.exists(sched_path):
        print(f"schedules.json missing: {sched_path}")
        return

    try:
        with open(sched_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            schedule = data.get("next_schedule", [])[:cardamount]
        if not schedule:
            print("No schedule!")
            return
        print(f"Schedule slots: {len(schedule)}")
    except Exception as e:
        print(f"Schedule error: {e}")
        return

    # ------------------------------------------------------------------ #
    # 6. Final count
    # ------------------------------------------------------------------ #
    final_count = min(cardamount, len(images), len(schedule), len(captions))
    if final_count == 0:
        print("Nothing to generate.")
        return

    print(f"\nBuilding {final_count} JARVEE-READY posts...\n")

    # ------------------------------------------------------------------ #
    # 7. Build rows – CORRECT DATE FORMAT: YYYY-MM-DD HH:MM
    # ------------------------------------------------------------------ #
    rows = []
    caption_idx = 0

    for i in range(final_count):
        caption = captions[caption_idx % len(captions)]
        caption_idx += 1
        img_url = images[i]
        slot = schedule[i]

        # CONVERT: 15/11/2025 00:29 → 2025-11-15 00:29
        date_parts = slot['date'].split('/')
        yyyy_mm_dd = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
        post_time = f"{yyyy_mm_dd} {slot['time_24hour']}"  # NO :00 seconds!

        rows.append({
            "Text": caption,
            "Image URL": img_url,
            "Tags": "",
            "Posting Time": post_time
        })

        card = img_url.split('/')[-1].split('?')[0]
        print(f"{i+1:2}. {post_time} → {card}")

    # ------------------------------------------------------------------ #
    # 8. WRITE PERFECT JARVEE CSV
    # ------------------------------------------------------------------ #
    try:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Text", "Image URL", "Tags", "Posting Time"],
                quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(rows)

        print("\n" + "═" * 100)
        print(f"JARVEE-READY CSV GENERATED!")
        print(f"   → {csv_path}")
        print(f"   {len(rows)} posts | EXACT FORMAT AS YOUR WORKING EXAMPLE")
        print("═" * 100)
        print(f"First post:")
        print(f"   \"{rows[0]['Text']}\"")
        print(f"   Time: {rows[0]['Posting Time']}")
        print(f"   Card: {rows[0]['Image URL'].split('/')[-1]}")
        print("═" * 100)

    except Exception as e:
        print(f"Save failed: {e}")


def uploadedjpgs():
    """Archive VALID URLs from next_jpgcard.json → uploadedjpgs.json
       AND DELETE **ALL** files from BOTH:
         - next jpg folder
         - uploaded jpgs folder
       Only valid URLs are preserved. Safe, robust, full logging."""

    # ------------------------------------------------------------------ #
    # 1. Load configuration
    # ------------------------------------------------------------------ #
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'

    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        author = config.get('author', '').strip()
        if not author:
            print("Error: 'author' is missing or empty in config.")
            return

    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    # ------------------------------------------------------------------ #
    # 2. Define paths
    # ------------------------------------------------------------------ #
    next_dir       = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    uploaded_dir   = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}'
    next_json_path = os.path.join(next_dir, 'next_jpgcard.json')
    uploaded_json_path = os.path.join(uploaded_dir, 'uploadedjpgs.json')

    os.makedirs(next_dir, exist_ok=True)
    os.makedirs(uploaded_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 3. Load next_jpgcard.json – keep ONLY valid URLs
    # ------------------------------------------------------------------ #
    next_urls = []
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw = data.get("next_jpgcard")

            if raw is not None:
                items = [raw] if isinstance(raw, str) else raw
                for item in items:
                    if isinstance(item, str):
                        url = item.strip()
                        if url.lower().startswith(('http://', 'https://')):
                            next_urls.append(url)
                        else:
                            print(f"Skipped invalid URL: {url}")
        except Exception as e:
            print(f"Failed to read next_jpgcard.json: {e}")
    else:
        print(f"Info: No next_jpgcard.json found.")

    print(f"Detected {len(next_urls)} valid URL(s) to archive.")

    # ------------------------------------------------------------------ #
    # 4. Delete ALL files from next jpg folder
    # ------------------------------------------------------------------ #
    next_files = [f for f in os.listdir(next_dir) if os.path.isfile(os.path.join(next_dir, f))]
    next_deleted = 0
    next_failed = []

    if next_files:
        print(f"\nDeleting {len(next_files)} file(s) from next jpg:")
        for f in next_files:
            path = os.path.join(next_dir, f)
            try:
                os.remove(path)
                next_deleted += 1
                print(f"   Deleted: next jpg/{f}")
            except Exception as e:
                next_failed.append((f, str(e)))
                print(f"   Failed: {f} → {e}")
    else:
        print("\nnext jpg folder already empty.")

    # ------------------------------------------------------------------ #
    # 5. Delete ALL files from uploaded jpgs folder (except JSON)
    # ------------------------------------------------------------------ #
    uploaded_files = [
        f for f in os.listdir(uploaded_dir)
        if os.path.isfile(os.path.join(uploaded_dir, f)) and f != 'uploadedjpgs.json'
    ]
    uploaded_deleted = 0
    uploaded_failed = []

    if uploaded_files:
        print(f"\nDeleting {len(uploaded_files)} file(s) from uploaded jpgs:")
        for f in uploaded_files:
            path = os.path.join(uploaded_dir, f)
            try:
                os.remove(path)
                uploaded_deleted += 1
                print(f"   Deleted: uploaded jpgs/{f}")
            except Exception as e:
                uploaded_failed.append((f, str(e)))
                print(f"   Failed: {f} → {e}")
    else:
        print("\nuploaded jpgs folder has no extra files.")

    # ------------------------------------------------------------------ #
    # 6. Load existing uploadedjpgs.json – keep ONLY valid URLs
    # ------------------------------------------------------------------ #
    existing_uploaded = []
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                raw = existing_data.get("uploaded_jpgs", [])
                candidates = [raw] if isinstance(raw, str) else raw
                for u in candidates:
                    if isinstance(u, str) and u.strip().lower().startswith(('http://', 'https://')):
                        existing_uploaded.append(u.strip())
        except Exception as e:
            print(f"Warning: Could not read uploadedjpgs.json: {e}")

    print(f"Found {len(existing_uploaded)} previously valid URLs.")

    # ------------------------------------------------------------------ #
    # 7. Combine & deduplicate URLs
    # ------------------------------------------------------------------ #
    all_urls = existing_uploaded + next_urls
    unique_urls = list(dict.fromkeys(all_urls))  # Preserves order
    newly_added = len(unique_urls) - len(existing_uploaded)

    # ------------------------------------------------------------------ #
    # 8. Save updated uploadedjpgs.json
    # ------------------------------------------------------------------ #
    timestamp = datetime.now(pytz.timezone('Africa/Lagos')).isoformat()

    uploaded_data = {
        "uploaded_jpgs": unique_urls,
        "last_cleared": timestamp,
        "total_uploaded": len(unique_urls),
        "urls_added_this_time": len(next_urls),
        "new_unique_urls": newly_added,
        "next_jpg_files_deleted": next_deleted,
        "uploaded_jpgs_files_deleted": uploaded_deleted,
        "failed_deletes_next": [f"{n}: {e}" for n, e in next_failed],
        "failed_deletes_uploaded": [f"{n}: {e}" for n, e in uploaded_failed],
        "author": author
    }

    try:
        with open(uploaded_json_path, 'w', encoding='utf-8') as f:
            json.dump(uploaded_data, f, indent=4, ensure_ascii=False)
        print(f"\nSaved uploadedjpgs.json → {len(unique_urls)} clean URLs")
    except Exception as e:
        print(f"Failed to write JSON: {e}")
        return

    # ------------------------------------------------------------------ #
    # 9. Clear next_jpgcard.json
    # ------------------------------------------------------------------ #
    try:
        cleared = {
            "next_jpgcard": [],
            "timestamp": timestamp,
            "total_checked": data.get("total_checked", 0) if 'data' in locals() else 0,
            "total_valid": len(next_urls),
            "note": "Cleared by uploadedjpgs() – ALL files deleted from both folders"
        }
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump(cleared, f, indent=4, ensure_ascii=False)
        print("Cleared next_jpgcard.json")
    except Exception as e:
        print(f"Warning: Could not clear next_jpgcard.json: {e}")

    # ------------------------------------------------------------------ #
    # 10. Final Summary
    # ------------------------------------------------------------------ #
    print("\n" + "="*70)
    print(f" FULL CLEANUP COMPLETE FOR @{author.upper()}")
    print(f"   URLs archived       : {len(next_urls)} → {newly_added} new")
    print(f"   next jpg deleted    : {next_deleted} file(s)")
    print(f"   uploaded jpgs deleted: {uploaded_deleted} file(s)")
    if next_failed: print(f"   next failed         : {len(next_failed)}")
    if uploaded_failed: print(f"   uploaded failed     : {len(uploaded_failed)}")
    print(f"   Total valid URLs    : {len(unique_urls)}")
    print(f"   Both folders now clean (except uploadedjpgs.json)")
    print("="*70)
    print(f"\nReady for fresh upload cycle. @teamxtech")



def moveuploadedurls():
    """
    Automates moving uploaded JPG URLs to the 'Uploaded' folder on jpgsvault.rf.gd using Selenium.
    After successful move:
      • Deletes ALL image files (.jpg, .png, .gif, etc.) from:
          - jpgfolders\{author}
          - next jpg\{author}
          - uploaded jpgs\{author}
      • Clears next_jpgcard.json
      • Removes moved URLs from uploadedjpgs.json
    Full cleanup for a clean slate.
    """
    # --------------------- CONFIG & PATHS ---------------------
    TARGET_URL = "https://jpgsvault.rf.gd/jpgsvault.php"
    CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'
    UPLOADED_JSON_DIR = r'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs'
    NEXT_JSON_DIR = r'C:\xampp\htdocs\serenum-csv\files\next jpg'
    JPGFOLDERS_DIR = r'C:\xampp\htdocs\serenum-csv\files\jpgfolders'
    CHROME_BINARY = r"C:\xampp\htdocs\CIPHER\googlechrome\Google\Chrome\Application\chrome.exe"

    # Supported image extensions (case-insensitive)
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.ico', '.svg'}

    print("\n" + "="*80)
    print("STARTING: move uploaded urls + FULL IMAGE CLEANUP (ALL FOLDERS)")
    print("="*80)

    # --------------------- LOAD CONFIG ---------------------
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: Config file not found: {CONFIG_PATH}")
        return

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        author = config.get('author', '').strip()
        if not author:
            print("ERROR: 'author' is missing or empty in config.")
            return
        print(f"Author: {author}")
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        return

    # --------------------- DERIVED PATHS ---------------------
    uploaded_json_path = os.path.join(UPLOADED_JSON_DIR, author, 'uploadedjpgs.json')
    next_json_path = os.path.join(NEXT_JSON_DIR, author, 'next_jpgcard.json')
    jpgfolder_dir = os.path.join(JPGFOLDERS_DIR, author)
    next_dir = os.path.join(NEXT_JSON_DIR, author)
    uploaded_dir = os.path.join(UPLOADED_JSON_DIR, author)

    # Ensure all author directories exist
    author_dirs = {
        'jpgfolders': jpgfolder_dir,
        'next_jpg': next_dir,
        'uploaded_jpgs': uploaded_dir
    }

    for name, path in author_dirs.items():
        if not os.path.exists(path):
            print(f"WARNING: Directory not found: {path} ({name})")
        else:
            print(f"Found: {path} ({name})")

    if not os.path.exists(uploaded_json_path):
        print(f"ERROR: uploadedjpgs.json not found: {uploaded_json_path}")
        return

    # --------------------- LOAD UPLOADED URLS TO MOVE ---------------------
    try:
        with open(uploaded_json_path, 'r', encoding='utf-8') as f:
            uploaded_data = json.load(f)
        all_uploaded_urls = uploaded_data.get("uploaded_jpgs", [])
    except Exception as e:
        print(f"ERROR: Failed to read uploadedjpgs.json: {e}")
        return

    if not all_uploaded_urls:
        print("No URLs in uploadedjpgs.json. Nothing to move.")
        return

    # Load next_jpgcard to know which ones were just marked
    next_urls = []
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                next_data = json.load(f)
            next_urls = next_data.get("next_jpgcard", [])
        except Exception as e:
            print(f"Warning: Could not read next_jpgcard.json: {e}")
    else:
        print("No next_jpgcard.json found. Will move all in uploadedjpgs.json.")

    # Use next_urls if available, else fall back to all
    urls_to_move = next_urls if next_urls else all_uploaded_urls
    if not urls_to_move:
        print("No URLs to move (next_jpgcard empty and no fallback).")
        return

    print(f"Preparing to move {len(urls_to_move)} URL(s) to 'Uploaded' folder...")

    # --------------------- SETUP SELENIUM ---------------------
    driver = None
    success = False
    try:
        options = Options()
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-autofill")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

        if os.path.exists(CHROME_BINARY):
            options.binary_location = CHROME_BINARY
            print("Using custom Chrome binary.")
        else:
            print("Custom Chrome binary not found. Using default.")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(driver_version="139.0.7258.128").install()),
            options=options
        )
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        print(f"Navigating to: {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(3)

        # Click "FOLDERS ▼"
        print('Clicking "FOLDERS ▼"')
        folder_toggle = driver.find_element(By.ID, "folder-toggle")
        folder_toggle.click()
        time.sleep(1)

        # Click author folder
        print(f'Opening folder: "{author}"')
        folder_menu = driver.find_element(By.ID, "folder-menu")
        author_folder_xpath = f".//div[contains(@class, 'folder-item')]//span[@class='folder-name' and text()='{author}']"
        author_folder = folder_menu.find_element(By.XPATH, author_folder_xpath)
        author_folder.click()
        time.sleep(2)

        # Click "Move to Uploaded"
        print('Clicking "Move to Uploaded"')
        move_btn = driver.find_element(By.ID, "move-to-uploaded-btn")
        move_btn.click()
        time.sleep(1)

        # Input URLs
        print(f"Pasting {len(urls_to_move)} URL(s)...")
        textarea = driver.find_element(By.ID, "move-indices")
        url_input = ",\n".join(urls_to_move)
        textarea.clear()
        textarea.send_keys(url_input)

        # Click Move
        print('Confirming move...')
        move_yes_btn = driver.find_element(By.ID, "move-yes")
        move_yes_btn.click()
        time.sleep(4)

        # Check success
        try:
            alert_modal = driver.find_element(By.ID, "alert-modal")
            alert_msg = alert_modal.find_element(By.ID, "alert-message").text
            print(f"Server: {alert_msg}")

            if "moved" in alert_msg.lower() and "to uploaded" in alert_msg.lower():
                success = True
                print("SUCCESS: Server confirmed move!")
                alert_ok = driver.find_element(By.ID, "alert-ok")
                alert_ok.click()
            else:
                print("WARNING: Move may have failed. Check message.")
        except Exception as e:
            print(f"WARNING: No alert appeared. Exception: {e}")

    except Exception as e:
        print(f"SELENIUM ERROR: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")

    # --------------------- FULL CLEANUP (ONLY IF SUCCESS) ---------------------
    if not success:
        print("\nCLEANUP SKIPPED: Move was not confirmed successful.")
        return

    print("\n" + "-"*60)
    print("STARTING FULL IMAGE CLEANUP ACROSS ALL AUTHOR FOLDERS")
    print("-"*60)

    deleted_files = 0
    failed_deletes = 0

    def is_image_file(filepath):
        """Check if file is an image by extension AND content (using imghdr)"""
        if not os.path.isfile(filepath):
            return False
        ext = os.path.splitext(filepath)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            # Double-check with imghdr (except for SVG which is XML)
            if ext == '.svg':
                return True
            try:
                return imghdr.what(filepath) is not None
            except:
                return ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        return False

    def delete_images_in_folder(folder_path, label):
        nonlocal deleted_files, failed_deletes
        if not os.path.exists(folder_path):
            print(f"{label} not found: {folder_path}")
            return
        print(f"Scanning for images in: {folder_path}")
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if is_image_file(file_path):
                try:
                    os.remove(file_path)
                    deleted_files += 1
                    print(f"  [DELETED] {label}/{filename}")
                except Exception as e:
                    failed_deletes += 1
                    print(f"  [FAILED] {label}/{filename} → {e}")

    # 1. Delete ALL images from all three author directories
    delete_images_in_folder(jpgfolder_dir, "jpgfolders")
    delete_images_in_folder(next_dir, "next jpg")
    delete_images_in_folder(uploaded_dir, "uploaded jpgs")

    # 2. Clear next_jpgcard.json
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "next_jpgcard": [],
                    "timestamp": datetime.now(pytz.timezone('Africa/Lagos')).isoformat(),
                    "note": "Cleared after successful move to Uploaded folder"
                }, f, indent=4)
            print(f"Cleared: {next_json_path}")
        except Exception as e:
            print(f"Failed to clear next_jpgcard.json: {e}")
    else:
        print("next_jpgcard.json not found (already clean)")

    # 3. Remove moved URLs from uploadedjpgs.json
    remaining_urls = [u for u in all_uploaded_urls if u not in urls_to_move]
    try:
        timestamp = datetime.now(pytz.timezone('Africa/Lagos')).isoformat()
        new_data = {
            "uploaded_jpgs": remaining_urls,
            "last_moved_to_uploaded": timestamp,
            "total_uploaded": len(remaining_urls),
            "last_moved_count": len(urls_to_move),
            "author": author
        }
        with open(uploaded_json_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4)
        print(f"Updated uploadedjpgs.json → {len(remaining_urls)} remaining")
    except Exception as e:
        print(f"Failed to update uploadedjpgs.json: {e}")

    # --------------------- FINAL SUMMARY ---------------------
    print("\n" + "="*80)
    print("FULL CLEANUP COMPLETE")
    print("="*80)
    print(f"Moved URLs             : {len(urls_to_move)}")
    print(f"Total images deleted   : {deleted_files}")
    print(f"Delete failures        : {failed_deletes}")
    print(f"Remaining in uploaded  : {len(remaining_urls)}")
    print(f"next_jpgcard.json      : CLEARED")
    print(f"All author image dirs  : CLEANED (.jpg, .png, .gif, .webp, etc.)")
    print("="*80)
    print("All done. Ready for next batch!")


def main():
    fetch_urls()
    corruptedjpgs()
    markjpgs()
    corruptedjpgs()
    crop_and_moveto_jpgs()
    update_calendar()
    generate_final_csv()
    uploadedjpgs()
    



if __name__ == "__main__":
   markjpgs()
   

