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
import os
import json
import csv
import random
import string
import psutil
from datetime import datetime, timezone
import connectwithinfinitydb as db
import json
import os
from datetime import datetime
import time
from selenium.webdriver.common.by import By
import re
from datetime import datetime, timezone
from webdriver_manager.chrome import ChromeDriverManager



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




# Force bypass of SSL verification for ChromeDriverManager
os.environ['WDM_SSL_VERIFY'] = '0'
   
def fetch_jpgsvault_urls():
    """
    Modified function to fetch all_urls data from jpgsvault_table
    Properly handles JSON array format from the database
    Clears existing data before saving new URLs
    """
    import json as json_module  # Rename to avoid conflict with your json variable
    import os
    
    # Inner function for manual parsing
    def manual_parse_urls(urls_field):
        """
        Fallback parser for when JSON parsing fails
        Handles various formats like comma-separated, newline-separated, etc.
        """
        urls_list = []
        
        # Try comma separation first
        if ',' in urls_field:
            # Split by comma but be careful with escaped commas
            parts = urls_field.split(',')
            for part in parts:
                part = part.strip()
                # Remove brackets and quotes
                part = re.sub(r'^[\[\]"\']+|[\[\]"\']+$', '', part)
                if part:
                    urls_list.append(part)
        elif '\n' in urls_field:
            # Split by newline
            for line in urls_field.split('\n'):
                line = line.strip()
                if line:
                    urls_list.append(line)
        else:
            # Single URL
            urls_list.append(urls_field.strip())
        
        return urls_list
    
    try:
        print(f"[ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ] Starting fetch from jpgsvault_table...")
        
        # Query to get all_urls column from jpgsvault_table
        query = "SELECT all_urls FROM jpgsvault_table" 
        result = db.execute_query(query)  # Using the global execute_query function
        
        if result.get('status') != 'success':
            print(f"QUERY ERROR: {result.get('message')}")
            return []
            
        rows = result.get('results', [])
        
        if not rows:
            print("WARNING: Database returned 'success' but the results list is empty.")
            print("Check if the table 'jpgsvault_table' actually has rows in the PHP interface.")
            return []
        
        print(f"SUCCESS: Fetched {len(rows)} records from 'jpgsvault_table'")
        
        # Extract all URLs from the rows
        all_urls = []
        seen_urls = set()
        skipped_count = 0
        metadata_count = 0
        urls_list = []  # Initialize for statistics
        
        for row in rows:
            # Get the all_urls field from each row
            urls_field = row.get('all_urls', '')
            
            if urls_field:
                # Try to parse as JSON array first
                urls_list = []
                
                # Check if it looks like a JSON array
                if urls_field.strip().startswith('[') and urls_field.strip().endswith(']'):
                    try:
                        # Parse as JSON array
                        urls_list = json_module.loads(urls_field)
                        print(f"Successfully parsed JSON array with {len(urls_list)} items")
                    except json_module.JSONDecodeError as e:
                        print(f"JSON parse error: {e}, falling back to manual parsing")
                        # Fallback to manual parsing if JSON fails
                        urls_list = manual_parse_urls(urls_field)
                else:
                    # Try other formats
                    urls_list = manual_parse_urls(urls_field)
                
                # Process each URL in the list
                for url in urls_list:
                    # Skip metadata entries like "total_urls: 9684"
                    if isinstance(url, str):
                        url_lower = url.lower().strip()
                        if url_lower.startswith('total_urls:') or url_lower.startswith('total_urls='):
                            print(f"Skipping metadata entry: {url}")
                            metadata_count += 1
                            continue
                    
                    url = str(url).strip()
                    
                    # Skip empty strings
                    if not url:
                        skipped_count += 1
                        continue
                    
                    # Remove quotes if present (from manual parsing)
                    url = url.strip('"').strip("'")
                    
                    # Fix escaped slashes
                    url = url.replace('\\/', '/')
                    
                    # Remove any leading/trailing brackets or weird characters
                    url = re.sub(r'^[\["\']+|[\]"\']+$', '', url)
                    
                    # Handle the URL construction
                    original_url = url  # Keep for debugging
                    
                    if 'jpgs' in url.lower():
                        # Find where jpgs starts
                        jpgs_index = url.lower().find('jpgs')
                        if jpgs_index != -1:
                            path_part = url[jpgs_index:]
                            # Clean up the path
                            path_part = path_part.replace('\\', '/')
                            # Replace multiple slashes with single slash
                            path_part = re.sub(r'/+', '/', path_part)
                            # Remove any quotes or brackets from path
                            path_part = re.sub(r'["\'\[\]]', '', path_part)
                            # Construct clean URL
                            url = f'http://fhdrikxsirudr.fwh.is/{path_part}'
                        else:
                            # If no jpgs found, treat as relative path
                            url = url.replace('\\', '/')
                            url = re.sub(r'/+', '/', url)
                            url = re.sub(r'["\'\[\]]', '', url)
                            url = f'http://fhdrikxsirudr.fwh.is/{url.lstrip("/")}'
                    elif url.startswith('/'):
                        url = f'http://fhdrikxsirudr.fwh.is{url}'
                        url = re.sub(r'/+', '/', url)
                    elif url.startswith('//'):
                        url = f'http:{url}'
                        url = re.sub(r'/+', '/', url)
                    elif not url.startswith('http'):
                        # Assume it's a relative path
                        url = url.replace('\\', '/')
                        url = re.sub(r'/+', '/', url)
                        url = re.sub(r'["\'\[\]]', '', url)
                        url = f'http://fhdrikxsirudr.fwh.is/{url.lstrip("/")}'
                    else:
                        # Already has http, just clean it
                        url = re.sub(r'["\'\[\]]', '', url)
                        url = re.sub(r'/+', '/', url)
                    
                    # Accept ALL URLs regardless of extension
                    if url and url not in seen_urls:
                        # Accept the URL regardless of extension
                        seen_urls.add(url)
                        all_urls.append(url)
                    elif url in seen_urls:
                        skipped_count += 1
                    else:
                        skipped_count += 1
                        print(f"DEBUG: Skipped invalid URL: {original_url} -> {url}")
        
        total = len(all_urls)
        expected_total = 9684  # From your metadata
        
        print(f"\n📊 STATISTICS:")
        print(f"   - Total items in JSON array: {len(urls_list)}")
        print(f"   - Metadata entries skipped: {metadata_count}")
        print(f"   - URLs extracted: {total}")
        print(f"   - Expected URLs: {expected_total}")
        print(f"   - Skipped/duplicates: {skipped_count}")
        
        if total != expected_total:
            print(f"\n⚠️ WARNING: Extracted {total} URLs but expected {expected_total}")
            print(f"   Difference: {expected_total - total} URLs missing")
            
            # Debug: Check what's in the first few URLs to see the pattern
            print("\n🔍 First 5 raw URLs from JSON:")
            for i, item in enumerate(urls_list[:5]):
                if isinstance(item, str) and not item.startswith('total_urls'):
                    print(f"   {i+1}. {item}")
        
        print(f"\n✅ Final: {total} unique JPG URL(s) extracted from all_urls column")
        
        # Create output in EXACT same format as fetch_urls
        output_data = {
            "source_url": "http://fhdrikxsirudr.fwh.is/loadimagesurl.php?i=1",
            "current_url": "http://fhdrikxsirudr.fwh.is/loadimagesurl.php?i=1",
            "page_title": "JPGs Vault Database Export",
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z",
            "total_jpgs": total,
            "expected_total": expected_total,
            "jpg_urls": all_urls,
            "debug": {
                "summary_cards": {"Unique URLs Saved": str(total)},
                "found_via_js": total,
                "source": "jpgsvault_table.all_urls",
                "records_processed": len(rows),
                "json_array_size": len(urls_list),
                "metadata_skipped": metadata_count
            }
        }
        
        # Save to the same output file as fetch_urls uses
        OUTPUT_FILE = r"C:\xampp\htdocs\serenum-csv\files\fetchedjpgsurl.json"
        
        # --- NEW: Clear existing data before saving ---
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        # Check if file exists and delete it
        if os.path.exists(OUTPUT_FILE):
            try:
                os.remove(OUTPUT_FILE)
                print(f"🗑️ Removed existing file: {OUTPUT_FILE}")
            except Exception as e:
                print(f"⚠️ Warning: Could not delete existing file: {e}")
        
        # Save new data
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 New data saved to {OUTPUT_FILE}")
        
        if all_urls:
            print(f"\n📋 Sample URLs (first 10):")
            for url in all_urls[:10]:
                print(f"  {url}")
        
        return all_urls
        
    except Exception as e:
        print(f"CRITICAL ERROR in fetch process: {e}")
        import traceback
        traceback.print_exc()
        return []                                                                              

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
) -> Tuple[bool, str, str]: 
    """
    Downloads a single image, verifies it with Pillow and returns:
        (is_valid: bool, debug_info: str, saved_path: str)

    The **original URL** is returned unchanged so the caller can store it.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    # ------------------------------------------------- request
    try:
        resp = requests.get(
            url, headers=headers, timeout=timeout,
            allow_redirects=True, stream=True
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}", ""
    except Exception as e:
        return False, f"Request error: {e}", ""

    # ------------------------------------------------- temp_dir required
    if not temp_dir:
        return False, "temp_dir required", ""

    os.makedirs(temp_dir, exist_ok=True)

    # ------------------------------------------------- build a safe filename
    base_name = os.path.basename(url.split("?")[0])
    if not base_name.lower().endswith((".jpg", ".jpeg", ".png")):
        base_name += ".jpg"

    temp_path = os.path.join(temp_dir, base_name)
    root, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(temp_path):
        temp_path = os.path.join(temp_dir, f"{root}_{counter}{ext}")
        counter += 1

    # ------------------------------------------------- stream to disk
    try:
        with open(temp_path, "wb") as f:
            resp.raw.decode_content = True
            shutil.copyfileobj(resp.raw, f)
    except Exception as e:
        return False, f"Save failed: {e}", ""

    # ------------------------------------------------- Pillow verify + load
    try:
        with Image.open(temp_path) as img:
            img.verify()
        with Image.open(temp_path) as img:
            img.load()
    except Exception as e:
        try:
            os.remove(temp_path)
        finally:
            pass
        return False, f"Corrupted: {e}", ""

    # ------------------------------------------------- move to final_dir (optional)
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
            finally:
                pass
            return False, f"Move failed: {e}", ""

    return True, f"OK → {os.path.getsize(final_path)} bytes", final_path

def markjpgs_old():

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
        except Exception:
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
    # Define both HTTP and HTTPS base paths for flexible matching
    http_base = f"http://fhdrikxsirudr.fwh.is/jpgs/{author}/"
    https_base = f"https://fhdrikxsirudr.fwh.is/jpgs/{author}/"
    
    if processjpgfrom == 'uploadedjpgs':
        http_base = f"http://fhdrikxsirudr.fwh.is/jpgs/{author}_uploaded/"
        https_base = f"https://fhdrikxsirudr.fwh.is/jpgs/{author}_uploaded/"

    jpgfolders_dir = fr'C:\xampp\htdocs\serenum-csv\files\jpgfolders\{author}'
    next_json_dir    = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    next_json_path  = os.path.join(next_json_dir, 'next_jpgcard.json')
    download_dir    = fr'C:\xampp\htdocs\serenum-csv\files\downloaded\{author}'
    uploaded_json_path = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}\uploadedjpgs.json'

    for d in [jpgfolders_dir, next_json_dir, download_dir]:
        os.makedirs(d, exist_ok=True)

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

    # Debug: Show a few sample URLs to see what we're working with
    print("\nSample fetched URLs (first 5):")
    for i, url in enumerate(list(all_fetched_urls)[:5]):
        print(f"  {i+1}: {url}")

    # Filter to relevant image URLs only - handle both HTTP and HTTPS
    all_image_urls = []
    
    for url in all_fetched_urls:
        url_lower = url.lower()
        
        # Check if it's a valid image file
        if not url_lower.endswith(('.jpg', '.jpeg', '.png')):
            continue
            
        # Check if it matches either HTTP or HTTPS base path
        # Using 'in' to check if the path pattern exists in the URL
        path_pattern = f"/jpgs/{author}/"
        if processjpgfrom == 'uploadedjpgs':
            path_pattern = f"/jpgs/{author}_uploaded/"
        
        if path_pattern in url:
            all_image_urls.append(url)
            continue
            
        # Also check for alternative patterns (sometimes the URL structure might vary)
        alt_pattern = f"jpgs/{author}/"
        if processjpgfrom == 'uploadedjpgs':
            alt_pattern = f"jpgs/{author}_uploaded/"
            
        if alt_pattern in url:
            all_image_urls.append(url)

    # Remove duplicates while preserving order
    seen = set()
    unique_image_urls = []
    for url in all_image_urls:
        if url not in seen:
            seen.add(url)
            unique_image_urls.append(url)

    print(f"\nFound {len(unique_image_urls)} candidate JPG/PNG URLs for author '{author}' in folder '{processjpgfrom}'")

    if len(unique_image_urls) == 0:
        print("No candidate URLs found. Abort.")
        print("\nDebug Info:")
        print(f"  Author: {author}")
        print(f"  Process from: {processjpgfrom}")
        print(f"  Expected path pattern: /jpgs/{author}/")
        print("\nAll fetched URLs (first 10):")
        for i, url in enumerate(list(all_fetched_urls)[:10]):
            print(f"  {i+1}: {url}")
        return

    # ------------------------------------------------------------------ #
    # 4. Load uploadedjpgs.json → SKIP ALREADY ARCHIVED URLs
    # ------------------------------------------------------------------ #
    uploaded_urls = set()
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw = data.get("uploaded_jpgs", [])
            
            if isinstance(raw, str):
                items = raw.strip().split(',')
            elif isinstance(raw, list):
                items = raw
            else:
                items = []

            for u in items:
                if isinstance(u, str):
                    # Normalize uploaded URLs to handle both HTTP and HTTPS
                    url = u.strip()
                    uploaded_urls.add(url)
                    # Also add the alternative protocol version
                    if url.startswith('http://'):
                        uploaded_urls.add('https://' + url[7:])
                    elif url.startswith('https://'):
                        uploaded_urls.add('http://' + url[8:])
            
            print(f"Loaded {len(uploaded_urls)} already-uploaded URLs → will skip them")
        except Exception as e:
            print(f"Warning: Could not read uploadedjpgs.json: {e}")

    # ------------------------------------------------------------------ #
    # 5. Load existing next_jpgcard.json (if any)
    # ------------------------------------------------------------------ #
    next_urls_set = set()  # Changed to set for faster lookup
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_next_urls = data.get("next_jpgcard", [])
            
            # Normalize URLs for comparison (handle both protocols)
            for url in existing_next_urls:
                next_urls_set.add(url)
                # Also add the alternative protocol version
                if url.startswith('http://'):
                    next_urls_set.add('https://' + url[7:])
                elif url.startswith('https://'):
                    next_urls_set.add('http://' + url[8:])
            
            print(f"Loaded {len(existing_next_urls)} URL(s) from next_jpgcard.json")
        except Exception as e:
            print(f"Corrupted next_jpgcard.json → {e}. Will rebuild.")
            next_urls_set = set()

    # ------------------------------------------------------------------ #
    # 6. SKIP URLs that are in uploaded OR next_jpgcard
    # ------------------------------------------------------------------ #
    original_count = len(unique_image_urls)
    candidate_urls = []
    
    for url in unique_image_urls:
        # Check if URL exists in uploaded_urls or next_urls_set
        url_http = url.replace('https://', 'http://') if url.startswith('https://') else url
        url_https = url.replace('http://', 'https://') if url.startswith('http://') else url
        
        # Skip if in either uploaded or next_jpgcard
        if (url not in uploaded_urls and url_http not in uploaded_urls and url_https not in uploaded_urls and
            url not in next_urls_set and url_http not in next_urls_set and url_https not in next_urls_set):
            candidate_urls.append(url)
    
    skipped_uploaded = sum(1 for url in unique_image_urls if url in uploaded_urls or 
                           (url.replace('https://', 'http://') if url.startswith('https://') else url) in uploaded_urls or
                           (url.replace('http://', 'https://') if url.startswith('http://') else url) in uploaded_urls)
    
    skipped_next = sum(1 for url in unique_image_urls if url in next_urls_set or 
                      (url.replace('https://', 'http://') if url.startswith('https://') else url) in next_urls_set or
                      (url.replace('http://', 'https://') if url.startswith('http://') else url) in next_urls_set)
    
    print(f"\nAfter deduplication: {len(candidate_urls)} new URLs left")
    print(f"  - Skipped (uploaded): {skipped_uploaded}")
    print(f"  - Skipped (in next_jpgcard): {skipped_next}")

    if len(candidate_urls) < cardamount:
        print(f"Only {len(candidate_urls)} NEW URLs available, need {cardamount}. Abort.")
        return

    # ------------------------------------------------------------------ #
    # 7. Count files in jpgfolders
    # ------------------------------------------------------------------ #
    image_exts = ('.jpg', '.jpeg', '.png')
    existing_files = [
        f for f in os.listdir(jpgfolders_dir)
        if f.lower().endswith(image_exts)
    ]
    file_count = len(existing_files)
    print(f"Found {file_count} image(s) in jpgfolders")

    # ------------------------------------------------------------------ #
    # 8. VALIDATION - Check if existing next_jpgcard.json matches files
    # ------------------------------------------------------------------ #
    def filename_from_url(url: str) -> str:
        return os.path.basename(url.split("?")[0])

    # Get current next_urls (original, not normalized)
    current_next_urls = []
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_next_urls = data.get("next_jpgcard", [])
        except Exception:
            current_next_urls = []

    url_filenames    = {filename_from_url(u) for u in current_next_urls}
    file_names       = set(existing_files)

    files_match_urls = file_names == url_filenames
    url_count_ok     = len(current_next_urls) == cardamount
    file_count_ok    = file_count == cardamount

    print("\nVALIDATION CHECK:")
    print(f"  • Required count         : {cardamount}")
    print(f"  • Files in folder        : {file_count}")
    print(f"  • URLs in JSON           : {len(current_next_urls)}")
    print(f"  • 1:1 filename match     : {'YES' if files_match_urls else 'NO'}")

    # ------------------------------------------------------------------ #
    # 9. DECISION – perfect sync or wipe & rebuild
    # ------------------------------------------------------------------ #
    if file_count_ok and url_count_ok and files_match_urls:
        print("\nPERFECT MATCH – skipping download.")
        return
    else:
        reasons = []
        if not file_count_ok:    reasons.append(f"File count ({file_count} ≠ {cardamount})")
        if not url_count_ok:     reasons.append(f"URL count ({len(current_next_urls)} ≠ {cardamount})")
        if not files_match_urls: reasons.append("Filename mismatch")
        print("\nMISMATCH DETECTED:")
        for r in reasons: print(f"  → {r}")

        # ---- wipe everything ------------------------------------------------
        print("Wiping jpgfolders and reset next_jpgcard.json...")
        for f in existing_files:
            try:
                os.remove(os.path.join(jpgfolders_dir, f))
            except Exception: pass

        for f in os.listdir(download_dir):
            p = os.path.join(download_dir, f)
            if os.path.isfile(p):
                try: os.remove(p)
                except Exception: pass

        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump({"next_jpgcard": []}, f, indent=4, ensure_ascii=False)
        print("  [RESET] next_jpgcard.json")
        
        print(f"\nREDOWNLOADING EXACTLY {cardamount} **NEW** VALID IMAGES...\n")

    # ------------------------------------------------------------------ #
    # 10. DOWNLOAD LOOP – COMMENTED OUT (DRY RUN / SAFE MODE)
    # ------------------------------------------------------------------ #
    """
    downloaded = 0
    valid_urls = []
    saved_paths = []

    for url in candidate_urls:
        if downloaded >= cardamount:
            break

        print(f"[{downloaded + 1}/{cardamount}] Downloading: {url}")
        ok, debug, saved_path = check_single_url(
            url,
            temp_dir=download_dir,
            final_dir=download_dir
        )

        if ok:
            valid_urls.append(url)
            saved_paths.append(saved_path)
            downloaded += 1
            print(f"  [SUCCESS] {debug}")
        else:
            print(f"  [FAILED] {debug}")

    if downloaded != cardamount:
        print(f"\nFAILED: Only {downloaded}/{cardamount} NEW images succeeded.")
        return
    """
    # ----- DOWNLOAD SECTION IS DISABLED -----
    print(f"[DRY RUN] Would download {cardamount} new images here (download code is commented out).")
    # Simulate success for the rest of the script
    downloaded = cardamount
    valid_urls = candidate_urls[:cardamount]
    saved_paths = [os.path.join(download_dir, filename_from_url(u)) for u in valid_urls]

    # ------------------------------------------------------------------ #
    # 11. COPY TO jpgfolders (preserving original filenames)
    # ------------------------------------------------------------------ #
    for src_path, orig_url in zip(saved_paths, valid_urls):
        dest_name = filename_from_url(orig_url)
        dest_path = os.path.join(jpgfolders_dir, dest_name)

        root, ext = os.path.splitext(dest_name)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(jpgfolders_dir, f"{root}_{counter}{ext}")
            counter += 1

        # Create placeholder if file doesn't exist
        if not os.path.exists(src_path):
            print(f"  [PLACEHOLDER] Creating dummy file for {dest_name}")
            with open(src_path, 'w') as dummy:
                dummy.write("placeholder")
        
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            print(f"  [COPY FAILED] {dest_name} → {e}")

    # ------------------------------------------------------------------ #
    # 12. WRITE next_jpgcard.json – only the original URLs
    # ------------------------------------------------------------------ #
    try:
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump(
                {"next_jpgcard": valid_urls},
                f,
                indent=4,
                ensure_ascii=False
            )
        print(f"\nSUCCESS: Saved {len(valid_urls)} placeholder URLs to next_jpgcard.json (dry run)")
    except Exception as e:
        print(f"Failed to save JSON: {e}")
        return

    # ------------------------------------------------------------------ #
    # 13. FINAL REPORT
    # ------------------------------------------------------------------ #
    print("\n" + "="*80)
    print("DRY RUN COMPLETE – NO REAL DOWNLOADS PERFORMED")
    print("="*80)
    print(f"Author             : {author}")
    print(f"Required           : {cardamount}")
    print(f"Skipped (uploaded) : {skipped_uploaded}")
    print(f"Skipped (next)     : {skipped_next}")
    print(f"Simulated Download : {downloaded} (no actual files downloaded)")
    print(f"jpgfolders         : {jpgfolders_dir}")
    print(f"Download Dir       : {download_dir}")
    print(f"JSON Path          : {next_json_path}")
    print("Ready for testing – real download loop is commented out.")
    print("="*80)

def markjpgs():

    # ------------------------------------------------------------------ #
    # 1. Load config
    # ------------------------------------------------------------------ #
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'
    FETCHED_JSON_PATH = r'C:\xampp\htdocs\serenum-csv\files\fetchedjpgsurl.json'

    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        author = config.get('author', '').strip()
        author_lower = author.lower()  # Store lowercase version for comparisons
        processjpgfrom = config.get('processjpgfrom', 'freshjpgs').strip().lower()
        if not author:
            print("Error: 'author' missing in config.")
            return

        try:
            cardamount = max(1, int(config.get('cardamount', 1)))
        except Exception:
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
    # Define both HTTP and HTTPS base paths for flexible matching
    http_base = f"http://fhdrikxsirudr.fwh.is/jpgs/{author}/"
    https_base = f"https://fhdrikxsirudr.fwh.is/jpgs/{author}/"
    
    if processjpgfrom == 'uploadedjpgs':
        http_base = f"http://fhdrikxsirudr.fwh.is/jpgs/{author}_uploaded/"
        https_base = f"https://fhdrikxsirudr.fwh.is/jpgs/{author}_uploaded/"

    jpgfolders_dir = fr'C:\xampp\htdocs\serenum-csv\files\jpgfolders\{author}'
    next_json_dir    = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    next_json_path  = os.path.join(next_json_dir, 'next_jpgcard.json')
    download_dir    = fr'C:\xampp\htdocs\serenum-csv\files\downloaded\{author}'
    uploaded_json_path = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}\uploadedjpgs.json'

    for d in [jpgfolders_dir, next_json_dir, download_dir]:
        os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 3. Load fetched URLs (CASE-INSENSITIVE FILTERING)
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

    # Debug: Show a few sample URLs to see what we're working with
    print("\nSample fetched URLs (first 5):")
    for i, url in enumerate(list(all_fetched_urls)[:5]):
        print(f"  {i+1}: {url}")

    # Filter to relevant image URLs only - FULL CASE-INSENSITIVE matching
    all_image_urls = []
    
    for url in all_fetched_urls:
        url_lower = url.lower()
        
        # Check if it's a valid image file
        if not url_lower.endswith(('.jpg', '.jpeg', '.png')):
            continue
            
        # CASE-INSENSITIVE path pattern matching using lowercase author
        path_pattern = f"/jpgs/{author_lower}/"
        if processjpgfrom == 'uploadedjpgs':
            path_pattern = f"/jpgs/{author_lower}_uploaded/"
        
        # Check if lowercase URL contains lowercase path pattern
        if path_pattern in url_lower:
            all_image_urls.append(url)
            continue
            
        # Also check for alternative patterns (case-insensitive)
        alt_pattern = f"jpgs/{author_lower}/"
        if processjpgfrom == 'uploadedjpgs':
            alt_pattern = f"jpgs/{author_lower}_uploaded/"
            
        if alt_pattern in url_lower:
            all_image_urls.append(url)
            continue
        
        # Final fallback: check if author name appears anywhere in URL (case-insensitive)
        if author_lower in url_lower and 'jpgs' in url_lower:
            all_image_urls.append(url)

    # Remove duplicates while preserving order
    seen = set()
    unique_image_urls = []
    for url in all_image_urls:
        if url not in seen:
            seen.add(url)
            unique_image_urls.append(url)

    print(f"\nFound {len(unique_image_urls)} candidate JPG/PNG URLs for author '{author}' in folder '{processjpgfrom}'")

    if len(unique_image_urls) == 0:
        print("No candidate URLs found. Abort.")
        print("\nDebug Info:")
        print(f"  Author: {author}")
        print(f"  Author (lowercase for matching): {author_lower}")
        print(f"  Process from: {processjpgfrom}")
        print(f"  Expected path pattern (case-insensitive): /jpgs/{author_lower}/")
        print("\nAll fetched URLs (first 10):")
        for i, url in enumerate(list(all_fetched_urls)[:10]):
            print(f"  {i+1}: {url}")
            print(f"      Lowercase: {url.lower()}")
            print(f"      Contains pattern: {path_pattern in url.lower() if 'path_pattern' in locals() else 'N/A'}")
        return

    # ------------------------------------------------------------------ #
    # 4. Load uploadedjpgs.json → SKIP ALREADY ARCHIVED URLs (CASE-INSENSITIVE)
    # ------------------------------------------------------------------ #
    uploaded_urls_norm = set()  # Store normalized (lowercase) versions
    uploaded_urls_original = set()  # Store original versions
    
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw = data.get("uploaded_jpgs", [])
            
            if isinstance(raw, str):
                items = raw.strip().split(',')
            elif isinstance(raw, list):
                items = raw
            else:
                items = []

            for u in items:
                if isinstance(u, str):
                    url = u.strip()
                    uploaded_urls_original.add(url)
                    uploaded_urls_norm.add(url.lower())
                    # Also add the alternative protocol version (normalized)
                    if url.startswith('http://'):
                        uploaded_urls_norm.add(('https://' + url[7:]).lower())
                    elif url.startswith('https://'):
                        uploaded_urls_norm.add(('http://' + url[8:]).lower())
            
            print(f"Loaded {len(uploaded_urls_original)} already-uploaded URLs → will skip them (case-insensitive)")
        except Exception as e:
            print(f"Warning: Could not read uploadedjpgs.json: {e}")

    # ------------------------------------------------------------------ #
    # 5. Load existing next_jpgcard.json (CASE-INSENSITIVE)
    # ------------------------------------------------------------------ #
    next_urls_norm = set()  # Store normalized (lowercase) versions
    next_urls_original = set()  # Store original versions
    
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_next_urls = data.get("next_jpgcard", [])
            
            # Normalize URLs for comparison (handle both protocols and case)
            for url in existing_next_urls:
                next_urls_original.add(url)
                next_urls_norm.add(url.lower())
                # Also add the alternative protocol version (normalized)
                if url.startswith('http://'):
                    next_urls_norm.add(('https://' + url[7:]).lower())
                elif url.startswith('https://'):
                    next_urls_norm.add(('http://' + url[8:]).lower())
            
            print(f"Loaded {len(existing_next_urls)} URL(s) from next_jpgcard.json")
        except Exception as e:
            print(f"Corrupted next_jpgcard.json → {e}. Will rebuild.")
            next_urls_norm = set()
            next_urls_original = set()

    # ------------------------------------------------------------------ #
    # 6. SKIP URLs that are in uploaded OR next_jpgcard (CASE-INSENSITIVE)
    # ------------------------------------------------------------------ #
    original_count = len(unique_image_urls)
    candidate_urls = []
    
    for url in unique_image_urls:
        url_lower = url.lower()
        
        # Normalize HTTP/HTTPS for comparison
        url_http_lower = url_lower.replace('https://', 'http://')
        url_https_lower = url_lower.replace('http://', 'https://')
        
        # Check against normalized (lowercase) sets
        if (url_lower not in uploaded_urls_norm and 
            url_http_lower not in uploaded_urls_norm and 
            url_https_lower not in uploaded_urls_norm and
            url_lower not in next_urls_norm and 
            url_http_lower not in next_urls_norm and 
            url_https_lower not in next_urls_norm):
            candidate_urls.append(url)
    
    # Calculate skipped counts for reporting
    skipped_uploaded = 0
    skipped_next = 0
    
    for url in unique_image_urls:
        url_lower = url.lower()
        url_http_lower = url_lower.replace('https://', 'http://')
        url_https_lower = url_lower.replace('http://', 'https://')
        
        if (url_lower in uploaded_urls_norm or 
            url_http_lower in uploaded_urls_norm or 
            url_https_lower in uploaded_urls_norm):
            skipped_uploaded += 1
        
        if (url_lower in next_urls_norm or 
            url_http_lower in next_urls_norm or 
            url_https_lower in next_urls_norm):
            skipped_next += 1
    
    print(f"\nAfter deduplication: {len(candidate_urls)} new URLs left")
    print(f"  - Skipped (uploaded): {skipped_uploaded}")
    print(f"  - Skipped (in next_jpgcard): {skipped_next}")

    if len(candidate_urls) < cardamount:
        print(f"Only {len(candidate_urls)} NEW URLs available, need {cardamount}. Abort.")
        return

    # ------------------------------------------------------------------ #
    # 7. Count files in jpgfolders
    # ------------------------------------------------------------------ #
    image_exts = ('.jpg', '.jpeg', '.png')
    existing_files = [
        f for f in os.listdir(jpgfolders_dir)
        if f.lower().endswith(image_exts)
    ]
    file_count = len(existing_files)
    print(f"Found {file_count} image(s) in jpgfolders")

    # ------------------------------------------------------------------ #
    # 8. VALIDATION - Check if existing next_jpgcard.json matches files (CASE-INSENSITIVE)
    # ------------------------------------------------------------------ #
    def filename_from_url(url: str) -> str:
        return os.path.basename(url.split("?")[0])

    # Get current next_urls (original, not normalized)
    current_next_urls = []
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_next_urls = data.get("next_jpgcard", [])
        except Exception:
            current_next_urls = []

    # CASE-INSENSITIVE filename matching
    url_filenames_lower = {filename_from_url(u).lower() for u in current_next_urls}
    file_names_lower = {f.lower() for f in existing_files}

    files_match_urls = file_names_lower == url_filenames_lower
    url_count_ok     = len(current_next_urls) == cardamount
    file_count_ok    = file_count == cardamount

    print("\nVALIDATION CHECK:")
    print(f"  • Required count         : {cardamount}")
    print(f"  • Files in folder        : {file_count}")
    print(f"  • URLs in JSON           : {len(current_next_urls)}")
    print(f"  • 1:1 filename match (case-insensitive): {'YES' if files_match_urls else 'NO'}")

    # ------------------------------------------------------------------ #
    # 9. DECISION – perfect sync or wipe & rebuild
    # ------------------------------------------------------------------ #
    if file_count_ok and url_count_ok and files_match_urls:
        print("\nPERFECT MATCH – skipping download.")
        return
    else:
        reasons = []
        if not file_count_ok:    reasons.append(f"File count ({file_count} ≠ {cardamount})")
        if not url_count_ok:     reasons.append(f"URL count ({len(current_next_urls)} ≠ {cardamount})")
        if not files_match_urls: reasons.append("Filename mismatch (case-insensitive check failed)")
        print("\nMISMATCH DETECTED:")
        for r in reasons: print(f"  → {r}")

        # ---- wipe everything ------------------------------------------------
        print("Wiping jpgfolders and reset next_jpgcard.json...")
        for f in existing_files:
            try:
                os.remove(os.path.join(jpgfolders_dir, f))
            except Exception: pass

        for f in os.listdir(download_dir):
            p = os.path.join(download_dir, f)
            if os.path.isfile(p):
                try: os.remove(p)
                except Exception: pass

        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump({"next_jpgcard": []}, f, indent=4, ensure_ascii=False)
        print("  [RESET] next_jpgcard.json")
        
        print(f"\nREDOWNLOADING EXACTLY {cardamount} **NEW** VALID IMAGES...\n")

    # ------------------------------------------------------------------ #
    # 10. DOWNLOAD LOOP – COMMENTED OUT (DRY RUN / SAFE MODE)
    # ------------------------------------------------------------------ #
    """
    downloaded = 0
    valid_urls = []
    saved_paths = []

    for url in candidate_urls:
        if downloaded >= cardamount:
            break

        print(f"[{downloaded + 1}/{cardamount}] Downloading: {url}")
        ok, debug, saved_path = check_single_url(
            url,
            temp_dir=download_dir,
            final_dir=download_dir
        )

        if ok:
            valid_urls.append(url)
            saved_paths.append(saved_path)
            downloaded += 1
            print(f"  [SUCCESS] {debug}")
        else:
            print(f"  [FAILED] {debug}")

    if downloaded != cardamount:
        print(f"\nFAILED: Only {downloaded}/{cardamount} NEW images succeeded.")
        return
    """
    # ----- DOWNLOAD SECTION IS DISABLED -----
    print(f"[DRY RUN] Would download {cardamount} new images here (download code is commented out).")
    # Simulate success for the rest of the script
    downloaded = cardamount
    valid_urls = candidate_urls[:cardamount]
    saved_paths = [os.path.join(download_dir, filename_from_url(u)) for u in valid_urls]

    # ------------------------------------------------------------------ #
    # 11. COPY TO jpgfolders (preserving original filenames)
    # ------------------------------------------------------------------ #
    for src_path, orig_url in zip(saved_paths, valid_urls):
        dest_name = filename_from_url(orig_url)
        dest_path = os.path.join(jpgfolders_dir, dest_name)

        root, ext = os.path.splitext(dest_name)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(jpgfolders_dir, f"{root}_{counter}{ext}")
            counter += 1

        # Create placeholder if file doesn't exist
        if not os.path.exists(src_path):
            print(f"  [PLACEHOLDER] Creating dummy file for {dest_name}")
            with open(src_path, 'w') as dummy:
                dummy.write("placeholder")
        
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            print(f"  [COPY FAILED] {dest_name} → {e}")

    # ------------------------------------------------------------------ #
    # 12. UNCONDITIONALLY CLEANUP AND WRITE next_jpgcard.json
    # ------------------------------------------------------------------ #
    # FIRST: Unconditionally clear/cleanup the next_jpgcard.json before writing
    print("\n[UNCONDITIONAL CLEANUP] Clearing next_jpgcard.json before writing new data...")
    
    # Backup existing data if needed (optional - but we're clearing unconditionally)
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_count = len(old_data.get("next_jpgcard", []))
                if old_count > 0:
                    print(f"  - Removing old data with {old_count} URL(s)")
        except Exception:
            pass
    
    # Unconditionally reset/clear the JSON file
    with open(next_json_path, 'w', encoding='utf-8') as f:
        json.dump({"next_jpgcard": []}, f, indent=4, ensure_ascii=False)
    print("  - Cleared next_jpgcard.json to empty array []")
    
    # NOW write the new valid URLs
    try:
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump(
                {"next_jpgcard": valid_urls},
                f,
                indent=4,
                ensure_ascii=False
            )
        print(f"\nSUCCESS: Saved {len(valid_urls)} new URLs to next_jpgcard.json (existing data was unconditionally cleared first)")
    except Exception as e:
        print(f"Failed to save JSON: {e}")
        return

    # ------------------------------------------------------------------ #
    # 13. FINAL REPORT
    # ------------------------------------------------------------------ #
    print("\n" + "="*80)
    print("DRY RUN COMPLETE – NO REAL DOWNLOADS PERFORMED")
    print("="*80)
    print(f"Author             : {author}")
    print(f"Required           : {cardamount}")
    print(f"Skipped (uploaded) : {skipped_uploaded}")
    print(f"Skipped (next)     : {skipped_next}")
    print(f"Simulated Download : {downloaded} (no actual files downloaded)")
    print(f"jpgfolders         : {jpgfolders_dir}")
    print(f"Download Dir       : {download_dir}")
    print(f"JSON Path          : {next_json_path}")
    print("Ready for testing – real download loop is commented out.")
    print("="*80)
    
def cleanup_wrong_author_urls():
    """Remove URLs from next_jpgcard.json that don't belong to the current author"""
    import os
    import json
    
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'
    
    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        author = config.get('author', '').strip()
        author_lower = author.lower()
        
        # Path to next_jpgcard.json
        next_json_path = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}\next_jpgcard.json'
        
        if not os.path.exists(next_json_path):
            print(f"No next_jpgcard.json found for {author}")
            return
        
        with open(next_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            urls = data.get("next_jpgcard", [])
        
        original_count = len(urls)
        
        # Filter URLs
        filtered_urls = []
        for url in urls:
            url_lower = url.lower()
            expected_path = f"/jpgs/{author_lower}/"
            if expected_path in url_lower:
                filtered_urls.append(url)
            else:
                print(f"Removing wrong author URL: {url}")
        
        if len(filtered_urls) != original_count:
            with open(next_json_path, 'w', encoding='utf-8') as f:
                json.dump({"next_jpgcard": filtered_urls}, f, indent=4, ensure_ascii=False)
            print(f"Cleaned next_jpgcard.json: removed {original_count - len(filtered_urls)} wrong URLs")
        else:
            print("All URLs belong to correct author")
            
    except Exception as e:
        print(f"Cleanup error: {e}")


def update_calendar():
    """Update the calendar and write to JSON, generating 12 months starting from current month."""

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
    
    # Generate 12 months starting from current month
    calendars = []
    year = current_year
    month = current_month

    for i in range(12):
        # Handle year/month rollover
        if month > 12:
            month = 1
            year += 1

        month_name = calendar.month_name[month]
        month_calendar = calendar.monthcalendar(year, month)

        days_list = []
        for week_idx, week in enumerate(month_calendar):
            # Only include weeks that have at least one valid day (not all zeros)
            if any(day != 0 for day in week):
                week_data = {
                    "week": week_idx + 1,
                    "days": []
                }
                for day in week:
                    if day == 0:
                        week_data["days"].append({"day": None})
                        continue

                    date_str = f"{day:02d}/{month:02d}/{year}"
                    is_today = (year == current_year and month == current_month and day == current_day)
                    is_past_day = (year < current_year or 
                                 (year == current_year and month < current_month) or 
                                 (year == current_year and month == current_month and day < current_day))

                    time_12hour_display = current_time_12hour if is_today else "00:00 pm"
                    time_24hour_display = current_time_24hour if is_today else "00:00"

                    # Determine time_ahead list
                    if is_today:
                        time_ahead = time_ahead_today
                    elif is_past_day:
                        time_ahead = []
                    else:
                        # Future day: all slots are available
                        time_ahead = [
                            {
                                "id": f"{day:02d}_{t['24hours'].replace(':', '')}",
                                "12hours": t["12hours"],
                                "24hours": t["24hours"],
                                "minutes_distance": int((
                                    datetime.strptime(f"{day:02d}/{month:02d}/{year} {t['24hours']}", "%d/%m/%Y %H:%M")
                                    - current_datetime
                                ).total_seconds() / 60),
                                "consideration": f"passed {t['12hours']}"
                            } for t in sorted_timeorders
                        ]

                    day_data = {
                        "day": {
                            "date": date_str,
                            "time_12hour": time_12hour_display,
                            "time_24hour": time_24hour_display,
                            "time_ahead": time_ahead
                        }
                    }
                    week_data["days"].append(day_data)

                days_list.append(week_data)

        calendars.append({
            "year": year,
            "month": month_name,
            "days": days_list
        })

        month += 1  # Move to next month

    # Final calendar data structure
    calendar_data = {
        "calendars": calendars
    }

    # Define output path with author, group_types, and type
    output_path = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}\\{type_value}calendar.json"
    print(f"Writing 12-month calendar data to {output_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write to JSON file
    with open(output_path, 'w') as f:
        json.dump(calendar_data, f, indent=4)
    print(f"12-month calendar data successfully written to {output_path}")
    
    # Call schedule_time
    update_timeschedule()

def update_timeschedule():
    """REBUILD next_schedule starting AFTER schedule_date — every run obeys schedule_date 100%.
    Now generates exactly as many slots as needed (up to cardamount / images available)."""
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
    
    author = cfg['author']
    type_value = cfg['type']
    group_types = cfg['group_types']
    cardamount = int(cfg.get('cardamount', 1))
    schedule_date_str = cfg.get('schedule_date', '').strip()
    
    print(f"Config loaded: author={author}, type={type_value}, cardamount={cardamount}")
    print(f"schedule_date (starting point) = '{schedule_date_str}'")
    
    # --------------------------------------------------------------------- #
    # 2. Parse schedule_date → strict starting point
    # --------------------------------------------------------------------- #
    start_dt = None
    if schedule_date_str:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(schedule_date_str.split('.')[0].strip(), fmt)
                if ' ' not in schedule_date_str:
                    dt = dt.replace(hour=0, minute=0)
                start_dt = dt
                break
            except ValueError:
                continue
    
    if start_dt is None:
        start_dt = datetime.now()
        print("Invalid or missing schedule_date → fallback to now")
    
    print(f"Starting schedule generation strictly AFTER: {start_dt.strftime('%d/%m/%Y %H:%M')}")
    NOW = datetime.now()
    print(f"Current time: {NOW.strftime('%d/%m/%Y %H:%M')}")
    
    # --------------------------------------------------------------------- #
    # 3. Load timeorders (your posting times per day)
    # --------------------------------------------------------------------- #
    timeorders_path = r"C:\xampp\htdocs\serenum-csv\timeorders.json"
    try:
        with open(timeorders_path, 'r', encoding='utf-8') as f:
            timeorders_data = json.load(f)
    except Exception as e:
        print(f"Timeorders error: {e}")
        return
    
    if type_value not in timeorders_data:
        print(f"Type '{type_value}' not found in timeorders.json")
        return
    
    timeorders = sorted(timeorders_data[type_value], key=lambda x: x["24hours"])
    print(f"Loaded {len(timeorders)} posting times per day for '{type_value}'")
    
    # --------------------------------------------------------------------- #
    # 4. Paths
    # --------------------------------------------------------------------- #
    base_dir = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}"
    schedules_path = os.path.join(base_dir, f"{type_value}schedules.json")
    
    # --------------------------------------------------------------------- #
    # 5. Load existing last_schedule (preserve published ones)
    # --------------------------------------------------------------------- #
    last_schedule = []
    if os.path.exists(schedules_path):
        try:
            with open(schedules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_schedule = data.get("last_schedule", [])
            print(f"Preserved {len(last_schedule)} already-published slots")
        except Exception as e:
            print(f"Error reading existing schedules.json: {e}")
    
    # --------------------------------------------------------------------- #
    # 6. Target: schedule exactly as many as cardamount (or less if fewer images)
    #    In real usage you would pass/read the actual available images count here
    # --------------------------------------------------------------------- #
    # For now using cardamount — replace 500 with your real "Images available" value if known
    available_images = 10000000000   # ← CHANGE THIS or make it dynamic from earlier part of script
    target_slots = min(cardamount, available_images)
    print(f"Target: schedule exactly {target_slots} slots (min of cardamount and available images)")
    
    # --------------------------------------------------------------------- #
    # 7. Generate new next_schedule — keep going until we have enough
    # --------------------------------------------------------------------- #
    new_next_schedule = []
    current_day = start_dt.date()
    days_searched = 0
    SAFETY_MAX_DAYS = 100000  # very high ceiling — should never hit with reasonable numbers
    
    while len(new_next_schedule) < target_slots and days_searched < SAFETY_MAX_DAYS:
        day_str = current_day.strftime("%d/%m/%Y")
        
        for t in timeorders:
            if len(new_next_schedule) >= target_slots:
                break
                
            slot_time_24 = t["24hours"]
            try:
                slot_dt = datetime.combine(current_day, datetime.strptime(slot_time_24, "%H:%M").time())
            except:
                continue
            
            # Keep original validation rules
            if current_day == start_dt.date():
                if slot_dt <= start_dt:
                    continue
                # 50-minute buffer only applies if this is TODAY
                if current_day == NOW.date():
                    if (slot_dt - NOW).total_seconds() / 60 < 50:
                        continue
            else:
                # Future days: skip only if somehow before now (shouldn't happen)
                if slot_dt <= NOW:
                    continue
            
            # Valid slot → add it
            slot_id = f"{current_day.day:02d}_{slot_time_24.replace(':', '')}"
            new_slot = {
                "id": slot_id,
                "date": day_str,
                "time_12hour": t["12hours"],
                "time_24hour": slot_time_24
            }
            new_next_schedule.append(new_slot)
            #print(f"  Added slot {len(new_next_schedule):3d}/{target_slots}: {day_str} {slot_time_24}")
        
        current_day += timedelta(days=1)
        days_searched += 1
    
    if days_searched >= SAFETY_MAX_DAYS:
        print(f"WARNING: Safety limit reached after {SAFETY_MAX_DAYS} days — only {len(new_next_schedule)} slots created")
    
    if not new_next_schedule:
        print("No valid slots could be scheduled after the start date!")
        return
    
    print(f"Generated {len(new_next_schedule)} new future slots")
    
    # --------------------------------------------------------------------- #
    # 8. Save: keep old last_schedule + brand new next_schedule
    # --------------------------------------------------------------------- #
    output = {
        "last_schedule": last_schedule,
        "next_schedule": new_next_schedule
    }
    
    os.makedirs(os.path.dirname(schedules_path), exist_ok=True)
    with open(schedules_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    
    print(f"Saved to: {schedules_path}")
    print(f" → last_schedule: {len(last_schedule)} items")
    print(f" → next_schedule: {len(new_next_schedule)} items (target was {target_slots})")
    
    # --------------------------------------------------------------------- #
    # 9. Update schedule_date to the LAST slot in the new queue
    # --------------------------------------------------------------------- #
    if new_next_schedule:
        last_slot = new_next_schedule[-1]
        new_schedule_date = f"{last_slot['date']} {last_slot['time_24hour']}"
        try:
            new_dt = datetime.strptime(new_schedule_date, "%d/%m/%Y %H:%M")
            cfg["schedule_date"] = new_dt.strftime("%d/%m/%Y %H:%M")
            with open(pageauthors_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
            print(f"schedule_date updated to last slot: {cfg['schedule_date']}")
            randomize_next_schedule_minutes()
        except Exception as e:
            print(f"Could not update schedule_date: {e}")
    
    print("update_timeschedule() completed successfully.")   
    
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
            #print(f"  → {s}")
            print
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


def generate_final_csv_old():
    """FINAL JARVEE-COMPATIBLE CSV – UNLIMITED POSTS WITH RANDOM CAPTION REUSE + 100 PER FILE SPLIT"""
    
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
        
        print(f"Generating JARVEE-READY CSV → {author} ({group_types}) | Up to {cardamount} posts")
        
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

    base_csv_name = f"{author}_posts"
    print(f"Saving to → {csv_dir}")

    # ------------------------------------------------------------------ #
    # 3. Load & clean captions (bulletproof)
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
                if not desc:
                    continue

                desc = desc.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                desc = desc.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                desc = ' '.join(desc.split())
                desc = ''.join(ch for ch in desc if ord(ch) >= 32 or ch in '\t')
                
                captions.append(desc)
        
        if not captions:
            print("No valid captions after cleaning!")
            return
        print(f"Captions loaded & cleaned: {len(captions)} → Will be reused randomly")
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
            images = json.load(f).get("next_jpgcard", [])[:cardamount]
        if not images:
            print("No images!")
            return
        print(f"Images available: {len(images)}")
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
            schedule = json.load(f).get("next_schedule", [])[:cardamount]
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
    final_count = min(cardamount, len(images), len(schedule))
    if final_count == 0:
        print("Nothing to generate.")
        return

    print(f"\nBuilding {final_count} JARVEE-READY posts with random caption reuse...\n")

    # ------------------------------------------------------------------ #
    # 7. Build all rows with random captions
    # ------------------------------------------------------------------ #
    rows = []
    random.seed()

    for i in range(final_count):
        caption = random.choice(captions)
        img_url = images[i]
        slot = schedule[i]

        date_parts = slot['date'].split('/')
        yyyy_mm_dd = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
        post_time = f"{yyyy_mm_dd} {slot['time_24hour']}"

        rows.append({
            "Text": caption,
            "Image URL": img_url,
            "Tags": "",
            "Posting Time": post_time
        })

        card = img_url.split('/')[-1].split('?')[0]
        #print(f"{i+1:3}. {post_time} → {card}")

    # ------------------------------------------------------------------ #
    # 8. DELETE OLD CSVs + SPLIT & SAVE NEW ONES (100 per file)
    # ------------------------------------------------------------------ #
    try:
        # Delete all existing CSVs with the same base name
        for file in os.listdir(csv_dir):
            if file.startswith(base_csv_name) and file.endswith('.csv'):
                os.remove(os.path.join(csv_dir, file))
        print(f"\nOld CSVs deleted in {csv_dir}")

        CHUNK_SIZE = 100
        total_files = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE  # Ceiling division

        for idx in range(total_files):
            chunk = rows[idx * CHUNK_SIZE : (idx + 1) * CHUNK_SIZE]
            
            # File naming: first file = author_posts.csv, rest = author_posts_a.csv, _b.csv, etc.
            if idx == 0 and len(rows) <= CHUNK_SIZE:
                csv_filename = f"{base_csv_name}.csv"
            else:
                suffix = '' if idx == 0 else '_' + string.ascii_lowercase[idx - 1]
                csv_filename = f"{base_csv_name}{suffix}.csv"
            
            csv_fullpath = os.path.join(csv_dir, csv_filename)

            with open(csv_fullpath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["Text", "Image URL", "Tags", "Posting Time"],
                    quoting=csv.QUOTE_ALL,
                    lineterminator='\n'
                )
                writer.writeheader()
                writer.writerows(chunk)

            print(f"Saved: {csv_filename} ({len(chunk)} posts)")

        print("\n" + "═" * 100)
        print("ALL JARVEE-READY CSVs GENERATED SUCCESSFULLY! (100 posts max per file)")
        print(f"   → {csv_dir}")
        print(f"   Total: {len(rows)} posts → split into {total_files} file(s)")
        print("   Old files cleared | Random captions | Smart quotes fixed | 100% safe")
        print("═" * 100)

    except Exception as e:
        print(f"Save failed: {e}")

def generate_final_csv():
    """FINAL JARVEE-COMPATIBLE CSV – UNLIMITED POSTS WITH RANDOM CAPTION REUSE + 100 PER FILE SPLIT"""
    
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
        captions_state = config.get('captions_state', 'mixed').lower().strip()
        
        if not author or not group_types:
            print("Error: Missing author or group_types")
            return
        
        print(f"Generating JARVEE-READY CSV → {author} ({group_types}) | Up to {cardamount} posts")
        print(f"Captions State: {captions_state.upper()}")
        
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

    base_csv_name = f"{author}_posts"
    print(f"Saving to → {csv_dir}")

    # ------------------------------------------------------------------ #
    # 3. Load & clean captions (bulletproof)
    # ------------------------------------------------------------------ #
    if not os.path.exists(captions_path):
        print(f"Captions missing: {captions_path}")
        return

    try:
        with open(captions_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        
        # Store captions with their IDs for tracking
        captions_with_ids = []
        captions_only = []
        
        for item in raw:
            if isinstance(item, dict) and 'description' in item:
                desc = str(item['description']).strip()
                if not desc:
                    continue

                desc = desc.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                desc = desc.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                desc = ' '.join(desc.split())
                desc = ''.join(ch for ch in desc if ord(ch) >= 32 or ch in '\t')
                
                # Get caption ID (use 'id' field or fallback to description)
                caption_id = item.get('id') or desc
                
                captions_with_ids.append({
                    'id': caption_id,
                    'description': desc
                })
                captions_only.append(desc)
        
        if not captions_with_ids:
            print("No valid captions after cleaning!")
            return
        print(f"Captions loaded & cleaned: {len(captions_with_ids)}")
        
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
            images = json.load(f).get("next_jpgcard", [])[:cardamount]
        if not images:
            print("No images!")
            return
        print(f"Images available: {len(images)}")
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
            schedule = json.load(f).get("next_schedule", [])[:cardamount]
        if not schedule:
            print("No schedule!")
            return
        print(f"Schedule slots: {len(schedule)}")
    except Exception as e:
        print(f"Schedule error: {e}")
        return

    # ------------------------------------------------------------------ #
    # 6. Handle FIXED captions state - track used captions internally
    # ------------------------------------------------------------------ #
    used_captions = []
    available_captions = captions_with_ids.copy()
    
    if captions_state == "fixed":
        print(f"\n📌 FIXED CAPTIONS MODE ENABLED - Tracking used captions internally")
        
        # Load previously used captions from CSV directory (internal tracking)
        tracking_file = os.path.join(csv_dir, f"{author}_used_captions.json")
        
        if os.path.exists(tracking_file):
            try:
                with open(tracking_file, 'r', encoding='utf-8') as f:
                    used_captions = json.load(f)
                print(f"📊 Loaded {len(used_captions)} used captions from internal tracking")
            except Exception as e:
                print(f"⚠️ Error loading used captions tracking: {e}")
                used_captions = []
        else:
            # Check if there are existing CSVs and extract used captions from them
            print("📊 No tracking file found. Checking existing CSVs...")
            existing_captions = []
            for file in os.listdir(csv_dir):
                if file.startswith(base_csv_name) and file.endswith('.csv'):
                    try:
                        with open(os.path.join(csv_dir, file), 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if 'Text' in row and row['Text'].strip():
                                    existing_captions.append(row['Text'].strip())
                    except Exception as e:
                        print(f"⚠️ Error reading {file}: {e}")
            
            if existing_captions:
                # Match existing captions with our caption IDs
                for cap in existing_captions:
                    for caption_item in captions_with_ids:
                        if caption_item['description'] == cap:
                            if caption_item['id'] not in used_captions:
                                used_captions.append(caption_item['id'])
                                break
                print(f"📊 Extracted {len(used_captions)} used captions from existing CSVs")
        
        # Filter out used captions
        used_ids = set(used_captions)
        available_captions = [c for c in captions_with_ids if c['id'] not in used_ids]
        
        print(f"📊 Total captions: {len(captions_with_ids)}, Used: {len(used_captions)}, Available: {len(available_captions)}")
        
        # Check if we have enough available captions for the required posts
        if len(available_captions) == 0:
            print("⚠️ ALL CAPTIONS HAVE BEEN USED!")
            print("💡 To generate a new CSV, you need to:")
            print("   1. Delete the tracking file or")
            print("   2. Switch to 'mixed' mode in config")
            return
        
        # Check if available captions are less than required
        if len(available_captions) < cardamount:
            print(f"⚠️ WARNING: Only {len(available_captions)} captions available but {cardamount} posts requested")
            print(f"📊 Will use all {len(available_captions)} available captions")
            final_count = min(cardamount, len(available_captions), len(images), len(schedule))
        else:
            final_count = min(cardamount, len(images), len(schedule))
        
        # If no posts to generate
        if final_count == 0:
            print("❌ No posts to generate. Not enough available captions.")
            return
        
        # We'll track which captions we use in this run
        used_in_this_run = []
        
    else:
        # MIXED mode - original behavior (unlimited reuse)
        print(f"\n🔄 MIXED CAPTIONS MODE - Unlimited reuse")
        final_count = min(cardamount, len(images), len(schedule))
        if final_count == 0:
            print("Nothing to generate.")
            return

    print(f"\nBuilding {final_count} JARVEE-READY posts...\n")

    # ------------------------------------------------------------------ #
    # 7. Build all rows with captions (respecting fixed mode)
    # ------------------------------------------------------------------ #
    rows = []
    random.seed()
    
    # For fixed mode, create a copy of available captions to work with
    if captions_state == "fixed":
        # Create a list of available captions to use (will be modified as we use them)
        remaining_captions = available_captions.copy()
        used_in_this_run = []
        
        for i in range(final_count):
            if not remaining_captions:
                # No more captions left - break out of loop
                print(f"⚠️ No more captions available after {i} posts")
                break
            
            # Select a random caption from remaining
            selected = random.choice(remaining_captions)
            caption_text = selected['description']
            caption_id = selected['id']
            
            # Remove it from remaining so it won't be reused
            remaining_captions.remove(selected)
            used_in_this_run.append(caption_id)
            
            img_url = images[i]
            slot = schedule[i]
            
            date_parts = slot['date'].split('/')
            yyyy_mm_dd = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
            post_time = f"{yyyy_mm_dd} {slot['time_24hour']}"
            
            rows.append({
                "Text": caption_text,
                "Image URL": img_url,
                "Tags": "",
                "Posting Time": post_time
            })
            
            # Print progress
            card = img_url.split('/')[-1].split('?')[0]
            #print(f"{i+1:3}. {post_time} → {card} | Caption: {caption_text[:50]}...")
    
    else:
        # MIXED mode - random reuse allowed
        for i in range(final_count):
            caption = random.choice(captions_only)
            img_url = images[i]
            slot = schedule[i]
            
            date_parts = slot['date'].split('/')
            yyyy_mm_dd = f"{date_parts[2]}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
            post_time = f"{yyyy_mm_dd} {slot['time_24hour']}"
            
            rows.append({
                "Text": caption,
                "Image URL": img_url,
                "Tags": "",
                "Posting Time": post_time
            })
            
            card = img_url.split('/')[-1].split('?')[0]
            #print(f"{i+1:3}. {post_time} → {card}")

    # ------------------------------------------------------------------ #
    # 8. DELETE OLD CSVs + SPLIT & SAVE NEW ONES (100 per file)
    # ------------------------------------------------------------------ #
    try:
        # Delete all existing CSVs with the same base name
        deleted_count = 0
        for file in os.listdir(csv_dir):
            if file.startswith(base_csv_name) and file.endswith('.csv'):
                os.remove(os.path.join(csv_dir, file))
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"\n✅ Deleted {deleted_count} old CSV(s) from {csv_dir}")
        else:
            print(f"\n📁 No old CSVs found in {csv_dir}")

        CHUNK_SIZE = 100
        total_files = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE  # Ceiling division

        for idx in range(total_files):
            chunk = rows[idx * CHUNK_SIZE : (idx + 1) * CHUNK_SIZE]
            
            # File naming: first file = author_posts.csv, rest = author_posts_a.csv, _b.csv, etc.
            if idx == 0 and len(rows) <= CHUNK_SIZE:
                csv_filename = f"{base_csv_name}.csv"
            else:
                suffix = '' if idx == 0 else '_' + string.ascii_lowercase[idx - 1]
                csv_filename = f"{base_csv_name}{suffix}.csv"
            
            csv_fullpath = os.path.join(csv_dir, csv_filename)

            with open(csv_fullpath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["Text", "Image URL", "Tags", "Posting Time"],
                    quoting=csv.QUOTE_ALL,
                    lineterminator='\n'
                )
                writer.writeheader()
                writer.writerows(chunk)

            print(f"✅ Saved: {csv_filename} ({len(chunk)} posts)")

        # ------------------------------------------------------------------ #
        # 9. Update tracking for FIXED mode
        # ------------------------------------------------------------------ #
        if captions_state == "fixed" and used_in_this_run:
            # Combine previously used with newly used
            all_used = used_captions + used_in_this_run
            
            # Save tracking file
            tracking_file = os.path.join(csv_dir, f"{author}_used_captions.json")
            try:
                with open(tracking_file, 'w', encoding='utf-8') as f:
                    json.dump(all_used, f, indent=2)
                print(f"📊 Updated tracking: {len(all_used)} total used captions")
                print(f"   Newly used in this run: {len(used_in_this_run)}")
                
                # Calculate remaining captions
                all_used_set = set(all_used)
                remaining = [c for c in captions_with_ids if c['id'] not in all_used_set]
                print(f"   Remaining available captions: {len(remaining)}")
                
                if len(remaining) == 0:
                    print("⚠️ ALL CAPTIONS HAVE NOW BEEN USED!")
                    print("💡 Next time, either:")
                    print("   1. Delete the tracking file to restart")
                    print("   2. Switch to 'mixed' mode in config")
                elif len(remaining) < 10:
                    print(f"⚠️ Only {len(remaining)} captions remaining!")
                
            except Exception as e:
                print(f"⚠️ Error saving tracking file: {e}")

        print("\n" + "═" * 100)
        print("✅ ALL JARVEE-READY CSVs GENERATED SUCCESSFULLY! (100 posts max per file)")
        print(f"   → {csv_dir}")
        print(f"   Total: {len(rows)} posts → split into {total_files} file(s)")
        print(f"   Mode: {captions_state.upper()}")
        
        if captions_state == "fixed":
            tracking_file = os.path.join(csv_dir, f"{author}_used_captions.json")
            if os.path.exists(tracking_file):
                try:
                    with open(tracking_file, 'r', encoding='utf-8') as f:
                        used_data = json.load(f)
                    print(f"   Used captions tracked: {len(used_data)} captions")
                except:
                    pass
        else:
            print("   Caption reuse: UNLIMITED (mixed mode)")
        
        print("   Old files cleared | Smart quotes fixed | 100% safe")
        print("═" * 100)

    except Exception as e:
        print(f"❌ Save failed: {e}") 

def uploadedjpgs():
    """Archive VALID URLs from next_jpgcard.json → uploadedjpgs.json
    AND DELETE **ALL** files from:
      - next jpg folder
      - uploaded jpgs folder
      - downloaded folder
      - jpgfolders folder ← NEW!
    Fully clear next_jpgcard.json.
    Only valid URLs are preserved. Safe, robust, full logging.
    
    MODIFICATION: 'uploaded_jpgs' is saved as a single, comma-separated string
    wrapped in double quotes, instead of a JSON list.
    """

    from datetime import datetime
    import pytz
    import os
    import json

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
    # 2. Define ALL relevant paths (including jpgfolders)
    # ------------------------------------------------------------------ #
    next_dir            = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    uploaded_dir        = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}'
    downloaded_dir      = fr'C:\xampp\htdocs\serenum-csv\files\downloaded\{author}'
    jpgfolders_dir      = fr'C:\xampp\htdocs\serenum-csv\files\jpgfolders\{author}'  # ← NEW
    next_json_path      = os.path.join(next_dir, 'next_jpgcard.json')
    uploaded_json_path = os.path.join(uploaded_dir, 'uploadedjpgs.json')

    # Ensure all directories exist
    for d in [next_dir, uploaded_dir, downloaded_dir, jpgfolders_dir]:
        os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 3. Load next_jpgcard.json – extract ONLY valid JPG URLs
    # ------------------------------------------------------------------ #
    next_urls = []
    next_json_data = {}
    if os.path.exists(next_json_path):
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                next_json_data = json.load(f)
            raw = next_json_data.get("next_jpgcard", [])

            # Handle case where 'next_jpgcard' might be a single string or a list
            items = [raw] if isinstance(raw, str) else raw
            for item in items:
                if isinstance(item, str):
                    url = item.strip()
                    if url.lower().startswith(('http://', 'https://')) and url.lower().endswith(('.jpg', '.jpeg')):
                        next_urls.append(url)
                    else:
                        print(f"Skipped invalid URL: {url}")
        except Exception as e:
            print(f"Failed to read next_jpgcard.json: {e}")
    else:
        print(f"Info: No next_jpgcard.json found.")

    print(f"Detected {len(next_urls)} valid URL(s) to archive.")

    # ------------------------------------------------------------------ #
    # 4. DELETE ALL FILES FROM 4 FOLDERS
    # ------------------------------------------------------------------ #
    folders_to_clean = [
        ("next jpg", next_dir),
        ("uploaded jpgs", uploaded_dir),
        ("downloaded", downloaded_dir),
        ("jpgfolders", jpgfolders_dir)  # ← NEW: FULL WIPE
    ]

    delete_stats = {
        "next jpg": {"deleted": 0, "failed": []},
        "uploaded jpgs": {"deleted": 0, "failed": []},
        "downloaded": {"deleted": 0, "failed": []},
        "jpgfolders": {"deleted": 0, "failed": []}
    }

    for label, folder in folders_to_clean:
        print(f"\nCleaning {label} folder: {folder}")
        try:
            # os.listdir will list files AND directories
            files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        except Exception as e:
            print(f"  [ERROR] Cannot access folder: {e}")
            continue

        if not files:
            print(f"  → Already empty.")
            continue

        # Preserve uploadedjpgs.json in its directory
        if label == "uploaded jpgs":
            files = [f for f in files if f != 'uploadedjpgs.json']

        for f in files:
            path = os.path.join(folder, f)
            try:
                os.remove(path)
                delete_stats[label]["deleted"] += 1
                print(f"    [DELETED] {f}")
            except Exception as e:
                delete_stats[label]["failed"].append((f, str(e)))
                print(f"    [FAILED] {f} → {e}")

    # ------------------------------------------------------------------ #
    # 5. Load existing uploadedjpgs.json – and parse its string format
    # ------------------------------------------------------------------ #
    existing_uploaded = []
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Expecting a string of comma-separated URLs or a list (for backward compatibility)
            raw_urls = data.get("uploaded_jpgs", [])
            
            if isinstance(raw_urls, str):
                # Split the comma-separated string into a list of URLs
                candidates = raw_urls.strip().split(',')
            elif isinstance(raw_urls, list):
                # Handle old list format for seamless transition
                candidates = raw_urls
            else:
                candidates = []

            for u in candidates:
                if isinstance(u, str) and u.strip().lower().startswith(('http://', 'https://')):
                    existing_uploaded.append(u.strip())
                    
        except Exception as e:
            print(f"Warning: Could not read or parse uploadedjpgs.json: {e}")

    print(f"Found {len(existing_uploaded)} previously archived URLs.")

    # ------------------------------------------------------------------ #
    # 6. Combine & deduplicate URLs (preserve order)
    # ------------------------------------------------------------------ #
    all_urls = existing_uploaded + next_urls
    unique_urls = list(dict.fromkeys(all_urls))
    newly_added = len(unique_urls) - len(existing_uploaded)

    # CONVERT LIST OF URLS TO THE REQUESTED SINGLE COMMA-SEPARATED STRING
    # Example: ["url1", "url2"] -> "url1,url2"
    uploaded_jpgs_string = ",".join(unique_urls)

    # ------------------------------------------------------------------ #
    # 7. Save updated uploadedjpgs.json with full cleanup metadata
    # ------------------------------------------------------------------ #
    timestamp = datetime.now(pytz.timezone('Africa/Lagos')).isoformat()

    uploaded_data = {
        # MODIFICATION HERE: storing the list as a single comma-separated string
        "uploaded_jpgs": uploaded_jpgs_string, 
        "last_cleared": timestamp,
        "total_uploaded": len(unique_urls),
        "urls_added_this_time": len(next_urls),
        "new_unique_urls": newly_added,
        "author": author,
        "cleanup_summary": {
            "folders_cleared": ["next jpg", "uploaded jpgs", "downloaded", "jpgfolders"],
            "next_jpg_files_deleted": delete_stats["next jpg"]["deleted"],
            "uploaded_jpgs_files_deleted": delete_stats["uploaded jpgs"]["deleted"],
            "downloaded_files_deleted": delete_stats["downloaded"]["deleted"],
            "jpgfolders_files_deleted": delete_stats["jpgfolders"]["deleted"],
            "failed_deletes": {
                "next_jpg": [f"{n}: {e}" for n, e in delete_stats["next jpg"]["failed"]],
                "uploaded_jpgs": [f"{n}: {e}" for n, e in delete_stats["uploaded jpgs"]["failed"]],
                "downloaded": [f"{n}: {e}" for n, e in delete_stats["downloaded"]["failed"]],
                "jpgfolders": [f"{n}: {e}" for n, e in delete_stats["jpgfolders"]["failed"]]
            }
        },
        "note": "TOTAL SYSTEM RESET: All image folders wiped. Ready for fresh markjpgs() cycle."
    }

    try:
        with open(uploaded_json_path, 'w', encoding='utf-8') as f:
            # json.dump will wrap the single string in quotes (e.g., "url1,url2,url3")
            json.dump(uploaded_data, f, indent=4, ensure_ascii=False)
        print(f"\nSaved uploadedjpgs.json → {len(unique_urls)} clean URLs preserved (as string)")
    except Exception as e:
        print(f"Failed to write uploadedjpgs.json: {e}")
        return

    # ------------------------------------------------------------------ #
    # 8. FULLY CLEAR next_jpgcard.json
    # ------------------------------------------------------------------ #
    try:
        cleared_json = {
            "next_jpgcard": [],
            "timestamp": timestamp,
            "total_checked": next_json_data.get("total_checked", 0),
            "total_valid": len(next_urls),
            "status": "FULLY CLEARED",
            "note": "All files deleted from: next jpg, uploaded jpgs, downloaded, jpgfolders. URLs archived."
        }
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump(cleared_json, f, indent=4, ensure_ascii=False)
        print("Cleared next_jpgcard.json → ready for fresh cycle")
    except Exception as e:
        print(f"Warning: Could not clear next_jpgcard.json: {e}")

    # ------------------------------------------------------------------ #
    # 9. Final Summary
    # ------------------------------------------------------------------ #
    total_deleted = sum(stats["deleted"] for stats in delete_stats.values())
    total_failed = sum(len(stats["failed"]) for stats in delete_stats.values())

    print("\n" + "="*88)
    print(f" TOTAL SYSTEM RESET COMPLETE FOR @{author.upper()}")
    print("="*88)
    print(f"   URLs archived             : {len(next_urls)} → {newly_added} new unique")
    print(f"   Total valid URLs          : {len(unique_urls)}")
    print(f"   Files deleted             : {total_deleted} across 4 folders")
    if total_failed:
        print(f"   Failed deletes            : {total_failed}")
    print(f"   Folders wiped             : next jpg | uploaded jpgs | downloaded | jpgfolders")
    print(f"   next_jpgcard.json         : FULLY CLEARED")
    print(f"   uploadedjpgs.json         : UPDATED & SAFE (URLs stored as a single string)")
    print("="*88)
    print(f" SYSTEM READY FOR FRESH MARKJPGS() CYCLE")
    print(f" @teamxtech – {timestamp.split('T')[0]} {timestamp.split('T')[1][:8]} WAT")
    print("="*88)



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
    fetch_jpgsvault_urls()
    markjpgs()
    cleanup_wrong_author_urls()
    update_calendar()
    generate_final_csv()
    #uploadedjpgs()
   



if __name__ == "__main__":
   main()
   

