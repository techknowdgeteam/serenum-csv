from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import os
import io

# Define the scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_drive():
    """Authenticate and create a Google Drive service object."""
    creds = None
    # Load credentials if they exist
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If no valid credentials, prompt user to log in
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def download_photos(folder_id=None, download_path='downloaded_photos'):
    """Download photos from Google Drive. Optionally specify a folder ID."""
    # Create download directory if it doesn't exist
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    # Authenticate and build the Drive service
    service = authenticate_drive()

    # Query to list files (filter by folder or all files)
    query = "mimeType contains 'image/'"  # Filter for image files
    if folder_id:
        query += f" and '{folder_id}' in parents"

    # List files
    results = service.files().list(
        q=query,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()
    items = results.get('files', [])

    if not items:
        print("No photos found.")
        return

    # Download each file
    for item in items:
        file_id = item['id']
        file_name = item['name']
        print(f"Downloading {file_name}...")
        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join(download_path, file_name)
        
        # Download the file
        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}% complete.")
    
    print("Download complete!")

# Example usage
# Replace 'your_folder_id' with the ID of your Google Drive folder (optional)
# To find folder_id, open the folder in Google Drive; the ID is in the URL: https://drive.google.com/drive/folders/FOLDER_ID
download_photos(folder_id='your_folder_id', download_path='my_photos')