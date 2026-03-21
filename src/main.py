import os
from datetime import datetime

# Import the new class-based modules
from google_form_reader import GoogleFormReader
from gemini_processor import GeminiProcessor
from insta_poster import InstagramPoster
from model import Confession, ManualPostEnhancementResponse, ModerationResponse
from typing import List

class ConfessionAutomation:
    def __init__(self):
        """Initialize the confession automation system."""
        self.sheet_url = os.getenv("GOOGLE_SHEET_URL")
        self.credentials_json_base64 = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
        self.instagram_page_id = os.getenv("INSTAGRAM_PAGE_ID")
        self.max_confession_per_run = int(os.getenv("MAX_CONFESSION_PER_RUN", 4))
        self.total_confessions_to_choose_from = 5
        self.manual_post_limit_per_run = 5
        
        # Initialize components
        self.google_reader = None
        self.gemini_processor = None
        self.instagram_poster = None

    def setup_components(self):
        """Initialize all the required components."""
        try:
            # Initialize Google Form Reader
            self.google_reader = GoogleFormReader(self.sheet_url)

            # Initialize Instagram Poster
            self.instagram_poster = InstagramPoster()
            self.gemini_processor = None
            
            return True
            
        except Exception as e:
            print(f"Error setting up components: {e}")
            return False

    def ensure_gemini_processor(self) -> bool:
        """Lazily initialize Gemini so manual override posts do not depend on it."""
        if self.gemini_processor is not None:
            return True

        try:
            self.gemini_processor = GeminiProcessor()
            return True
        except Exception as e:
            print(f"Error setting up Gemini processor: {e}")
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
        new_confessions = self.google_reader.get_latest_confessions_from_sheet()
        print(f"Found {len(new_confessions)} new confessions from sheet.")

        if not new_confessions:
            print("No new confessions found in the Google Sheet.")
            return

        force_post_confessions = [item for item in new_confessions if item.force_post]
        regular_confessions = [item for item in new_confessions if not item.force_post]
        ai_candidates = []
        ai_selected_posts = []

        if force_post_confessions:
            if len(force_post_confessions) > 2:
                prioritized_force_posts = force_post_confessions[:self.manual_post_limit_per_run]
                print(
                    f"Found {len(force_post_confessions)} manual override confession(s). "
                    f"Posting up to {self.manual_post_limit_per_run} of them this run and skipping AI selection."
                )
                self.prepare_force_posts(prioritized_force_posts)
                shortlisted_posts = prioritized_force_posts
            else:
                print(
                    f"Found {len(force_post_confessions)} manual override confession(s). "
                    "Posting them first and also running the normal AI selection flow this run."
                )
                self.prepare_force_posts(force_post_confessions)
                shortlisted_posts = force_post_confessions

                if len(regular_confessions) >= self.total_confessions_to_choose_from:
                    if not self.ensure_gemini_processor():
                        print("Gemini setup failed while manual override posts are present, so only the override rows will be posted.")
                    else:
                        ai_candidates = regular_confessions[-self.total_confessions_to_choose_from:]
                        print(f"Processing {len(ai_candidates)} confessions for moderation.")

                        ai_selected_posts = self.moderate_confessions(ai_candidates)

                        if ai_selected_posts:
                            print(
                                f"Selecting top {self.max_confession_per_run} confessions "
                                "based on creativity and potential reach..."
                            )
                            ai_selected_posts = self.gemini_processor.select_top_confessions(
                                ai_selected_posts,
                                max_count=self.max_confession_per_run
                            )
                            print(f"Selected {len(ai_selected_posts)} top confessions for posting.")
                            shortlisted_posts.extend(ai_selected_posts)
                        else:
                            print("No safe AI-reviewed confessions found for posting.")
                elif regular_confessions:
                    print(
                        f"Found only {len(regular_confessions)} regular confession(s). "
                        f"Need at least {self.total_confessions_to_choose_from} for AI shortlisting, "
                        "so only the manual override rows will be posted this run."
                    )
        elif len(regular_confessions) >= self.total_confessions_to_choose_from:
            if not self.ensure_gemini_processor():
                print("Gemini setup failed and there are no manual override posts to continue with.")
                return
            else:
                ai_candidates = regular_confessions[-self.total_confessions_to_choose_from:]
                print(f"Processing {len(ai_candidates)} confessions for moderation.")

                ai_selected_posts = self.moderate_confessions(ai_candidates)

                if ai_selected_posts:
                    print(
                        f"Selecting top {self.max_confession_per_run} confessions "
                        "based on creativity and potential reach..."
                    )
                    ai_selected_posts = self.gemini_processor.select_top_confessions(
                        ai_selected_posts,
                        max_count=self.max_confession_per_run
                    )
                    print(f"Selected {len(ai_selected_posts)} top confessions for posting.")
                else:
                    print("No safe AI-reviewed confessions found for posting.")
            shortlisted_posts = ai_selected_posts
        elif regular_confessions:
            print(
                f"Found only {len(regular_confessions)} regular confession(s). "
                f"Need at least {self.total_confessions_to_choose_from} for AI shortlisting, "
                "so leaving them untouched for a later run."
            )
            shortlisted_posts = []
        else:
            shortlisted_posts = []

        if not shortlisted_posts:
            print("No confessions ready for posting.")
            return

        # Schedule posts and track which ones were successfully scheduled
        attempted_rows = self.schedule_posts(shortlisted_posts)

        # Only mark AI-reviewed confessions as 0 if the system processed at least one post.
        # Manual override confessions are never marked as rejected here.
        if attempted_rows:
            ai_candidate_rows = [item.row_num for item in ai_candidates]
            ai_selected_rows = [item.row_num for item in ai_selected_posts]
            rejected_rows = set(ai_candidate_rows) - set(ai_selected_rows)
            for row in rejected_rows:
                self.google_reader.mark_confession_as_processed(row, 0)
                print(f"Marked row {row} as NOT POSTED (rejected during selection) in Google Sheet.")
        else:
            print("No posts were attempted. System may have failed. Not marking confessions as processed.")

        # Cleanup
        self.instagram_poster.delete_all_assets()
        print(f"Confession automation finished at {datetime.now()}")

    def prepare_force_posts(self, confessions: List[Confession]) -> None:
        """Populate post metadata for manual override posts without moderation gating."""
        gemini_ready = self.ensure_gemini_processor()

        for confession in confessions:
            confession.summary_caption = ""
            confession.sentiment = confession.sentiment or "Neutral"
            confession.category = confession.category or "campus_life"
            confession.sigma_reply = ""
            confession.pinned_comments = None
            confession.story_share_candidate = False

            if not gemini_ready:
                continue

            try:
                result: ManualPostEnhancementResponse = self.gemini_processor.enrich_manual_post(confession.text)
                confession.summary_caption = result.summary_caption
                confession.sentiment = result.sentiment
                confession.category = result.category
                confession.sigma_reply = result.admin_reply
                confession.pinned_comments = {
                    "funny": result.funny_pinned_comment,
                    "empathetic": result.empathetic_pinned_comment,
                    "discussion_bait": result.discussion_pinned_comment,
                }
                confession.story_share_candidate = result.story_share_candidate
            except Exception as e:
                print(
                    f"Manual post enrichment failed for confession ID {confession.timestamp}: {e}. "
                    "Continuing with fallback caption/comment defaults."
                )

    def moderate_confessions(self, new_confessions: List[Confession]) -> List[Confession]:
        """Moderate confessions using Gemini and return safe ones."""
        shortlisted_confessions = []
        
        for confession in new_confessions:
            print(f"\nProcessing confession ID: {confession.timestamp}")

            if len(confession.text) < 60:
                print(f"Confession ID {confession.timestamp} is too short to process. Skipping.")
                continue
            
            # Moderate and shortlist using Gemini
            gemini_result: ModerationResponse = self.gemini_processor.moderate_and_shortlist_confession(confession.text)

            
            if gemini_result.is_safe:
                print(
                    f"Confession deemed SAFE. Sentiment: {gemini_result.sentiment}. "
                    f"Category: {gemini_result.category}. "
                    f"Story share: {'yes' if gemini_result.story_share_candidate else 'no'}"
                )
                confession.sentiment = gemini_result.sentiment
                confession.category = gemini_result.category
                confession.summary_caption = gemini_result.summary_caption
                confession.story_share_candidate = gemini_result.story_share_candidate
                shortlisted_confessions.append(confession)
            else:
                print(f"Confession deemed UNSAFE: {gemini_result.rejection_reason}")

        print(f"\nFound {len(shortlisted_confessions)} safe confessions.")
        return shortlisted_confessions

    def schedule_posts(self, shortlisted_posts: List[Confession]) -> set:
        """
        Schedule posts using Instagram Graph API.
        Returns a set of row numbers that were successfully scheduled.
        """
        attempted_rows = set()
        
        for i, post_data in enumerate(shortlisted_posts):
            print(f"Attempting to schedule post {i+1}/{len(shortlisted_posts)}...")
            count = self.google_reader.get_count()
            post_data.count = count + 1
            
            try:
                # Use the Instagram poster to schedule the post
                if self.instagram_poster.schedule_instagram_post(post_data):
                    print(f"Successfully scheduled confession ID: {post_data.timestamp} to Instagram!")
                    # Mark as processed in sheet with status 1 (success)
                    self.google_reader.increment_count()
                    self.google_reader.mark_confession_as_processed(
                        post_data.row_num,
                        1,
                        clear_manual_post=post_data.force_post,
                    )
                    attempted_rows.add(post_data.row_num)
                else:
                    print(f"Failed to schedule post for confession ID: {post_data.timestamp}")
                    print(
                        f"Leaving status unchanged for row {post_data.row_num} so it can be retried later."
                    )
            except Exception as e:
                print(f"Error scheduling post for confession ID: {post_data.timestamp}: {e}")
                print(
                    f"Leaving status unchanged for row {post_data.row_num} because scheduling did not complete."
                )
        
        return attempted_rows        

def main():
    """Main function to run the confession automation."""
    automation = ConfessionAutomation()
    automation.process_confessions()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables for local testing
    main()
