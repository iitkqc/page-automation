import os
import json
from datetime import datetime
import time # Import time for delays
import base64

# Change import from google_forms_reader to google_sheets_reader
from google_form_reader import get_sheets_client, get_latest_confessions_from_sheet, mark_confession_as_processed, get_updated_count
from gemini_processor import moderate_and_shortlist_confession, select_top_confessions
from insta_poster import schedule_instagram_post # Updated import to use the new function
from utils import delete_all_cloudinary_assets

# --- Configuration (loaded from environment variables in GitHub Actions) ---
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
CREDENTIALS_JSON_BASE64 = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE") # Base64 encoded JSON
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
PROCESSED_CONFESSIONS_FILE = "processed_confessions.json" # File to store processed IDs

def decode_credentials(base64_string, filename):
    """Decodes a base64 string to a JSON file."""
    decoded_bytes = base64.b64decode(base64_string)
    with open(filename, "wb") as f:
        f.write(decoded_bytes)
    return filename

def main():
    print(f"Starting confession automation at {datetime.now()}")

    # 1. Decode Google Sheets credentials
    credentials_file_path = None
    try:
        credentials_file_path = decode_credentials(CREDENTIALS_JSON_BASE64, "google_sheets_credentials.json")
        print("Google Sheets credentials decoded.")
    except Exception as e:
        print(f"Error decoding Google Sheets credentials: {e}")
        return

    # 2. Get Google Sheets client and fetch latest confessions
    if not SHEET_URL or not credentials_file_path:
        print("Missing Google Sheets configuration (SHEET_URL or credentials_file_path). Exiting.")
        return

    sheets_client = get_sheets_client(credentials_file_path)
    
    # Read confessions from the sheet, using the PROCESSED_CONFESSIONS_FILE to avoid duplicates
    new_confessions = get_latest_confessions_from_sheet(SHEET_URL, sheets_client, PROCESSED_CONFESSIONS_FILE)
    print(f"Found {len(new_confessions)} new confessions from sheet.")
    if not new_confessions:
        print("No new confessions found in the Google Sheet.")
        return

    shortlisted_posts = []
    
    for confession in new_confessions:
        print(f"\nProcessing confession ID: {confession[1]}")
        
        # 3. Moderate and shortlist using Gemini 1.5 Flash
        gemini_result = moderate_and_shortlist_confession(confession[2])
        
        if gemini_result['is_safe']:
            print(f"Confession deemed SAFE. Sentiment: {gemini_result['sentiment']}")
            shortlisted_posts.append({
                'id': confession[1],
                'text': gemini_result['original_text'],
                'summary_caption': gemini_result['summary_caption'],
                'row_num': confession[0], # Keep track of original row for marking
                'sentiment': gemini_result['sentiment']
            })
        else:
            print(f"Confession deemed UNSAFE: {gemini_result['rejection_reason']}")

    print(f"\nFound {len(shortlisted_posts)} safe confessions.")
    if not shortlisted_posts:
        print("No safe confessions found for posting.")
        return

  
    print("Selecting top 6 confessions based on creativity and potential reach...")
    shortlisted_posts = select_top_confessions(shortlisted_posts)
    print(f"Selected {len(shortlisted_posts)} top confessions for posting.")

    # 5. Schedule posts using Instagram Graph API
    for i, post_data in enumerate(shortlisted_posts):
        print(f"Attempting to schedule post {i+1}/{len(shortlisted_posts)}...")
        count = get_updated_count(SHEET_URL, sheets_client)
        
        # Use the new schedule_instagram_post function which handles image generation and posting
        if schedule_instagram_post(post_data, count):
            print(f"Successfully scheduled confession ID: {post_data['id']} to Instagram!")
            # Mark as processed in sheet with status 1 (success)
            mark_confession_as_processed(SHEET_URL, sheets_client, post_data['row_num'], 1)
        else:
            print(f"Failed to schedule post for confession ID: {post_data['id']}")
            # Mark as processed in sheet with status 0 (failed)
            mark_confession_as_processed(SHEET_URL, sheets_client, post_data['row_num'], 0)

    #mark unpublished rows to 0
    total_rows = [item[0] for item in new_confessions]
    posted_rows = [item.get("row_num") for item in shortlisted_posts]

    not_posted_rows = set(total_rows) - set(posted_rows)
    for row in not_posted_rows:
        mark_confession_as_processed(SHEET_URL, sheets_client, row, 0)
        print(f"Marked row {row} as NOT POSTED in Google Sheet.")

    print(f"Confession automation finished at {datetime.now()}")

    delete_all_cloudinary_assets()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables for local testing
    main()