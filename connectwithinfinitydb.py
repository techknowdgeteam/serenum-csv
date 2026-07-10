from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import signal
import sys
import os
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import psutil
import shutil

# ==============================================================================
# ⚠️ CRITICAL CONFIGURATION ⚠️
# 1. Update the paths below to match your local installation.
# 2. Update the CHROME_DRIVER_PATH to match the driver in your initialization function.
# ==============================================================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# NOTE: This path is critical for the initialize_browser function to work correctly.
# Ensure this matches the path used in the initialize_browser function's internal setup.
CHROME_DRIVER_PATH = r"C:\Users\PC\.wdm\drivers\chromedriver\win64\141.0.7390.122\chromedriver-win32\chromedriver.exe" 

# Server Configuration (Remains the same)
primary_servers = {
    'query_page': 'http://fhdrikxsirudr.fwh.is/phpmyadmintemplate.php',
    'fetch': 'http://fhdrikxsirudr.fwh.is/phpmyadmin_tablesfetch.php'
}
backup_servers = {
    'query_page': 'http://fhdrikxsirudr.fwh.is/phpmyadmintemplate.php',
    'fetch': 'http://fhdrikxsirudr.fwh.is/phpmyadmin_tablesfetch.php'
}
server3 = {
    'query_page': 'http://fhdrikxsirudr.fwh.is/phpmyadmintemplate.php',
    'fetch': 'http://fhdrikxsirudr.fwh.is/phpmyadmin_tablesfetch.php'
}


admin_email = 'ciphercirclex12@gmail.com'
admin_password = '@ciphercircleadminauthenticator#'
temp_download_dir = r'C:\xampp\htdocs\CIPHER\temp_downloads'
json_log_path = r'C:\xampp\htdocs\CIPHER\cipher trader\market\dbserver\connectwithdb.json'

# Global driver and session
driver = None
session = None
current_servers = primary_servers  # Start with primary servers
# ==============================================================================


import os
import time
import shutil
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# NEW IMPORT: This handles the version mismatch automatically
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# ⚠️ UPDATED CONFIGURATION
# ==============================================================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# CHROME_DRIVER_PATH is no longer needed as a hardcoded string!

def initialize_browser():
    """
    Initialize Chrome using ChromeDriverManager with the same configuration as fetch_urls.
    Automatically matches driver version to the installed browser version.
    """
    global driver, session, current_servers
    load_images_url()
    # Check if existing session is alive
    if driver is not None:
        log_and_print("Checking existing browser session...", "INFO")
        try:
            driver.get(current_servers['query_page'])
            # Re-sync session cookies
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            return True
        except Exception:
            log_and_print("Session invalid, restarting browser...", "WARNING")
            try: driver.quit()
            except: pass
            driver = None

    log_and_print("--- Step 1: Setting Up Chrome Environment ---", "TITLE")
    
    # Profile setup
    real_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    source_profile = os.path.join(real_user_data, "Profile 1")
    selenium_profile = os.path.expanduser(r"~\.chrome_selenium_profile")

    if not os.path.exists(selenium_profile) and os.path.exists(source_profile):
        log_and_print("Creating Selenium Chrome profile copy...", "INFO")
        try:
            shutil.copytree(source_profile, selenium_profile, dirs_exist_ok=True)
        except Exception as e:
            log_and_print(f"Profile copy failed: {e}", "WARNING")

    # Chrome Options - Matches fetch_urls configuration
    chrome_options = Options()
    if os.path.exists(CHROME_PATH):
        chrome_options.binary_location = CHROME_PATH
    
    chrome_options.add_argument(f"--user-data-dir={selenium_profile}")
    chrome_options.add_argument("--profile-directory=Default")
    
    # Headless mode (can be disabled for debugging)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Disable HTTPS upgrades and certificate errors (matching fetch_urls)
    chrome_options.add_argument("--disable-features=HttpsUpgrades")
    chrome_options.add_argument("--disable-features=HttpsOnlyMode")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-web-security")
    
    # Anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Log level
    chrome_options.add_argument("--log-level=3")

    log_and_print("--- Step 2: Auto-Installing Matching ChromeDriver ---", "TITLE")
    try:
        # Use ChromeDriverManager to auto-match driver version
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Hide automation (matching fetch_urls)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        log_and_print("ChromeDriver matched and initialized successfully.", "SUCCESS")
    except Exception as e:
        log_and_print(f"FATAL: Could not initialize ChromeDriver: {str(e)}", "ERROR")
        return False

    log_and_print("--- Step 3: Authenticating and Accessing Query Page ---", "TITLE")
    server_attempts = [
        (primary_servers, "Primary"),
        (backup_servers, "Backup"),
        (server3, "Server3")
    ]
    
    for servers, server_type in server_attempts:
        current_servers = servers
        try:
            driver.set_page_load_timeout(60)
            driver.get(servers['query_page'])
            
            # Wait for page to be fully loaded
            log_and_print("Waiting for page to load...", "INFO")
            max_wait = 30
            for i in range(max_wait):
                ready_state = driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    log_and_print("Page fully loaded!", "SUCCESS")
                    break
                time.sleep(1)
            
            # Inject credentials via LocalStorage
            driver.execute_script(f"localStorage.setItem('admin_email', '{admin_email}');")
            driver.execute_script(f"localStorage.setItem('admin_password', '{admin_password}');")
            
            # Reload to apply credentials
            driver.get(servers['query_page'])
            
            # Wait for query element to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "sql-query"))
            )
            
            log_and_print(f"Authenticated on {server_type} server", "SUCCESS")
            
            # Sync requests session
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            
            append_to_json_log(server_type, servers['query_page'])
            return True
        except Exception as e:
            log_and_print(f"{server_type} server failed: {str(e)}", "INFO")
            continue
    

    return False

def load_images_url():
    """
    Initialize its own browser session, load http://fhdrikxsirudr.fwh.is/loadimagesurl.php,
    extract only the text content (headless mode), then close the browser.
    """
    temp_driver = None
    url = "http://fhdrikxsirudr.fwh.is/loadimagesurl.php"
    
    try:
        print("=" * 60)
        print("LOAD IMAGES URL - Starting standalone browser session (HEADLESS)")
        print("=" * 60)
        
        # --- Step 1: Setup Chrome Profile ---
        real_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        source_profile = os.path.join(real_user_data, "Profile 1")
        selenium_profile = os.path.expanduser(r"~\.chrome_selenium_profile_temp")
        
        if not os.path.exists(selenium_profile) and os.path.exists(source_profile):
            print("Creating temporary Chrome profile copy...")
            try:
                shutil.copytree(source_profile, selenium_profile, dirs_exist_ok=True)
            except Exception as e:
                print(f"Profile copy warning: {e}")
        
        # --- Step 2: Configure Chrome Options ---
        chrome_options = Options()
        if os.path.exists(CHROME_PATH):
            chrome_options.binary_location = CHROME_PATH
        
        chrome_options.add_argument(f"--user-data-dir={selenium_profile}")
        chrome_options.add_argument("--profile-directory=Default")
        
        # HEADLESS MODE ENABLED
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Disable HTTPS upgrades and certificate errors
        chrome_options.add_argument("--disable-features=HttpsUpgrades")
        chrome_options.add_argument("--disable-features=HttpsOnlyMode")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-web-security")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Realistic user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Log level
        chrome_options.add_argument("--log-level=3")
        
        # --- Step 3: Initialize ChromeDriver ---
        print("Initializing ChromeDriver in headless mode...")
        service = Service(ChromeDriverManager().install())
        temp_driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Hide automation
        temp_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("ChromeDriver initialized successfully (headless)!")
        
        # --- Step 4: Load the URL ---
        print(f"Loading URL: {url}")
        temp_driver.get(url)
        time.sleep(3)  # Wait for page to fully load
        
        # Wait for body to be present
        WebDriverWait(temp_driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # --- Step 5: Extract only text content ---
        page_text = temp_driver.find_element(By.TAG_NAME, "body").text
        
        # --- Step 6: Print results ---
        print("\n" + "=" * 60)
        print(f"URL: {url}")
        print("=" * 60)
        print("EXTRACTED TEXT CONTENT:")
        print("-" * 60)
        print(page_text)
        print("=" * 60)
        
        # --- Step 7: Close browser ---
        temp_driver.quit()
        temp_driver = None
        
        # Clean up temporary profile (optional)
        try:
            if os.path.exists(selenium_profile):
                shutil.rmtree(selenium_profile)
                print("Temporary profile cleaned up.")
        except Exception as e:
            print(f"Could not delete temp profile: {e}")
        
        return page_text
        
    except Exception as e:
        print(f"ERROR loading {url}: {str(e)}")
        if temp_driver:
            try:
                temp_driver.quit()
            except:
                pass
        return None
       
def log_and_print(message, level="INFO"):
    """Helper function to print formatted messages without color coding."""
    indent = "    "
    formatted_message = f"{level:7} | {indent}{message}"
    print(formatted_message)

def append_to_json_log(server_type, server_url):
    """Append the server used to the JSON log file if the URL is different from the last recorded URL."""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'server_type': server_type,
        'server_url': server_url,
        'status': 'success'
    }
    log_data = []

    try:
        if os.path.exists(json_log_path):
            with open(json_log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
                if not isinstance(log_data, list):
                    log_data = []
    except Exception as e:
        log_and_print(f"Error reading JSON log file: {str(e)}, starting with empty log", "WARNING")
        log_data = []

    if log_data and log_data[-1].get('server_url') == server_url:
        log_and_print(f"Skipping log append: Same server URL ({server_url}) as last entry", "INFO")
        return

    log_data.append(log_entry)

    try:
        os.makedirs(os.path.dirname(json_log_path), exist_ok=True)
        with open(json_log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        log_and_print(f"Logged server usage ({server_type}: {server_url}) to {json_log_path}", "SUCCESS")
    except Exception as e:
        log_and_print(f"Failed to write to JSON log file: {str(e)}", "ERROR")

def signal_handler(sig, frame):
    """Handle script interruption (Ctrl+C)."""
    log_and_print("Script interrupted by user. Initiating cleanup...", "WARNING")
    cleanup()
    sys.exit(0)

def cleanup():
    """Clean up resources before exiting."""
    global driver, session
    log_and_print("--- Cleanup Operations ---", "TITLE")
    log_and_print("Starting cleanup process", "INFO")
    
    if driver:
        log_and_print("Clearing browser localStorage", "INFO")
        try:
            if "data:" not in driver.current_url:
                driver.execute_script("localStorage.clear();")
                log_and_print("LocalStorage cleared successfully", "SUCCESS")
        except Exception as e:
            log_and_print(f"Failed to clear localStorage: {str(e)}", "ERROR")
        log_and_print("Closing browser", "INFO")
        driver.quit()
        driver = None
        log_and_print("Browser closed successfully", "SUCCESS")

    if session:
        session.close()
        session = None
        log_and_print("Closed HTTP session", "SUCCESS")

    # Cleanup temp download directory
    if os.path.exists(temp_download_dir):
        log_and_print(f"Cleaning temporary download directory: {temp_download_dir}", "INFO")
        try:
            for temp_file in os.listdir(temp_download_dir):
                file_path = os.path.join(temp_download_dir, temp_file)
                os.remove(file_path)
            os.rmdir(temp_download_dir)
            log_and_print(f"Successfully removed temporary directory: {temp_download_dir}", "SUCCESS")
        except Exception as e:
            log_and_print(f"Failed to clean temporary directory: {str(e)}", "ERROR")


def check_server_availability(url):
    """Check if a server is available by sending a HEAD request with browser-like headers."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        response = requests.head(url, headers=headers, timeout=10, verify=True)
        log_and_print(f"Server check response for {url}: Status {response.status_code}", "INFO")
        return response.status_code == 200
    except requests.RequestException as e:
        log_and_print(f"Server availability check failed for {url}: {str(e)}", "INFO")
        return False

def execute_query_old(sql_query):
    global driver, session
    try:
        log_and_print("===== Database Query Execution =====", "TITLE")
        if not initialize_browser():
            return {'status': 'error', 'message': 'Browser init failed', 'results': []}

        # --- Step 5: JS Injection (The Latency Fix) ---
        try:
            query_textarea = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "sql-query"))
            )
            driver.execute_script("arguments[0].value = arguments[1];", query_textarea, sql_query)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", query_textarea)
            
            execute_button = driver.find_element(By.XPATH, "//button[text()='Execute Query']")
            execute_button.click()
        except Exception as e:
            return {'status': 'error', 'message': f"Input failed: {str(e)}", 'results': []}

        # --- Step 6: The Patient Scraper ---
        log_and_print("--- Step 6: Fetching Query Results (Selenium) ---", "TITLE")
        results = []
        try:
            # Check if it's a SELECT query
            is_select = sql_query.strip().upper().startswith("SELECT")

            if is_select:
                # CRITICAL: Wait for the table to physically exist in the DOM
                # This prevents the "Table not found" error during the ID check
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query-result table, #column-data table"))
                )
            else:
                # For UPDATE/INSERT, wait for the message div
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "message"))
                )

            # Now that we know the element is there, parse the HTML
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Look for table in common containers
            container = soup.find('div', id='query-result') or soup.find('div', id='column-data')
            table = container.find('table') if container else soup.find('table')

            if table:
                headers = [th.text.strip() for th in table.find_all('th')]
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) > 0:
                        row_dict = {headers[i]: cols[i].text.strip() for i in range(len(cols)) if i < len(headers)}
                        results.append(row_dict)
                log_and_print(f"Scraped {len(results)} rows successfully", "SUCCESS")
            else:
                # Handle Non-SELECT success messages
                msg_text = soup.find('div', id='message').get_text() if soup.find('div', id='message') else ""
                if "Affected rows" in msg_text or "success" in msg_text.lower():
                    results = [{'status': 'done'}]
                else:
                    log_and_print("No table found after waiting.", "WARNING")

            return {'status': 'success', 'results': results}

        except Exception as e:
            # If a SELECT query times out, it genuinely means no data was found
            log_and_print(f"Result fetch timed out or failed: {str(e)}", "WARNING")
            return {'status': 'success', 'results': []} # Return empty list so loop can continue

    except Exception as e:
        return {'status': 'error', 'message': str(e), 'results': []}

def execute_query(sql_query):
    global driver, session
    try:
        log_and_print("===== Database Query Execution =====", "TITLE")
        if not initialize_browser():
            return {'status': 'error', 'message': 'Browser init failed', 'results': []}
        
        # --- Step 5: JS Injection ---
        try:
            query_textarea = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "sql-query"))
            )
            driver.execute_script("arguments[0].value = arguments[1];", query_textarea, sql_query)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", query_textarea)
            
            execute_button = driver.find_element(By.XPATH, "//button[text()='Execute Query']")
            execute_button.click()
            log_and_print(f"Query executed: {sql_query[:100]}...", "INFO")
        except Exception as e:
            return {'status': 'error', 'message': f"Input failed: {str(e)}", 'results': []}

        # --- Step 6: Improved Result Fetching ---
        log_and_print("--- Step 6: Fetching Query Results (Selenium) ---", "TITLE")
        results = []
        
        try:
            # Check if it's a SELECT query
            is_select = sql_query.strip().upper().startswith("SELECT")
            
            # Give the page time to process the query
            time.sleep(3)  # Add a small delay for the AJAX response
            
            if is_select:
                # Try multiple selectors for result tables
                selectors = [
                    "#query-result table",
                    "#column-data table",
                    ".result table",
                    "table",
                    "#results table"
                ]
                
                table_found = False
                for selector in selectors:
                    try:
                        log_and_print(f"Looking for table with selector: {selector}", "INFO")
                        # Wait for the table to appear
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        table_found = True
                        log_and_print(f"Table found with selector: {selector}", "SUCCESS")
                        break
                    except:
                        continue
                
                if not table_found:
                    # Debug: Print the page source to see what's actually there
                    log_and_print("Table not found. Checking page content...", "WARNING")
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    if "no results" in page_text.lower() or "empty" in page_text.lower():
                        log_and_print("Query returned no results (empty set)", "INFO")
                        return {'status': 'success', 'results': []}
                    else:
                        log_and_print(f"Page contains: {page_text[:500]}", "INFO")
                        return {'status': 'success', 'results': []}
                
                # Now parse the HTML
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find the table in the page
                table = None
                for container_id in ['query-result', 'column-data', 'results']:
                    container = soup.find('div', id=container_id)
                    if container:
                        table = container.find('table')
                        if table:
                            log_and_print(f"Found table in container: {container_id}", "SUCCESS")
                            break
                
                if not table:
                    table = soup.find('table')
                
                if table:
                    # Extract headers
                    headers = []
                    header_row = table.find('tr')
                    if header_row:
                        headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
                    
                    # Extract data rows
                    for row in table.find_all('tr')[1:]:  # Skip header row
                        cols = row.find_all('td')
                        if len(cols) > 0:
                            row_dict = {}
                            for i, col in enumerate(cols):
                                if i < len(headers):
                                    row_dict[headers[i]] = col.text.strip()
                                else:
                                    row_dict[f"col_{i}"] = col.text.strip()
                            results.append(row_dict)
                    
                    log_and_print(f"Scraped {len(results)} rows successfully", "SUCCESS")
                else:
                    log_and_print("No table found in page source", "WARNING")
                    # Check if there's a message about empty result
                    msg_div = soup.find('div', id='message')
                    if msg_div and "affected rows" in msg_div.text.lower():
                        results = [{'status': 'done', 'message': msg_div.text.strip()}]
                
                return {'status': 'success', 'results': results}
                
            else:
                # For UPDATE/INSERT, wait for the message div
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "message"))
                )
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                msg_text = soup.find('div', id='message').get_text() if soup.find('div', id='message') else ""
                if "Affected rows" in msg_text or "success" in msg_text.lower():
                    results = [{'status': 'done', 'message': msg_text}]
                return {'status': 'success', 'results': results}

        except Exception as e:
            log_and_print(f"Result fetch failed: {str(e)}", "ERROR")
            # Don't return error - it might just be empty results
            return {'status': 'success', 'results': []}

    except Exception as e:
        log_and_print(f"Query execution error: {str(e)}", "ERROR")
        return {'status': 'error', 'message': str(e), 'results': []}
    
def shutdown():
    """Explicitly shut down the browser and cleanup."""
    cleanup()

if __name__ == "__main__":
    # For testing standalone
    # REMEMBER TO SET CHROME_DRIVER_PATH AND CHROME_PATH BEFORE RUNNING!
    
    sql_query = "SELECT id FROM jpgsvault_table WHERE id = '2'"
    result = execute_query(sql_query)
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))
    shutdown()
    