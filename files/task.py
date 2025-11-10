from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import os
import psutil  # Import psutil for process management

def close_existing_chrome_instances():
    """Close all running Chrome instances and print a single message if any were closed."""
    closed_any = False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() in ['chrome', 'chrome.exe', 'chromedriver', 'chromedriver.exe']:
                proc.terminate()  # Attempt to terminate gracefully
                try:
                    proc.wait(timeout=3)  # Wait up to 3 seconds for the process to terminate
                except psutil.TimeoutExpired:
                    proc.kill()  # Force kill if it doesn't terminate
                closed_any = True  # Mark that at least one process was closed
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue  # Skip if process no longer exists or access is denied
    
    if closed_any:
        print("Closed Chrome process(es)")

def necessarytracks(driver, wait):
    """Handle optional tracking tasks, such as clicking 'Continue' or 'Allow' on the remember browser page."""
    try:
        # Check if the page title contains "Remember Browser"
        page_title = driver.title.lower()
        if "remember browser" in page_title:
            print("Reached 'remember browser' page. Attempting to click 'Continue' button.")
            try:
                # Wait for the "Continue" or "Allow" button and click it
                continue_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Allow')]"))
                )
                continue_button.click()
                print("Clicked 'Continue' on remember browser page.")
                time.sleep(1)  # Brief pause to allow page transition
            except Exception as e:
                print(f"Failed to click 'Continue' button on remember browser page: {str(e)}")
                # Continue execution instead of raising an error, as this is optional
        # Add more tracking tasks here if needed in the future
    except Exception as e:
        print(f"Error in necessarytracks: {str(e)}")
        # Continue execution, as tracking tasks are optional

def homepage(driver, wait, is_business=False):
    """Check if the current page is the Facebook or Business Manager homepage."""
    try:
        if is_business:
            # For Business Manager, check for elements indicating the homepage (e.g., "Create Ad" or account selector)
            wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create ad') or contains(@class, 'business-account-selector')]"))
            )
            print("Confirmed: Business Manager homepage detected.")
        else:
            # For regular Facebook, look for "What's on your mind?" text
            wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), \"what's on your mind\")]"))
            )
            print("Confirmed: Facebook homepage detected with 'What's on your mind?' text.")
        return True
    except Exception as e:
        print(f"Homepage not detected (Business={is_business}): {str(e)}")
        return False

def facebook(driver, wait):
    """Handle login and homepage check for Facebook."""
    try:
        # Navigate to Facebook
        driver.get("https://www.facebook.com")
        
        # Check if already on the homepage
        if homepage(driver, wait, is_business=False):
            print("Launched directly to Facebook homepage, no login required.")
            return True
        
        # Check if login form is present
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        placeholder_text = email_field.get_attribute("placeholder").lower()
        if "email address or phone number" in placeholder_text:
            print("Confirmed: Facebook login form detected with 'Email address or phone number' placeholder.")
            
            # Enter credentials
            email_field.send_keys("taskbusterx@gmail.com")
            password_field = driver.find_element(By.ID, "pass")
            password_field.send_keys("@taskbusterx#")
            
            # Click login button
            login_button = driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Handle 2FA or other prompts
            try:
                wait.until(EC.url_contains("two_step_verification/two_factor/"))
                print("Reached 2FA verification page for Facebook.")
                print("Waiting for you to manually enter your authentication.")
                
                # Continuously check for expected pages
                while True:
                    current_url = driver.current_url
                    if homepage(driver, wait, is_business=False) or "?sk=welcome" in current_url or current_url in ["https://www.facebook.com/", "https://www.facebook.com"]:
                        print("Facebook login successful (reached welcome page or homepage)")
                        return True
                    elif "two_step_verification/two_factor/" in current_url:
                        time.sleep(1)  # Wait before checking again
                    else:
                        necessarytracks(driver, wait)
                        if not (homepage(driver, wait, is_business=False) or "?sk=welcome" in current_url or current_url in ["https://www.facebook.com/", "https://www.facebook.com"]):
                            print("Unexpected URL detected:", current_url)
                            raise Exception("Navigated to an unexpected page")
                                
            except Exception as e:
                print(f"2FA page not detected for Facebook or error occurred: {str(e)}")
                if homepage(driver, wait, is_business=False) or "?sk=welcome" in driver.current_url or driver.current_url in ["https://www.facebook.com/", "https://www.facebook.com"]:
                    print("Facebook login successful (reached welcome page or homepage without 2FA)")
                    return True
                else:
                    raise Exception("Facebook login failed")
                
        else:
            print(f"Login form not confirmed: Placeholder text '{placeholder_text}' does not contain 'Email address or phone number'.")
            raise Exception("Facebook login form not confirmed")
            
    except Exception as e:
        print(f"Facebook login error: {str(e)}")
        raise

def metaBusiness(driver, wait):
    """Handle login and homepage check for Business Manager."""
    try:
        # Navigate to Business Manager
        driver.get("https://business.facebook.com")
        
        # Check if already on Business Manager homepage
        if homepage(driver, wait, is_business=True):
            print("Launched directly to Business Manager homepage, no additional login required.")
        else:
            # Check for login form
            try:
                email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
                placeholder_text = email_field.get_attribute("placeholder").lower()
                if "email address or phone number" in placeholder_text:
                    print("Confirmed: Business Manager login form detected.")
                    # Enter credentials
                    email_field.send_keys("taskbusterx@gmail.com")
                    password_field = driver.find_element(By.ID, "pass")
                    password_field.send_keys("@taskbusterx#")
                    login_button = driver.find_element(By.NAME, "login")
                    login_button.click()
                else:
                    print(f"Business Manager login form not confirmed: Placeholder text '{placeholder_text}'.")
                    raise Exception("Business Manager login form not confirmed")
            except Exception as e:
                print(f"No login form detected on Business Manager, checking for prompts: {str(e)}")
                # Handle 2FA or tracking prompts
                try:
                    wait.until(EC.url_contains("two_step_verification/two_factor/"))
                    print("Reached 2FA verification page for Business Manager.")
                    print("Waiting for you to manually enter your authentication.")
                    while True:
                        current_url = driver.current_url
                        if homepage(driver, wait, is_business=True) or "business.facebook.com" in current_url:
                            print("Business Manager login successful (reached homepage)")
                            break
                        elif "two_step_verification/two_factor/" in current_url:
                            time.sleep(1)
                        else:
                            necessarytracks(driver, wait)
                            if not (homepage(driver, wait, is_business=True) or "business.facebook.com" in current_url):
                                print("Unexpected URL detected:", current_url)
                                raise Exception("Navigated to an unexpected page")
                except Exception as e:
                    print(f"2FA page not detected for Business Manager or error occurred: {str(e)}")
                    if homepage(driver, wait, is_business=True) or "business.facebook.com" in driver.current_url:
                        print("Business Manager login successful (reached homepage without 2FA)")
                    else:
                        raise Exception("Business Manager login failed")
        
        # Click the 'Create Post' button
        try:
            create_post_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create post')]"))
            )
            create_post_button.click()
            print("Clicked 'Create Post' button on Business Manager page.")
            time.sleep(1)  # Brief pause to allow the post creation dialog to load
        except Exception as e:
            print(f"Failed to click 'Create Post' button: {str(e)}")
            try:
                create_post_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid*='create-post'], a[href*='create_post'], div[role='button'][aria-label*='Create Post']"))
                )
                create_post_button.click()
                print("Clicked 'Create Post' button using alternative locator.")
                time.sleep(1)
            except Exception as e2:
                print(f"Alternative locator for 'Create Post' also failed: {str(e2)}")
                raise Exception("Could not locate or click 'Create Post' button")
        
        return True
        
    except Exception as e:
        print(f"Business Manager error: {str(e)}")
        raise

def textstopost(driver, wait):
    """Enter the first sentence into the post text field."""
    try:
        # First sentence from the provided list
        post_text = "A massive financial breakthrough is coming your way this week, claim it now!"
        
        # Locate the text input field in the post creation dialog
        text_field = wait.until(
            EC.presence_of_element_located((By.XPATH, "//textarea | //div[@contenteditable='true'] | //input[@placeholder='Write something...']"))
        )
        text_field.click()  # Ensure the field is focused
        text_field.send_keys(post_text)
        print(f"Entered text into post field: '{post_text}'")
        time.sleep(1)  # Brief pause to ensure text is entered
        
    except Exception as e:
        print(f"Failed to enter text: {str(e)}")
        # Try alternative locators for text field
        try:
            text_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, div[contenteditable='true'], input[placeholder*='write']"))
            )
            text_field.click()
            text_field.send_keys(post_text)
            print(f"Entered text using alternative locator: '{post_text}'")
            time.sleep(1)
        except Exception as e2:
            print(f"Alternative locator for text field failed: {str(e2)}")
            # Do not raise exception here to allow wait_for_command to be called

def enable_scheduling(driver, wait):
    """Enable the 'Set date and time' toggle, locate 'Active times' text, and identify the month and year 2025 in the calendar element."""
    try:
        # Wait for and click the scheduling toggle
        scheduling_toggle = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'set date and time')]//input[@type='checkbox'] | //div[contains(@aria-label, 'Set date and time') or contains(text(), 'Set date and time')]//following-sibling::div[@role='switch'] | //span[contains(text(), 'Set date and time')]/following::input[1]"))
        )
        # If it's a checkbox, click it to toggle on
        if scheduling_toggle.tag_name == 'input' and scheduling_toggle.get_attribute('type') == 'checkbox':
            if not scheduling_toggle.is_selected():
                scheduling_toggle.click()
                print("Toggled 'Set date and time' checkbox on.")
            else:
                print("'Set date and time' is already enabled.")
        else:
            # For switch-like elements, click the switch
            scheduling_toggle.click()
            print("Clicked 'Set date and time' toggle.")
        
        time.sleep(2)  # Pause to allow the date/time picker to appear

        # Locate the "Active times" text
        try:
            active_times_text = wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'active times')]"))
            )
            print("Located 'Active times' text in the scheduling section.")
        except Exception as e:
            print(f"Failed to locate 'Active times' text: {str(e)}")
            try:
                active_times_text = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Active times'], div[class*='schedule'] span"))
                )
                print("Located 'Active times' text using alternative locator.")
            except Exception as e2:
                print(f"Alternative locator for 'Active times' text failed: {str(e2)}")
                # Continue despite failure to locate "Active times"

        # List of months to iterate through
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        print("List of months:", months)

        # Identify the month and year (2025) in the calendar element
        try:
            # Locate the calendar element containing the month and year
            calendar_element = wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[contains(@class, 'calendar') or contains(@class, 'date-picker') or contains(@class, 'datepicker')]//*[contains(text(), '2025') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'january') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'february') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'march') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'april') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'may') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'june') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'july') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'august') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'september') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'october') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'november') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'december')]"
                ))
            )
            calendar_text = calendar_element.text.strip()
            print(f"Found calendar text in scheduling section: '{calendar_text}'")

            # Check for month and year 2025
            found_month = None
            for month in months:
                if month.lower() in calendar_text.lower() and "2025" in calendar_text:
                    found_month = month
                    print(f"Identified month and year in calendar: {month} 2025")
                    break

            if not found_month:
                print("No month matching 2025 found in the calendar element.")
        except Exception as e:
            print(f"Failed to locate calendar element with month and year: {str(e)}")
            try:
                # Alternative locator for calendar element
                calendar_element = wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "div[class*='calendar'] span, div[class*='date-picker'] span, div[class*='datepicker'] [aria-label*='month'], div[class*='datepicker'] [aria-label*='year']"
                    ))
                )
                calendar_text = calendar_element.text.strip()
                print(f"Found calendar text using alternative locator: '{calendar_text}'")

                # Check for month and year 2025
                found_month = None
                for month in months:
                    if month.lower() in calendar_text.lower() and "2025" in calendar_text:
                        found_month = month
                        print(f"Identified month and year in calendar: {month} 2025")
                        break

                if not found_month:
                    print("No month matching 2025 found with alternative locator.")
            except Exception as e2:
                print(f"Alternative locator for calendar element failed: {str(e2)}")
                # Continue despite failure to allow script to proceed

    except Exception as e:
        print(f"Failed to enable scheduling toggle: {str(e)}")
        try:
            scheduling_toggle = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label*='Schedule'] input[type='checkbox'], [data-testid*='schedule-toggle']"))
            )
            scheduling_toggle.click()
            print("Enabled scheduling using alternative locator.")
            time.sleep(2)

            # Locate "Active times" text
            try:
                active_times_text = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'active times')]"))
                )
                print("Located 'Active times' text in the scheduling section.")
            except Exception as e3:
                print(f"Failed to locate 'Active times' text: {str(e3)}")
                try:
                    active_times_text = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Active times'], div[class*='schedule'] span"))
                    )
                    print("Located 'Active times' text using alternative locator.")
                except Exception as e4:
                    print(f"Alternative locator for 'Active times' text failed: {str(e4)}")

            # Identify the month and year (2025) in the calendar element
            try:
                calendar_element = wait.until(
                    EC.presence_of_element_located((
                        By.XPATH, 
                        "//div[contains(@class, 'calendar') or contains(@class, 'date-picker') or contains(@class, 'datepicker')]//*[contains(text(), '2025') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'january') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'february') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'march') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'april') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'may') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'june') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'july') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'august') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'september') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'october') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'november') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'december')]"
                    ))
                )
                calendar_text = calendar_element.text.strip()
                print(f"Found calendar text in scheduling section: '{calendar_text}'")

                # Check for month and year 2025
                found_month = None
                for month in months:
                    if month.lower() in calendar_text.lower() and "2025" in calendar_text:
                        found_month = month
                        print(f"Identified month and year in calendar: {month} 2025")
                        break

                if not found_month:
                    print("No month matching 2025 found in the calendar element.")
            except Exception as e3:
                print(f"Failed to locate calendar element with month and year: {str(e3)}")
                try:
                    calendar_element = wait.until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            "div[class*='calendar'] span, div[class*='date-picker'] span, div[class*='datepicker'] [aria-label*='month'], div[class*='datepicker'] [aria-label*='year']"
                        ))
                    )
                    calendar_text = calendar_element.text.strip()
                    print(f"Found calendar text using alternative locator: '{calendar_text}'")

                    # Check for month and year 2025
                    found_month = None
                    for month in months:
                        if month.lower() in calendar_text.lower() and "2025" in calendar_text:
                            found_month = month
                            print(f"Identified month and year in calendar: {month} 2025")
                            break

                    if not found_month:
                        print("No month matching 2025 found with alternative locator.")
                except Exception as e4:
                    print(f"Alternative locator for calendar element failed: {str(e4)}")
                    # Continue despite failure

        except Exception as e2:
            print(f"Alternative locator for scheduling toggle failed: {str(e2)}")
            # Continue to allow script to proceed

def wait_for_command():
    """Wait for user input to proceed with the next command."""
    print("Browser is open with both Facebook and Business Manager tabs, currently on Business Manager tab. Waiting for your next command...")
    print("Type 'quit' to close the browser or enter any other command to continue.")
    while True:
        command = input("Enter command: ").strip().lower()
        if command == "quit":
            print("Received 'quit' command. Closing browser.")
            return False  # Signal to close the browser
        else:
            print(f"Received command: '{command}'. This script does not handle custom commands yet.")
            print("Please implement additional command handling or type 'quit' to close the browser.")
            # You can extend this to handle specific commands in the future

def operate(mode):
    # Close any existing Chrome instances to avoid conflicts
    print("Closing existing Chrome instances...")
    close_existing_chrome_instances()
    time.sleep(1)  # Brief pause to ensure processes are closed

    # Define the path to the Chrome user data directory
    user_data_dir = os.path.expanduser("~/.chrome-user-data")  # Adjust this path as needed
    profile_directory = "Default"  # Use "Default" or specific profile name if using multiple profiles

    # Set up Chrome options
    chrome_options = Options()
    if mode == "headless":
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
    else:
        chrome_options.add_argument("--start-maximized")  # Maximize window on launch in headed mode
    
    # Specify the user data directory and profile
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_directory}")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Suppress GCM errors

    # Initialize the WebDriver using ChromeDriverManager
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    # Create WebDriverWait instance
    wait = WebDriverWait(driver, 15)
    
    try:
        # Perform login for Facebook
        facebook_tab = driver.current_window_handle
        facebook(driver, wait)
        
        # Open a new tab for Business Manager
        driver.execute_script("window.open('');")
        business_tab = driver.window_handles[-1]
        driver.switch_to.window(business_tab)
        print("Opened new tab for Business Manager.")
        
        # Perform login and actions for Business Manager
        metaBusiness(driver, wait)
        
        # Enter text in the post creation dialog
        textstopost(driver, wait)
        
        # Enable scheduling toggle
        enable_scheduling(driver, wait)
        
        # Stay on the Business Manager tab and wait for commands
        driver.switch_to.window(business_tab)
        if wait_for_command() == False:
            print("Closing browser as per command.")
            driver.quit()
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Proceed to wait_for_command even if an error occurs
        driver.switch_to.window(driver.window_handles[-1])  # Ensure we're on the last tab
        if wait_for_command() == False:
            print("Closing browser as per command.")
            driver.quit()
            
    finally:
        # Only quit if not already closed in wait_for_command
        if driver.service.process:  # Check if driver is still active
            time.sleep(2)
            driver.quit()

if __name__ == "__main__":
    operate("headed")  # Using "headed" mode
    