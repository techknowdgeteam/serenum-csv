import connectwithinfinitydb as db
import json
import os
from datetime import datetime
import time
from selenium.webdriver.common.by import By
import re
from datetime import datetime, timezone
from webdriver_manager.chrome import ChromeDriverManager
   
def fetch_jpgsvault_urls():
    """
    Modified function to fetch all_urls data from jpgsvault_table
    Properly handles JSON array format from the database
    """
    import json as json_module  # Rename to avoid conflict with your json variable
    
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
        
        # Save to file
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Data saved to {OUTPUT_FILE}")
        
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

if __name__ == "__main__":
    fetch_jpgsvault_urls()
    