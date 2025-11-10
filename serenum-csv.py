from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def launch_browser():
    """
    Initialize Chrome WebDriver in headed or headless mode (mode set in main()),
    and navigate to the hardcoded URL.

    Returns:
        webdriver.Chrome: Initialized WebDriver instance on success.
        None: On failure (with error logged).
    """
    # Hardcoded URL
    URL = "https://jpgsvault.rf.gd/jpgsvault.php"
    CHROME_BINARY_PATH = r"C:\xampp\htdocs\CIPHER\googlechrome\Google\Chrome\Application\chrome.exe"

    # Mode is injected via global or closure — but here we read from a variable set in main
    # We'll use a module-level variable set by main()
    mode = getattr(launch_browser, 'mode', 'headed').strip().lower()

    options = Options()
    
    # Common options
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-autofill")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Set binary location
    if CHROME_BINARY_PATH and os.path.exists(CHROME_BINARY_PATH):
        options.binary_location = CHROME_BINARY_PATH
    else:
        logger.warning(f"Custom Chrome binary not found at {CHROME_BINARY_PATH}. Using system default.")

    # Mode-specific options
    if mode in ["headless", "head"]:
        logger.info("Launching browser in HEADLESS mode")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        logger.info("Launching browser in HEADED mode")
        options.add_argument("--start-maximized")

    try:
        # Use webdriver-manager with specific ChromeDriver version
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(driver_version="139.0.7258.128").install()),
            options=options
        )
        driver.set_page_load_timeout(60)
        logger.info(f"Navigating to {URL}")
        driver.get(URL)
        return driver
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        return None

def check_single_url(url: str, timeout: int = 30) -> tuple[bool, str]:
    """
    Ultra-tolerant check: Full GET + JPG magic bytes verification.
    Returns (is_valid: bool, debug_info: str)
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        debug = f"Status: {response.status_code}, Size: {len(response.content)} bytes"

        if response.status_code != 200:
            return False, debug + f" (HTTP {response.status_code})"

        # Check for JPG magic bytes (FF D8 FF at start)
        if len(response.content) > 3 and response.content[:3] == b'\xff\xd8\xff':
            return True, debug + " (Valid JPG)"

        # Fallback: If not magic bytes, check if content looks like error HTML
        if b'<html' in response.content.lower() or b'404' in response.content:
            return False, debug + " (Error page detected)"

        # Otherwise, assume valid (e.g., other image types)
        return True, debug + " (Content OK)"

    except requests.exceptions.Timeout:
        return False, "Timeout (server slow)"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def markjpgs():
    # ------------------------------------------------------------------ #
    # 1. Load configuration
    # ------------------------------------------------------------------ #
    JSON_CONFIG_PATH = r'C:\xampp\htdocs\serenum-csv\pageandgroupauthors.json'

    try:
        with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        author = config.get('author', '').strip()
        if not author:
            print("Error: 'author' is missing or empty.")
            return

        try:
            cardamount = int(config.get('cardamount', 1))
            cardamount = max(1, cardamount)
        except (ValueError, TypeError):
            print("Warning: 'cardamount' invalid. Using 1.")
            cardamount = 1

    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    # ------------------------------------------------------------------ #
    # 2. Load already uploaded URLs (to avoid duplicates)
    # ------------------------------------------------------------------ #
    uploaded_dir = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}'
    uploaded_json_path = os.path.join(uploaded_dir, 'uploadedjpgs.json')

    already_uploaded = set()
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                uploaded_data = json.load(f)
                uploaded_list = uploaded_data.get("uploaded_jpgs", [])
                already_uploaded = set(uploaded_list)
            print(f"Loaded {len(already_uploaded)} previously uploaded JPGs (will skip duplicates)")
        except Exception as e:
            print(f"Warning: Could not read uploadedjpgs.json → {e}")
            already_uploaded = set()
    else:
        print("No uploadedjpgs.json found → starting fresh")

    # ------------------------------------------------------------------ #
    # 3. Prepare output folder / file
    # ------------------------------------------------------------------ #
    output_dir = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, 'next_jpgcard.json')

    # ------------------------------------------------------------------ #
    # 4. Scan for NEW valid URLs only
    # ------------------------------------------------------------------ #
    base_url = f"https://jpgsvault.rf.gd//jpgs/{author}/card_"
    valid_new_urls = []
    checked_urls = 0
    invalid_count = 0
    skipped_duplicates = 0

    print(f"\nTarget: {cardamount} NEW valid JPG(s) for author '{author}'")
    print("Scanning URLs → skipping already uploaded ones...\n")

    for idx in range(1, 100_000):  # increased safety limit
        url = f"{base_url}{idx}.jpg"
        checked_urls += 1

        # Early skip if already uploaded
        if url in already_uploaded:
            skipped_duplicates += 1
            if skipped_duplicates <= 10 or skipped_duplicates % 50 == 0:
                print(f"  [Skipped] Already uploaded: {url}")
            continue

        is_valid, debug = check_single_url(url)
        if is_valid:
            valid_new_urls.append(url)
            print(f"  [NEW] {url} ({debug})")
        else:
            invalid_count += 1
            print(f"  [Invalid] {url} ({debug})")

        # Stop when we have enough NEW ones
        if len(valid_new_urls) >= cardamount:
            print(f"\nSuccess: Found {len(valid_new_urls)} NEW valid URLs!")
            break

    # If not enough, warn
    if len(valid_new_urls) < cardamount:
        print(f"\nWarning: Only found {len(valid_new_urls)} new URLs (wanted {cardamount})")
        print("   → All remaining cards on server are already uploaded.")

    # ------------------------------------------------------------------ #
    # 5. Write next_jpgcard.json with ONLY NEW URLs + stats
    # ------------------------------------------------------------------ #
    try:
        timestamp = datetime.now(pytz.timezone('Africa/Lagos')).isoformat()
        data = {
            "next_jpgcard": valid_new_urls,
            "timestamp": timestamp,
            "total_checked": checked_urls,
            "total_valid_new": len(valid_new_urls),
            "total_invalid": invalid_count,
            "skipped_already_uploaded": skipped_duplicates,
            "author": author,
            "note": "Only brand-new URLs (not in uploadedjpgs.json)"
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print("\n" + "=" * 70)
        print(f"Saved {len(valid_new_urls)} NEW valid link(s) to:")
        print(f"   {json_path}")
        print(f"Checked URLs           : {checked_urls}")
        print(f"New & Valid            : {len(valid_new_urls)}")
        print(f"Invalid / Broken       : {invalid_count}")
        print(f"Skipped (already used) : {skipped_duplicates}")
        print("=" * 70)

        if valid_new_urls:
            print("\nNew URLs ready for posting:")
            update_calendar()
            for u in valid_new_urls:
                print(f"   {u}")
        else:
            print("\nNo new URLs found. All cards have been used.")

    except Exception as e:
        print(f"Failed to write JSON: {e}")


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
    """Move next → last (OVERWRITE last), generate NEW next_schedule using ID-only deduplication.
       Now supports custom start via 'schedule_date' in config.
       AFTER generation: updates 'schedule_date' in config to LAST slot in new next_schedule."""

    import os
    import json
    import random
    from datetime import datetime, timedelta

    # === Load config ===
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

    # === Determine starting datetime: custom schedule_date or now ===
    start_datetime = None
    if schedule_date_str and len(schedule_date_str) >= 10:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                if ' ' in schedule_date_str:
                    dt = datetime.strptime(schedule_date_str, fmt)
                else:
                    dt = datetime.strptime(schedule_date_str, fmt)
                    dt = dt.replace(hour=0, minute=0)
                start_datetime = dt
                print(f"Using custom schedule_date: {start_datetime.strftime('%d/%m/%Y %H:%M')}")
                break
            except ValueError:
                continue

    if start_datetime is None:
        start_datetime = datetime.now()
        print(f"No valid schedule_date found. Using current time: {start_datetime.strftime('%d/%m/%Y %H:%M')}")

    current_datetime = start_datetime
    current_date_obj = current_datetime.date()
    current_time_24hour = current_datetime.strftime("%H:%M")
    current_date_str = current_datetime.strftime("%d/%m/%Y")

    print(f"Starting schedule from: {current_date_str} {current_time_24hour}")

    # === Paths ===
    base_dir = f"C:\\xampp\\htdocs\\serenum-csv\\files\\next jpg\\{author}\\jsons\\{group_types}"
    calendar_path = os.path.join(base_dir, f"{type_value}calendar.json")
    schedules_path = os.path.join(base_dir, f"{type_value}schedules.json")

    # === Load calendar ===
    try:
        with open(calendar_path, 'r', encoding='utf-8') as f:
            calendar_data = json.load(f)
    except Exception as e:
        print(f"Calendar error: {e}")
        return

    # === Load timeorders ===
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

    # === Load existing schedules ===
    old_last_schedule = []
    old_next_schedule = []
    if os.path.exists(schedules_path):
        try:
            with open(schedules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            old_last_schedule = data.get("last_schedule", [])
            old_next_schedule = data.get("next_schedule", [])
            print(f"Loaded: {len(old_last_schedule)} in last, {len(old_next_schedule)} in next")
        except Exception as e:
            print(f"Error reading schedules.json: {e}")

    # === STEP 1: OVERWRITE last_schedule with old_next_schedule ===
    new_last_schedule = old_next_schedule
    print(f"OVERWRITTEN last_schedule with {len(new_last_schedule)} slots from previous next_schedule")

    # === STEP 2: Build used_ids set (from NEW last_schedule only) ===
    used_ids = set()
    for slot in new_last_schedule:
        slot_id = slot.get("id")
        if slot_id:
            used_ids.add(slot_id)

    # === STEP 3: Generate NEW next_schedule from start_datetime onward ===
    next_schedule_list = []
    search_date = current_date_obj

    while len(next_schedule_list) < cardamount:
        found_today = False
        day_found_in_calendar = False

        for cal in calendar_data["calendars"]:
            for week in cal["days"]:
                for day_entry in week["days"]:
                    day = day_entry.get("day")
                    if not day or not day.get("date"):
                        continue
                    date_str = day["date"]
                    try:
                        slot_date = datetime.strptime(date_str, "%d/%m/%Y")
                    except:
                        continue

                    if slot_date.date() < search_date:
                        continue
                    if slot_date.date() > search_date and search_date != current_date_obj:
                        continue

                    day_found_in_calendar = True

                    for slot in day.get("time_ahead", []):
                        if len(next_schedule_list) >= cardamount:
                            break

                        if slot["24hours"] not in [t["24hours"] for t in timeorders]:
                            continue
                        if "passed" not in slot["consideration"].lower():
                            continue

                        slot_time_str = slot["24hours"]
                        slot_datetime = datetime.combine(
                            slot_date.date(),
                            datetime.strptime(slot_time_str, "%H:%M").time()
                        )

                        if slot_datetime <= current_datetime:
                            continue

                        if slot_date.date() == current_date_obj:
                            time_diff = (slot_datetime - current_datetime).total_seconds() / 60
                            if time_diff < 50:
                                continue

                        if slot["id"] in used_ids:
                            continue

                        new_slot = {
                            "id": slot["id"],
                            "date": date_str,
                            "time_12hour": slot["12hours"],
                            "time_24hour": slot["24hours"]
                        }
                        next_schedule_list.append(new_slot)
                        used_ids.add(slot["id"])
                        print(f"Scheduled: {date_str} {slot['24hours']} (id: {slot['id']})")
                        found_today = True

                    if len(next_schedule_list) >= cardamount:
                        break
                if len(next_schedule_list) >= cardamount:
                    break
            if len(next_schedule_list) >= cardamount:
                break

        if len(next_schedule_list) < cardamount:
            search_date += timedelta(days=1)
            print(f"No more slots today. Moving to next day: {search_date.strftime('%d/%m/%Y')}")

        if not day_found_in_calendar and len(next_schedule_list) == 0:
            print("No future calendar entries found.")
            break

    if not next_schedule_list:
        print("No new slots available after the specified schedule_date.")
        return

    # === STEP 4: Write NEW schedules.json ===
    output_data = {
        "last_schedule": new_last_schedule,
        "next_schedule": next_schedule_list
    }

    os.makedirs(os.path.dirname(schedules_path), exist_ok=True)
    with open(schedules_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    # === STEP 5: UPDATE schedule_date in pageandgroupauthors.json to LAST slot in next_schedule ===
    if next_schedule_list:
        last_slot = next_schedule_list[-1]  # Last item in the list
        last_date_str = last_slot["date"]
        last_time_24 = last_slot["time_24hour"]

        # Parse and reformat to ensure correct format: "12/11/2025 04:27"
        try:
            last_datetime = datetime.strptime(f"{last_date_str} {last_time_24}", "%d/%m/%Y %H:%M")
            new_schedule_date = last_datetime.strftime("%d/%m/%Y %H:%M")
            
            # Update config in memory
            cfg["schedule_date"] = new_schedule_date

            # Write back to pageandgroupauthors.json
            with open(pageauthors_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)

            print(f"UPDATED schedule_date in config → \"{new_schedule_date}\" (last slot in next_schedule)")
        except Exception as e:
            print(f"Failed to update schedule_date: {e}")

    print(f"SUCCESS: {len(next_schedule_list)} NEW slots scheduled starting from {current_datetime.strftime('%d/%m/%Y %H:%M')}.")
    print(f"         last_schedule now contains {len(new_last_schedule)} slot(s) [OVERWRITTEN]")

    # Randomize minutes (01–30)
    try:
        randomize_next_schedule_minutes()
    except NameError:
        print("randomize_next_schedule_minutes() not defined.")      

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
        uploadedjpgs()

    except Exception as e:
        print(f"Save failed: {e}")

def uploadedjpgs():
    """Move all URLs from next_jpgcard.json → uploadedjpgs.json
       Clears next_jpgcard.json after successful move.
       FIXED: All paths use raw strings (r'...') to prevent Unicode escape errors."""

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
    # 2. Define paths - ALL USING RAW STRINGS (r"...")
    # ------------------------------------------------------------------ #
    next_dir = fr'C:\xampp\htdocs\serenum-csv\files\next jpg\{author}'
    uploaded_dir = fr'C:\xampp\htdocs\serenum-csv\files\uploaded jpgs\{author}'

    next_json_path = os.path.join(next_dir, 'next_jpgcard.json')
    uploaded_json_path = os.path.join(uploaded_dir, 'uploadedjpgs.json')

    # ------------------------------------------------------------------ #
    # 3. Check if next_jpgcard.json exists and has data
    # ------------------------------------------------------------------ #
    if not os.path.exists(next_json_path):
        print(f"No next_jpgcard.json found at:\n   {next_json_path}")
        print("Nothing to upload/move.")
        return

    try:
        with open(next_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read next_jpgcard.json: {e}")
        return

    next_urls = data.get("next_jpgcard", [])
    if not next_urls:
        print("next_jpgcard.json is empty – nothing to move.")
        return

    print(f"\nFound {len(next_urls)} URL(s) in next_jpgcard.json")
    print("Moving to uploadedjpgs.json...\n")

    # ------------------------------------------------------------------ #
    # 4. Load existing uploadedjpgs.json (append mode)
    # ------------------------------------------------------------------ #
    existing_uploaded = []
    if os.path.exists(uploaded_json_path):
        try:
            with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_uploaded = existing_data.get("uploaded_jpgs", [])
            print(f"Found {len(existing_uploaded)} previously uploaded JPGs.")
        except Exception as e:
            print(f"Warning: Could not read existing uploadedjpgs.json: {e}")
            existing_uploaded = []

    # ------------------------------------------------------------------ #
    # 5. Combine and deduplicate
    # ------------------------------------------------------------------ #
    all_uploaded = existing_uploaded + next_urls
    seen = set()
    unique_uploaded = []
    for url in all_uploaded:
        if url not in seen:
            seen.add(url)
            unique_uploaded.append(url)

    added_count = len(unique_uploaded) - len(existing_uploaded)

    # ------------------------------------------------------------------ #
    # 6. Save to uploadedjpgs.json
    # ------------------------------------------------------------------ #
    os.makedirs(uploaded_dir, exist_ok=True)

    timestamp = datetime.now(pytz.timezone('Africa/Lagos')).isoformat()

    uploaded_data = {
        "uploaded_jpgs": unique_uploaded,
        "last_moved_from_next": timestamp,
        "total_uploaded": len(unique_uploaded),
        "moved_this_time": len(next_urls),
        "newly_added": added_count,
        "author": author
    }

    try:
        with open(uploaded_json_path, 'w', encoding='utf-8') as f:
            json.dump(uploaded_data, f, indent=4)

        print("=" * 60)
        print(f"SUCCESS: Moved {len(next_urls)} JPG URL(s) to uploaded list")
        print(f"   → {uploaded_json_path}")
        print(f"   Total in uploadedjpgs.json: {len(unique_uploaded)}")
        print(f"   Newly added (no dupes): {added_count}")
        print("=" * 60)

        print("\nLast 5 uploaded URLs:")
        for url in unique_uploaded[-5:]:
            print(f"   {url}")

    except Exception as e:
        print(f"Failed to write uploadedjpgs.json: {e}")
        return

    # ------------------------------------------------------------------ #
    # 7. CLEAR next_jpgcard.json
    # ------------------------------------------------------------------ #
    try:
        with open(next_json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "next_jpgcard": [],
                "timestamp": timestamp,
                "total_checked": data.get("total_checked", 0),
                "total_valid": 0,
                "total_invalid": data.get("total_invalid", 0),
                "note": "Cleared by uploadedjpgs() – all moved to uploaded jpgs folder"
            }, f, indent=4)

        print(f"\nCleared next_jpgcard.json (ready for next batch)")

    except Exception as e:
        print(f"Warning: Could not clear next_jpgcard.json: {e}")

    print("\nAll done! Your uploaded JPGs are now safely archived.")

def main():
    markjpgs()
    generate_final_csv()

main()



    
