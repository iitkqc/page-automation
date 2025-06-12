import os
import json
from datetime import datetime
import time # Import time for delays

# Change import from google_forms_reader to google_sheets_reader
from google_sheets_reader import get_sheets_client, get_latest_confessions_from_sheet, mark_confession_as_processed
from gemini_processor import moderate_and_shortlist_confession
from instagram_poster import generate_confession_image, upload_image_to_instagram_with_public_url, publish_instagram_post # Assuming you use the modified upload function

# --- Configuration (loaded from environment variables in GitHub Actions) ---
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
CREDENTIALS_JSON_BASE64 = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON_BASE64") # Base64 encoded JSON
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
PUBLIC_IMAGE_BASE_URL = os.getenv("PUBLIC_IMAGE_BASE_URL", "https://example.com/generated_images/")
PROCESSED_CONFESSIONS_FILE = "processed_confessions.json" # File to store processed IDs

def decode_credentials(base64_string, filename="credentials.json"):
    """Decodes a base64 string to a JSON file."""
    import base64
    decoded_bytes = base64.b64decode(base64_string)
    with open(filename, "wb") as f:
        f.write(decoded_bytes)
    return filename

def main():
    print(f"Starting confession automation at {datetime.now()}")

    # 1. Decode Google Sheets credentials
    credentials_file_path = None
    if CREDENTIALS_JSON_BASE64:
        try:
            credentials_file_path = decode_credentials(CREDENTIALS_JSON_BASE64, "google_sheets_credentials.json")
            print("Google Sheets credentials decoded.")
        except Exception as e:
            print(f"Error decoding Google Sheets credentials: {e}")
            return
    else:
        print("GOOGLE_SHEETS_CREDENTIALS_JSON_BASE64 not set. Sheets API may fail.")
        # Fallback for local testing, though not recommended for GH Actions
        credentials_file_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")

    # 2. Get Google Sheets client and fetch latest confessions
    if not SHEET_URL or not credentials_file_path:
        print("Missing Google Sheets configuration (SHEET_URL or credentials_file_path). Exiting.")
        return

    sheets_client = get_sheets_client(credentials_file_path)
    
    # Read confessions from the sheet, using the PROCESSED_CONFESSIONS_FILE to avoid duplicates
    new_confessions = get_latest_confessions_from_sheet(SHEET_URL, sheets_client, PROCESSED_CONFESSIONS_FILE)
    print(f"Found {len(new_confessions)} new confessions from sheet.")

    shortlisted_posts = []
    
    for confession in new_confessions:
        print(f"\nProcessing confession ID: {confession['id']} (Row: {confession['row_num']})")
        
        # 3. Moderate and shortlist using Gemini 1.5 Flash
        gemini_result = moderate_and_shortlist_confession(confession['text'])
        
        if gemini_result['is_safe']:
            print(f"Confession deemed SAFE. Sentiment: {gemini_result['sentiment']}")
            shortlisted_posts.append({
                'id': confession['id'],
                'text': confession['text'],
                'summary_caption': gemini_result['summary_caption'],
                'row_num': confession['row_num'] # Keep track of original row for marking
            })
            if len(shortlisted_posts) >= 8: # Stop after shortlisting 8 posts
                break
        else:
            print(f"Confession deemed UNSAFE: {gemini_result['rejection_reason']}")

    print(f"\nShortlisted {len(shortlisted_posts)} confessions for posting.")

    # 4. Schedule posts using Instagram Graph API
    for i, post_data in enumerate(shortlisted_posts):
        # Generate image locally
        image_filename = f"confession_{post_data['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        image_path = os.path.join("generated_images", image_filename)
        generate_confession_image(post_data['text'], image_path)

        # Construct the public URL for the image
        # This assumes your GitHub Pages setup will serve images from 'generated_images/'
        public_image_url = f"{PUBLIC_IMAGE_BASE_URL}{image_filename}"
        
        print(f"Attempting to upload and publish post {i+1}/{len(shortlisted_posts)}...")
        print(f"Public image URL assumed: {public_image_url}") # This needs to be a real URL after GH Pages deploy

        media_container_id = upload_image_to_instagram_with_public_url(public_image_url, post_data['summary_caption'])
        
        if media_container_id:
            print("Waiting a few seconds for media container to process...")
            time.sleep(10) # Give Instagram time to process the container
            if publish_instagram_post(media_container_id):
                print(f"Successfully posted confession ID: {post_data['id']} (Row: {post_data['row_num']}) to Instagram!")
                # Mark as processed in sheet and local file
                mark_confession_as_processed(SHEET_URL, sheets_client, post_data['id'], post_data['row_num'], PROCESSED_CONFESSIONS_FILE)
            else:
                print(f"Failed to publish post for confession ID: {post_data['id']}")
        else:
            print(f"Failed to create Instagram media container for confession ID: {post_data['id']}")

    print(f"Confession automation finished at {datetime.now()}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables for local testing
    main()