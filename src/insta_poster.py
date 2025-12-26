import requests
import os
import time
import cloudinary
import cloudinary.api
from cloudinary.exceptions import Error
import cloudinary.uploader
from typing import List, Dict
from model import Confession
from confession_image_generator import ConfessionImageGenerator

# --- Configuration ---
FB_GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")

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
        
        # if not self.access_token:
        #     print("Warning: INSTAGRAM_ACCESS_TOKEN not set.")

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

    def create_instagram_carousel(self, image_urls: List[str], caption: str | None, sigma_reply: str | None) -> str:
        """Create Instagram carousel post"""
        if not self.instagram_page_id or not self.access_token:
            print("Instagram API credentials not set.")
            return ""
        
        # For single image, use regular post
        if len(image_urls) == 1:
            return self.create_single_instagram_post(image_urls[0], caption, sigma_reply)
        
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
            'caption': f"{f'Admin reply: {sigma_reply}\n' if sigma_reply else caption} \n\n#IITKQuickConfessions #IITKConfessions #confession #iitk #iitkanpur #iit #jee #jeeadvanced #jeemains",
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

    def create_single_instagram_post(self, image_url: str, caption: str | None, sigma_reply: str | None) -> str:
        """Create single Instagram post"""
        url = f"{self.fb_graph_api_base}/{self.instagram_page_id}/media"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        data = {
            'image_url': image_url,
            'caption': f"{f'Admin reply: {sigma_reply}\n' if sigma_reply else caption}  \n\n#IITKQuickConfessions #IITKConfessions #confession #iitk #iitkanpur #iit #jee #jeeadvanced #jeemains",
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            media_container_id = response.json().get('id', '')
            print(f"Media container created with")
            return media_container_id
        except requests.exceptions.RequestException as e:
            print(f"Error creating media container: {e}")
            return ""

    def publish_instagram_post(self, media_container_id: str) -> bool:
        """Publish the media container to Instagram"""
        if not self.instagram_page_id or not self.access_token:
            return False

        url = f"{self.fb_graph_api_base}/{self.instagram_page_id}/media_publish"
        params = {
            'creation_id': media_container_id,
            'access_token': self.access_token
        }

        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            post_id = response.json().get('id')
            print(f"Successfully published post with ID: {post_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error publishing post: {e}")
            return False

    def schedule_instagram_post(self, confession: Confession) -> bool:
        """Main function to process confession and post to Instagram"""
        print(f"Processing confession: {confession.timestamp}")
        
        # Initialize image generator
        generator = ConfessionImageGenerator(confession)
        
        # Generate images (single or carousel)
        image_paths = generator.generate_confession_images()
        
        if not image_paths:
            print("Failed to generate images.")
            return False
        
        # Upload to Cloudinary
        public_urls = self.upload_images_to_cloudinary(image_paths, confession.row_num)
        if not public_urls:
            print("Failed to upload images to Cloudinary")
            return False
        
        # Create Instagram post (single or carousel)
        if len(public_urls) == 1:
            media_container_id = self.create_single_instagram_post(public_urls[0], confession.summary_caption, confession.sigma_reply)
        else:
            media_container_id = self.create_instagram_carousel(public_urls, confession.summary_caption, confession.sigma_reply)
        
        if media_container_id:
            print("Waiting for Instagram to process media...")
            time.sleep(20)  # Give Instagram time to process
            
            success = self.publish_instagram_post(media_container_id)
            if success:
                print(f"Successfully posted confession {confession.timestamp} to Instagram!")
                # Clean up local images
                for image_path in image_paths:
                    try:
                        os.remove(image_path)
                    except:
                        pass
                return True
        
        return False

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