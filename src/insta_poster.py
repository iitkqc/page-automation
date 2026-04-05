import requests
import os
import time
import cloudinary
import cloudinary.api
from cloudinary.exceptions import Error
import cloudinary.uploader
from typing import List
from model import Confession
from confession_image_generator import ConfessionImageGenerator
from reel_generator import FfmpegReelGenerator

# --- Configuration ---
FB_GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
MAX_CONFESSION_STORY_SHARES_PER_RUN = 1
MAX_SUMMARY_STORY_SLIDES = 1

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


class InstagramPoster:
    def __init__(self):
        """Initialize Instagram Poster with configuration."""
        self.fb_graph_api_base = FB_GRAPH_API_BASE
        self.instagram_page_id = INSTAGRAM_PAGE_ID
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.confession_story_shares_posted = 0
        
        # if not self.access_token:
        #     print("Warning: INSTAGRAM_ACCESS_TOKEN not set.")

    def should_retry_publish(self, response: requests.Response | None) -> bool:
        """Return True when Instagram says the media is still processing."""
        if response is None:
            return False

        try:
            payload = response.json()
        except ValueError:
            return False

        error = payload.get("error", {})
        message = " ".join(
            str(part or "")
            for part in (
                error.get("message"),
                error.get("error_user_title"),
                error.get("error_user_msg"),
            )
        ).lower()

        return error.get("code") == 9007 or "not ready for publishing" in message or "media id is not available" in message

    def upload_image_to_cloudinary(self, image_path: str, public_id: str) -> str:
        """Upload a single image to Cloudinary and return its URL."""
        try:
            response = cloudinary.uploader.upload(
                image_path,
                public_id=public_id,
                overwrite=True,
                resource_type="image"
            )
            secure_url = response["secure_url"]
            print(f"Uploaded image to Cloudinary: {secure_url}")
            return secure_url
        except Exception as e:
            print(f"Error uploading image to Cloudinary: {e}")
            return ""

    def upload_images_to_cloudinary(self, image_paths: List[str], row_num: int) -> List[str]:
        """Upload multiple images to Cloudinary and return URLs"""
        public_urls = []
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                public_id = f"confessions/confession_{row_num}_slide_{i}"
                response = cloudinary.uploader.upload(
                    image_path,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image"
                )
                public_urls.append(response['secure_url'])
                print(f"Uploaded slide {i} to Cloudinary: {response['secure_url']}")
            except Exception as e:
                print(f"Error uploading slide {i} to Cloudinary: {e}")
                return []
        
        return public_urls

    def upload_video_to_cloudinary(self, video_path: str, row_num: int) -> str:
        """Upload video to Cloudinary and return URL"""
        try:
            public_id = f"confessions/confession_{row_num}_reel"
            response = cloudinary.uploader.upload(
                video_path,
                public_id=public_id,
                overwrite=True,
                resource_type="video"
            )
            print(f"Uploaded reel to Cloudinary: {response['secure_url']}")
            return response['secure_url']
        except Exception as e:
            print(f"Error uploading reel to Cloudinary: {e}")
            return ""

    def build_post_caption(self, caption: str | None, sigma_reply: str | None) -> str:
        """Build the final caption string without leaking None values into the post."""
        hashtag_block = (
            "#IITKQuickConfessions #IITKConfessions #confession "
            "#iitk #iitkanpur #iit #jee #jeeadvanced #jeemains"
        )
        admin_reply = (sigma_reply or "").strip()
        clean_caption = (caption or "").strip()

        if admin_reply:
            return f"Admin reply: {admin_reply}\n\n{hashtag_block}"
        if clean_caption:
            return f"{clean_caption}\n\n{hashtag_block}"
        return hashtag_block

    def create_instagram_carousel(self, image_urls: List[str], caption: str | None, sigma_reply: str | None) -> str:
        """Create Instagram carousel post"""
        if not self.instagram_page_id or not self.access_token:
            print("Instagram API credentials not set.")
            return ""
        
        # Carousel requires at least 2 images
        if len(image_urls) < 2:
            print("Carousel requires at least 2 images.")
            return ""
        
        # Create carousel container
        url = f"{self.fb_graph_api_base}/me/media"
        
        # First, create media objects for each image
        media_ids = []
        for image_url in image_urls:

            headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
            }
            params = {
                'image_url': image_url,
                'caption': caption,
                'is_carousel_item': 'true',
            }
            
            try:
                response = requests.post(url, headers=headers, params=params)
                response.raise_for_status()
                media_id = response.json().get('id')
                media_ids.append(media_id)
                print(f"Created carousel item")
            except requests.exceptions.RequestException as e:
                print(f"Error creating carousel item: {e}")
                return ""
        
        # Create carousel container
        carousel_params = {
            'media_type': 'CAROUSEL',
            'children': ','.join(media_ids),
            'caption': self.build_post_caption(caption, sigma_reply),
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, params=carousel_params)
            response.raise_for_status()
            carousel_id = response.json().get('id')
            print(f"Created carousel container")
            return carousel_id
        except requests.exceptions.RequestException as e:
            print(f"Error creating carousel container: {e}")
            print(f"Response: {response.text}")
            return ""

    def create_instagram_reel(self, video_url: str, caption: str | None, sigma_reply: str | None) -> str:
        """Create Instagram reel post"""
        if not self.instagram_page_id or not self.access_token:
            print("Instagram API credentials not set.")
            return ""
        
        url = f"{self.fb_graph_api_base}/{self.instagram_page_id}/media"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        data = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': self.build_post_caption(caption, sigma_reply),
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            media_container_id = response.json().get('id', '')
            print(f"Reel media container created: {media_container_id}")
            return media_container_id
        except requests.exceptions.RequestException as e:
            print(f"Error creating reel media container: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return ""

    def create_instagram_story(self, image_url: str) -> str:
        """Create an Instagram story container from an image URL."""
        if not self.instagram_page_id or not self.access_token:
            print("Instagram API credentials not set.")
            return ""

        url = f"{self.fb_graph_api_base}/{self.instagram_page_id}/media"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "image_url": image_url,
            "media_type": "STORIES",
        }

        try:
            response = requests.post(url, headers=headers, params=params)
            response.raise_for_status()
            media_container_id = response.json().get("id", "")
            print(f"Story media container created: {media_container_id}")
            return media_container_id
        except requests.exceptions.RequestException as e:
            print(f"Error creating story media container: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return ""

    def publish_instagram_post(self, media_container_id: str, retry_delays: List[int] | None = None) -> str:
        """Publish the media container to Instagram and return the media ID."""
        if not self.instagram_page_id or not self.access_token:
            return ""

        url = f"{self.fb_graph_api_base}/{self.instagram_page_id}/media_publish"
        params = {
            'creation_id': media_container_id,
            'access_token': self.access_token
        }
        retry_schedule = retry_delays or []

        for attempt in range(len(retry_schedule) + 1):
            try:
                response = requests.post(url, params=params)
                response.raise_for_status()
                post_id = response.json().get('id')
                print(f"Successfully published post with ID: {post_id}")
                return post_id or ""
            except requests.exceptions.RequestException as e:
                response = getattr(e, "response", None)
                print(f"Error publishing post: {e}")
                if response is not None:
                    print(f"Response: {response.text}")

                if attempt < len(retry_schedule) and self.should_retry_publish(response):
                    wait_seconds = retry_schedule[attempt]
                    print(
                        f"Media is still processing. Retrying publish in {wait_seconds} seconds "
                        f"(attempt {attempt + 2}/{len(retry_schedule) + 1})..."
                    )
                    time.sleep(wait_seconds)
                    continue

                return ""

    def pick_generated_comment(self, confession: Confession) -> str:
        """Pick one generated engagement comment to post."""
        if not confession.pinned_comments:
            return ""

        ordered_comments = [
            confession.pinned_comments.get("discussion_bait", ""),
            confession.pinned_comments.get("funny", ""),
            confession.pinned_comments.get("empathetic", ""),
        ]

        for comment in ordered_comments:
            cleaned = (comment or "").strip()
            if not cleaned:
                continue
            return cleaned

        return ""

    def post_instagram_comment(self, media_id: str, message: str) -> bool:
        """Post a comment on a published Instagram media object."""
        if not media_id or not self.access_token:
            return False

        url = f"{self.fb_graph_api_base}/{media_id}/comments"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "message": message,
            "access_token": self.access_token,
        }

        try:
            response = requests.post(url, headers=headers, params=params)
            response.raise_for_status()
            comment_id = response.json().get("id", "")
            print(f"Posted comment on media {media_id}: {comment_id or 'created'}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error posting comment on media {media_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False

    def post_generated_comments(self, media_id: str, confession: Confession) -> None:
        """Post one generated comment after publish without failing the main post."""
        comment = self.pick_generated_comment(confession)
        if not comment:
            return

        print(f"Posting generated comment for confession {confession.timestamp}...")
        time.sleep(3)
        success = self.post_instagram_comment(media_id, comment)
        if not success:
            print("Generated comment failed to post.")

    def share_confession_to_story(self, confession: Confession, generator: ConfessionImageGenerator, story_text: str | None = None) -> None:
        """Best-effort story share for confessions flagged as socially resonant."""
        if not confession.story_share_candidate:
            return
        if self.confession_story_shares_posted >= MAX_CONFESSION_STORY_SHARES_PER_RUN:
            print(
                f"Skipping story share for confession {confession.timestamp} because the per-run "
                "story limit has already been reached."
            )
            return

        print(f"Confession {confession.timestamp} flagged for story share. Creating story...")
        story_image_path = ""

        try:
            story_image_path = generator.create_story_image(story_text)
            if not story_image_path:
                print("Failed to generate story image.")
                return

            story_url = self.upload_image_to_cloudinary(
                story_image_path,
                f"confessions/confession_{confession.row_num}_story"
            )
            if not story_url:
                print("Failed to upload story image to Cloudinary.")
                return

            media_container_id = self.create_instagram_story(story_url)
            if not media_container_id:
                return

            print("Waiting for Instagram to process story media...")
            time.sleep(10)
            story_id = self.publish_instagram_post(media_container_id, retry_delays=[5, 10, 15])
            if story_id:
                self.confession_story_shares_posted += 1
                print(f"Successfully shared confession {confession.timestamp} to Instagram Story!")
        except Exception as e:
            print(f"Story share failed for confession {confession.timestamp}: {e}")
        finally:
            if story_image_path:
                try:
                    os.remove(story_image_path)
                except OSError:
                    pass

    def share_text_story(self, story_text: str, public_id_suffix: str) -> bool:
        """Post a best-effort story from standalone text."""
        cleaned_story_text = (story_text or "").strip()
        if not cleaned_story_text:
            return False

        story_confession = Confession(
            timestamp=str(int(time.time())),
            row_num=0,
            text=cleaned_story_text,
            sentiment="Neutral",
            category="campus_life",
        )
        generator = ConfessionImageGenerator(story_confession)
        story_slides = self.split_story_text_into_slides(
            cleaned_story_text,
            max_slides=MAX_SUMMARY_STORY_SLIDES,
        )
        all_slides_shared = True

        for index, slide_text in enumerate(story_slides, start=1):
            story_image_path = ""

            try:
                story_image_path = generator.create_story_image(
                    slide_text,
                    footer_text="",
                    max_chars=380,
                    start_size=52,
                    min_size=28,
                    text_top=250,
                    bottom_padding=120,
                )
                if not story_image_path:
                    print("Failed to generate summary story image.")
                    return False

                story_url = self.upload_image_to_cloudinary(
                    story_image_path,
                    f"confessions/{public_id_suffix}_slide_{index}"
                )
                if not story_url:
                    print("Failed to upload summary story image to Cloudinary.")
                    return False

                media_container_id = self.create_instagram_story(story_url)
                if not media_container_id:
                    return False

                print(f"Waiting for Instagram to process summary story media {index}/{len(story_slides)}...")
                time.sleep(10)
                story_id = self.publish_instagram_post(media_container_id, retry_delays=[5, 10, 15])
                if not story_id:
                    all_slides_shared = False
                    break
            except Exception as e:
                print(f"Summary story share failed: {e}")
                all_slides_shared = False
                break
            finally:
                if story_image_path:
                    try:
                        os.remove(story_image_path)
                    except OSError:
                        pass

        if all_slides_shared:
            print("Successfully shared summary story to Instagram!")
        return all_slides_shared

    def split_story_text_into_slides(self, story_text: str, max_chars_per_slide: int = 330, max_slides: int = 1) -> List[str]:
        """Split longer review-story text into a small number of readable story slides."""
        paragraphs = [part.strip() for part in story_text.split("\n\n") if part.strip()]
        if not paragraphs:
            return []

        slides = []
        current_slide = ""

        for paragraph in paragraphs:
            candidate = f"{current_slide}\n\n{paragraph}".strip() if current_slide else paragraph
            if len(candidate) <= max_chars_per_slide:
                current_slide = candidate
                continue

            if current_slide:
                slides.append(current_slide)
                current_slide = paragraph
            else:
                slides.append(paragraph[:max_chars_per_slide].rsplit(" ", 1)[0].strip() or paragraph[:max_chars_per_slide])
                current_slide = paragraph[len(slides[-1]):].strip()

            if len(slides) >= max_slides:
                break

        if current_slide and len(slides) < max_slides:
            slides.append(current_slide)

        return slides[:max_slides]

    def schedule_instagram_post(self, confession: Confession) -> bool:
        """Main function to process confession and post to Instagram"""
        print(f"Processing confession: {confession.timestamp}")
        try:
            # Initialize image generator
            generator = ConfessionImageGenerator(confession)

            # Check if text will generate only one slide
            slides = generator.split_text_into_slides()
            is_single_slide = len(slides) == 1

            if is_single_slide:
                # Create reel for single slide
                print("Single slide detected. Creating reel...")

                # Generate reel image (9:16 with larger font)
                color_scheme = {
                    'bg': (0, 0, 0),
                    'text': (255, 255, 255),
                    'accent': (220, 220, 220),
                }
                reel_image_path = generator.create_reel_image(slides[0], color_scheme)

                if not reel_image_path:
                    print("Failed to generate reel image.")
                    return False

                # Generate reel video using FFmpeg
                reel_output_path = os.path.join("generated_images", f"confession_{confession.row_num}_reel.mp4")
                audio_path = "assets/audio1.mp3"

                reel_gen = FfmpegReelGenerator(reel_image_path, reel_output_path, audio_path)
                reel_video_path = reel_gen.create_reel()

                if not reel_video_path:
                    print("Failed to generate reel video.")
                    # Clean up reel image
                    try:
                        os.remove(reel_image_path)
                    except:
                        pass
                    return False

                # Upload reel to Cloudinary
                reel_url = self.upload_video_to_cloudinary(reel_video_path, confession.row_num)
                if not reel_url:
                    print("Failed to upload reel to Cloudinary")
                    # Clean up local files
                    try:
                        os.remove(reel_image_path)
                        os.remove(reel_video_path)
                    except:
                        pass
                    return False

                # Create Instagram reel post
                media_container_id = self.create_instagram_reel(reel_url, confession.summary_caption, confession.sigma_reply)

                if media_container_id:
                    print("Waiting for Instagram to process reel...")
                    time.sleep(30)  # Reels may need more time to process

                    post_id = self.publish_instagram_post(media_container_id, retry_delays=[15, 20, 30, 45])
                    if post_id:
                        self.post_generated_comments(post_id, confession)
                        self.share_confession_to_story(confession, generator, slides[0])
                        print(f"Successfully posted reel for confession {confession.timestamp} to Instagram!")
                        # Clean up local files
                        try:
                            os.remove(reel_image_path)
                            os.remove(reel_video_path)
                        except:
                            pass
                        return True

                # Clean up on failure
                try:
                    os.remove(reel_image_path)
                    os.remove(reel_video_path)
                except:
                    pass
                return False
            else:
                # Multiple slides - create carousel
                print("Multiple slides detected. Creating carousel...")

                # Generate images (carousel)
                image_paths = generator.generate_confession_images()

                if not image_paths:
                    print("Failed to generate images.")
                    return False

                # Upload to Cloudinary
                public_urls = self.upload_images_to_cloudinary(image_paths, confession.row_num)
                if not public_urls:
                    print("Failed to upload images to Cloudinary")
                    return False

                # Create Instagram carousel
                media_container_id = self.create_instagram_carousel(public_urls, confession.summary_caption, confession.sigma_reply)

                if media_container_id:
                    print("Waiting for Instagram to process media...")
                    time.sleep(20)  # Give Instagram time to process

                    post_id = self.publish_instagram_post(media_container_id, retry_delays=[10, 15, 20])
                    if post_id:
                        self.post_generated_comments(post_id, confession)
                        self.share_confession_to_story(confession, generator, slides[0])
                        print(f"Successfully posted confession {confession.timestamp} to Instagram!")
                        # Clean up local images
                        for image_path in image_paths:
                            try:
                                os.remove(image_path)
                            except:
                                pass
                        return True

                return False
        finally:
            confession.pinned_comments = None

    def refresh_instagram_access_token(self) -> str:
        """Refresh the Instagram access token if needed"""
        url = f"{self.fb_graph_api_base}/refresh_access_token"
        params = {
            'grant_type': "ig_refresh_token",
            'access_token': self.access_token
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            new_token = response.json().get('access_token', '')
            if new_token:
                print("Instagram access token refreshed successfully.")
                self.access_token = new_token
                return new_token
            else:
                print("Failed to refresh Instagram access token.")
                return ""
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing Instagram access token: {e}")
            return ""
        
    def delete_all_assets(self):
        """
        Deletes all assets (images, videos, raw files) from your Cloudinary account.
        WARNING: This action is irreversible. All assets will be permanently deleted.
        """
        print("WARNING: This will permanently delete ALL assets from your Cloudinary account.")
        print("Please ensure you have backups if needed.")

        resource_types = ['image', 'video', 'raw'] # Add or remove types as needed

        for r_type in resource_types:
            print(f"\n--- Deleting {r_type.upper()} resources ---")
            next_cursor = None
            has_more = True
            total_deleted = 0

            while has_more:
                try:
                    # Use list_resources to get a batch of resource IDs
                    # max_results can be up to 500
                    response = cloudinary.api.resources(
                        type="upload", # 'upload', 'private', 'authenticated'
                        resource_type=r_type,
                        max_results=500,
                        next_cursor=next_cursor
                    )

                    resources = response.get('resources', [])
                    if not resources:
                        print(f"No more {r_type} resources found.")
                        has_more = False
                        continue

                    public_ids = [res['public_id'] for res in resources]

                    if public_ids:
                        print(f"Found {len(public_ids)} {r_type} resources to delete. Deleting...")
                        # Delete the resources
                        delete_result = cloudinary.api.delete_resources(
                            public_ids,
                            resource_type=r_type,
                            invalidate=True # Invalidate CDN cache for these assets
                        )
                        total_deleted += len(public_ids)
                        print(f"Deletion status for current batch: {delete_result}")
                    else:
                        print(f"No {r_type} public IDs to delete in this batch.")

                    next_cursor = response.get('next_cursor')
                    if not next_cursor:
                        has_more = False
                        print(f"Finished processing all {r_type} resources.")
                    else:
                        print(f"Proceeding to next batch of {r_type} resources...")
                        # Small delay to respect API rate limits, especially for very large accounts
                        time.sleep(1)

                except Error as e:
                    print(f"Cloudinary API Error while deleting {r_type}: {e}")
                    has_more = False # Stop on error
                except Exception as e:
                    print(f"An unexpected error occurred while deleting {r_type}: {e}")
                    has_more = False # Stop on error

            print(f"--- Total {r_type.upper()} resources deleted: {total_deleted} ---")

        print("\n--- All specified resource types have been processed. ---")
        print("It may take some time for changes to propagate and for CDN caches to clear.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test with short tex
    short_confession = Confession(
        timestamp= '14/06/2025 19:30:55',
        row_num=1,
        text="I secretly love pineapple on pizza and I'm tired of pretending I don't!",
        summary_caption="🍕 Food confession time! #confessions #foodie #unpopularopinion",
        sentiment="positive",
        count=1,
        sigma_reply="Embrace your unique taste! Pineapple on pizza is a bold choice! 🍍🍕"
    )
    
    # Test with long text that will create a carousel
    long_confession = Confession(
        timestamp='14/06/2025 19:35:00',
        row_num=2,
        text= """I've been living a double life for the past three years. By day, I'm a corporate lawyer working 80-hour weeks in a prestigious firm. Everyone thinks I'm this successful, put-together person. But by night, I'm a street artist creating murals in abandoned buildings around the city. I've never told anyone, not even my closest friends or family. The art world knows me by a completely different name, and I've even sold some pieces to galleries. The crazy part is that some of my corporate colleagues have unknowingly bought my art for their offices. I'm torn between two worlds - the financial security of my legal career and the creative fulfillment of my art. Sometimes I wonder what would happen if these two worlds collided. Would I lose everything I've worked for, or would people finally see the real me? I dream of the day I can just be an artist full-time, but the fear of disappointing everyone and losing my stable income keeps me trapped in this double life. It's exhausting pretending to be someone I'm not during the day, but I don't know how to break free from this cycle.""",
        summary_caption="🎨 Living a double life between corporate world and street art... #confessions #artist #doublelife #authentic #dreams",
        sentiment="mixed",
        count=2,
        sigma_reply="Your story is a powerful reminder of the struggle between passion and stability."
    )
    
    poster = InstagramPoster()
    
    print("Testing short confession...")
    poster.schedule_instagram_post(short_confession)
    
    print("\n" + "="*50 + "\n")
    
    print("Testing long confession (carousel)...")
    poster.schedule_instagram_post(long_confession)
