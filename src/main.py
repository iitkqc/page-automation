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
        configured_post_limit = int(os.getenv("MAX_CONFESSION_PER_RUN", 2))
        self.max_confession_per_run = max(1, min(configured_post_limit, 2))
        self.total_confessions_to_choose_from = 5
        
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
        shortlisted_posts = []
        remaining_slots = self.max_confession_per_run

        if force_post_confessions:
            prioritized_force_posts = force_post_confessions[:remaining_slots]
            print(
                f"Found {len(force_post_confessions)} manual override confession(s). "
                f"Posting up to {len(prioritized_force_posts)} of them first this run."
            )
            self.prepare_force_posts(prioritized_force_posts)
            shortlisted_posts.extend(prioritized_force_posts)
            remaining_slots -= len(prioritized_force_posts)

        if remaining_slots > 0 and regular_confessions:
            if len(regular_confessions) >= self.total_confessions_to_choose_from:
                if not self.ensure_gemini_processor():
                    if shortlisted_posts:
                        print(
                            "Gemini setup failed while manual override posts are present, "
                            "so only the override rows will be posted."
                        )
                    else:
                        print("Gemini setup failed and there are no manual override posts to continue with.")
                        return
                else:
                    ai_candidates = regular_confessions[-self.total_confessions_to_choose_from:]
                    print(
                        f"Processing {len(ai_candidates)} regular confession(s) to fill "
                        f"{remaining_slots} remaining post slot(s)."
                    )

                    ai_selected_posts = self.moderate_confessions(ai_candidates)

                    if ai_selected_posts:
                        print(
                            f"Selecting top {remaining_slots} confession(s) "
                            "based on creativity and potential reach..."
                        )
                        ai_selected_posts = self.gemini_processor.select_top_confessions(
                            ai_selected_posts,
                            max_count=remaining_slots
                        )
                        print(f"Selected {len(ai_selected_posts)} AI confession(s) for posting.")
                        shortlisted_posts.extend(ai_selected_posts)
                    else:
                        print("No safe AI-reviewed confessions found for posting.")
            else:
                print(
                    f"Found only {len(regular_confessions)} regular confession(s). "
                    f"Need at least {self.total_confessions_to_choose_from} for AI shortlisting, "
                    "so leaving those rows untouched for a later run."
                )

        shortlisted_posts = shortlisted_posts[:self.max_confession_per_run]
        ai_rejection_story_posted = False

        if not shortlisted_posts:
            if ai_candidates:
                ai_rejection_story_posted = self.post_ai_rejection_summary_story(ai_candidates)
            print("No confessions ready for posting.")
            self.instagram_poster.delete_all_assets()
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

        if ai_candidates and not ai_rejection_story_posted:
            self.post_ai_rejection_summary_story(ai_candidates)

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
                confession.rejection_reason = "It felt too brief and underdeveloped for the feed."
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
                confession.rejection_reason = ""
                shortlisted_confessions.append(confession)
            else:
                confession.rejection_reason = (
                    gemini_result.rejection_reason.strip()
                    or "It did not feel safe enough for a public campus feed."
                )
                print(f"Confession deemed UNSAFE: {gemini_result.rejection_reason}")

        print(f"\nFound {len(shortlisted_confessions)} safe confessions.")
        return shortlisted_confessions

    def extract_story_rejection_angle(self, reason: str) -> tuple[str, str, bool] | None:
        """Map a rejection reason to a short, audience-friendly story angle."""
        cleaned_reason = " ".join((reason or "").lower().split())
        if not cleaned_reason:
            return None

        if any(keyword in cleaned_reason for keyword in ("allegation", "misconduct", "accus", "faculty member", "professor", "prof ")):
            return ("serious_allegations", "serious allegations", True)
        if any(keyword in cleaned_reason for keyword in ("manipulative", "coerc", "exploit", "toxic", "unhealthy relationship", "relationship dynamics")):
            return ("manipulative_dynamics", "manipulative relationship games", True)
        if any(keyword in cleaned_reason for keyword in ("personal", "private", "identif", "revealing", "doxx")):
            return ("too_revealing", "details too revealing for a public page", True)
        if any(keyword in cleaned_reason for keyword in ("harass", "hate", "abuse", "unsafe", "stalk", "threat", "violent", "danger", "harmful language", "negativity")):
            return ("safety_lines", "language that crosses safety lines", True)
        if any(keyword in cleaned_reason for keyword in ("sexual", "explicit", "nsfw")):
            return ("too_explicit", "stuff too explicit for the page", True)
        if any(keyword in cleaned_reason for keyword in ("short", "brief", "underdeveloped", "generic", "weak", "hook", "specific", "detail", "flat", "repet", "similar", "duplicate")):
            return ("too_thin", "stories too thin to stand out", False)
        if any(keyword in cleaned_reason for keyword in ("campus-native", "campus native", "iitk", "broad campus")):
            return ("not_iitk_enough", "posts that do not feel rooted enough in IITK life", False)
        if "niche" in cleaned_reason:
            return ("too_niche", "stories too niche for the wider page", False)
        if any(keyword in cleaned_reason for keyword in ("advice", "forum")):
            return ("advice_post", "advice-type posts better suited elsewhere", False)

        return None

    def join_story_angles(self, angles: List[str]) -> str:
        """Join short story angles into one natural phrase."""
        if not angles:
            return ""
        if len(angles) == 1:
            return angles[0]
        if len(angles) == 2:
            return f"{angles[0]} or {angles[1]}"
        return f"{angles[0]}, {angles[1]}, or {angles[2]}"

    def build_ai_rejection_story_text(self, ai_candidates: List[Confession]) -> str:
        """Create a concise, audience-friendly story summary for selected rejection angles."""
        rejected_reasons = [
            confession.rejection_reason
            for confession in ai_candidates
            if (confession.rejection_reason or "").strip()
        ]
        if len(rejected_reasons) < 2:
            return ""

        engaging_angles = []
        fallback_angles = []
        seen_keys = set()

        for reason in rejected_reasons:
            angle = self.extract_story_rejection_angle(reason or "")
            if not angle:
                continue

            angle_key, angle_text, is_engaging = angle
            if angle_key in seen_keys:
                continue

            seen_keys.add(angle_key)
            if is_engaging:
                engaging_angles.append(angle_text)
            else:
                fallback_angles.append(angle_text)

        if not engaging_angles:
            return ""

        selected_angles = engaging_angles[:2]
        if len(selected_angles) < 2 and fallback_angles:
            selected_angles.append(fallback_angles[0])

        combined_angles = self.join_story_angles(selected_angles[:2])
        if not combined_angles:
            return ""

        return (
            "What quietly gets a confession skipped?\n\n"
            f"Usually things like {combined_angles}."
        )

    def post_ai_rejection_summary_story(self, ai_candidates: List[Confession]) -> bool:
        """Best-effort story share summarizing why some AI-reviewed confessions were skipped."""
        story_text = self.build_ai_rejection_story_text(ai_candidates)
        if not story_text:
            print("Skipping AI rejection summary story because there was no strong audience-facing angle.")
            return False

        print("Posting AI rejection summary story...")
        return self.instagram_poster.share_text_story(
            story_text,
            public_id_suffix=f"ai_rejection_summary_{int(datetime.now().timestamp())}",
        )

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
