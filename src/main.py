import os
from datetime import datetime

# Import the new class-based modules
from google_form_reader import GoogleFormReader
from gemini_processor import GeminiProcessor
from insta_poster import InstagramPoster

class ConfessionAutomation:
    def __init__(self):
        """Initialize the confession automation system."""
        self.sheet_url = os.getenv("GOOGLE_SHEET_URL")
        self.credentials_json_base64 = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
        self.instagram_page_id = os.getenv("INSTAGRAM_PAGE_ID")
        self.processed_confessions_file = "processed_confessions.json"
        self.max_confession_per_run = int(os.getenv("MAX_CONFESSION_PER_RUN", 4))
        
        # Initialize components
        self.google_reader = None
        self.gemini_processor = None
        self.instagram_poster = None

    def setup_components(self):
        """Initialize all the required components."""
        try:
            # Initialize Google Form Reader
            self.google_reader = GoogleFormReader(self.sheet_url)
            
            # Initialize Gemini Processor
            self.gemini_processor = GeminiProcessor()
            
            # Initialize Instagram Poster
            self.instagram_poster = InstagramPoster()
            
            return True
            
        except Exception as e:
            print(f"Error setting up components: {e}")
            return False

    def setup_instagram_token(self):
        """Set up Instagram access token and refresh if needed."""
        token = self.google_reader.get_instagram_access_token()
        if not token:
            print("No Instagram access token found. Attempting to refresh...")
            return False
        
        os.environ['INSTAGRAM_ACCESS_TOKEN'] = token
        self.instagram_poster.access_token = token

        if datetime.now().day == 28:
            print("Refreshing Instagram access token...")
            new_token = self.instagram_poster.refresh_instagram_access_token()
            if new_token:
                self.google_reader.set_instagram_access_token(new_token)
                os.environ['INSTAGRAM_ACCESS_TOKEN'] = new_token
                self.instagram_poster.access_token = new_token
                print("Instagram access token refreshed successfully.")
                return True
            else:
                print("Failed to refresh Instagram access token. Exiting.")
                return False
        
        return True

    def process_confessions(self):
        """Main method to process confessions from start to finish."""
        print(f"Starting confession automation at {datetime.now()}")

        # Setup components
        if not self.setup_components():
            print("Failed to setup components. Exiting.")
            return

        # Setup Instagram token
        if not self.setup_instagram_token():
            print("Failed to setup Instagram token. Exiting.")
            return

        if not os.getenv('INSTAGRAM_ACCESS_TOKEN'):
            print("No Instagram access token found. Please set it in the Google Sheet.")
            return
        
        # Read confessions from the sheet
        new_confessions = self.google_reader.get_latest_confessions_from_sheet(
            self.processed_confessions_file
        )
        print(f"Found {len(new_confessions)} new confessions from sheet.")
        new_confessions = new_confessions[-15:]  # Limit to last 15 confessions for rate limiting
        print(f"Processing {len(new_confessions)} confessions for moderation.")

        if not new_confessions:
            print("No new confessions found in the Google Sheet.")
            return

        # Process and moderate confessions
        shortlisted_posts = self.moderate_confessions(new_confessions)
        
        if not shortlisted_posts:
            print("No safe confessions found for posting.")
            return

        # Select top confessions
        print(f"Selecting top {self.max_confession_per_run} confessions based on creativity and potential reach...")
        shortlisted_posts = self.gemini_processor.select_top_confessions(
            shortlisted_posts, 
            max_count=self.max_confession_per_run
        )
        print(f"Selected {len(shortlisted_posts)} top confessions for posting.")

        # Schedule posts
        self.schedule_posts(shortlisted_posts, new_confessions)

        # Cleanup
        self.instagram_poster.delete_all_assets()
        print(f"Confession automation finished at {datetime.now()}")

    def moderate_confessions(self, new_confessions):
        """Moderate confessions using Gemini and return safe ones."""
        shortlisted_posts = []
        
        for confession in new_confessions:
            print(f"\nProcessing confession ID: {confession[1]}")
            
            # Moderate and shortlist using Gemini
            gemini_result = self.gemini_processor.moderate_and_shortlist_confession(confession[2])
            
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
        return shortlisted_posts

    def schedule_posts(self, shortlisted_posts, new_confessions):
        """Schedule posts using Instagram Graph API."""
        for i, post_data in enumerate(shortlisted_posts):
            print(f"Attempting to schedule post {i+1}/{len(shortlisted_posts)}...")
            count = self.google_reader.get_count()
            
            # Use the Instagram poster to schedule the post
            if self.instagram_poster.schedule_instagram_post(post_data, count + 1):
                print(f"Successfully scheduled confession ID: {post_data['id']} to Instagram!")
                # Mark as processed in sheet with status 1 (success)
                self.google_reader.increment_count()
                self.google_reader.mark_confession_as_processed(post_data['row_num'], 1)
            else:
                print(f"Failed to schedule post for confession ID: {post_data['id']}")
                # Mark as processed in sheet with status 0 (failed)
                self.google_reader.mark_confession_as_processed(post_data['row_num'], 0)

        # Mark unpublished rows to 0
        total_rows = [item[0] for item in new_confessions]
        posted_rows = [item.get("row_num") for item in shortlisted_posts]

        not_posted_rows = set(total_rows) - set(posted_rows)
        for row in not_posted_rows:
            self.google_reader.mark_confession_as_processed(row, 0)
            print(f"Marked row {row} as NOT POSTED in Google Sheet.")

def main():
    """Main function to run the confession automation."""
    automation = ConfessionAutomation()
    automation.process_confessions()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables for local testing
    main()