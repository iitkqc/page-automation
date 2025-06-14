import requests
import os
import time
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont
import textwrap
from typing import List, Dict

# --- Configuration ---
FB_GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

IMAGE_OUTPUT_DIR = "generated_images"

if not os.path.exists(IMAGE_OUTPUT_DIR):
    os.makedirs(IMAGE_OUTPUT_DIR)

class ConfessionImageGenerator:
    def __init__(self):
        self.img_width = 1080
        self.img_height = 1080
        self.margin = 80
        self.line_spacing = 15
        self.max_chars_per_slide = 400  # Adjust based on readability
    
    def load_fonts(self):
        """Load fonts with fallback options"""
        try:
            # Try different font paths
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "arial.ttf"  # Local
            ]
            # TODO: Add hindi fonts, hindi fonts are not working now
            
            font_large = None
            font_medium = None
            font_small = None
            
            for path in font_paths:
                try:
                    font_large = ImageFont.truetype(path, 50)
                    font_medium = ImageFont.truetype(path, 32)
                    font_small = ImageFont.truetype(path, 24)
                    break
                except:
                    continue
            
            if not font_large:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                
            return font_large, font_medium, font_small
            
        except Exception as e:
            print(f"Font loading error: {e}")
            default_font = ImageFont.load_default()
            return default_font, default_font, default_font
    
    def create_solid_background(self, colors: Dict) -> Image.Image:
        """Create a solid background image"""
        img = Image.new('RGB', (self.img_width, self.img_height), color=colors['bg'])
        return img
    
    def split_text_into_slides(self, text: str) -> List[str]:
        """Split long text into readable slides"""
        if len(text) <= self.max_chars_per_slide:
            return [text]
        
        # Split by sentences first
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        slides = []
        current_slide = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed limit, start new slide
            if len(current_slide) + len(sentence) + 2 > self.max_chars_per_slide:
                if current_slide:
                    slides.append(current_slide.strip())
                    current_slide = sentence + "."
                else:
                    # Single sentence is too long, force split
                    words = sentence.split()
                    temp_slide = ""
                    for word in words:
                        if len(temp_slide) + len(word) + 1 > self.max_chars_per_slide:
                            if temp_slide:
                                slides.append(temp_slide.strip())
                                temp_slide = word
                            else:
                                # Single word too long, truncate
                                slides.append(word[:self.max_chars_per_slide-3] + "...")
                                temp_slide = ""
                        else:
                            temp_slide += " " + word if temp_slide else word
                    if temp_slide:
                        current_slide = temp_slide + "."
            else:
                current_slide += " " + sentence + "." if current_slide else sentence + "."
        
        if current_slide:
            slides.append(current_slide.strip())
        
        return slides
    
    def create_slide_image(self, text: str, slide_num: int, total_slides: int, 
                          colors: Dict, row_num: str, confession_id: str, count: int) -> str:
        """Create a single slide image"""
        font_large, font_medium, font_small = self.load_fonts()
        
        # Create background
        img = self.create_solid_background(colors)
        draw = ImageDraw.Draw(img)
        
        # Add decorative elements
        self.add_decorative_elements(draw, colors)
        
        # Wrap text for better readability
        wrapped_text = textwrap.fill(text, width=35, break_long_words=False)
        lines = wrapped_text.split('\n')
        
        # Calculate text positioning
        line_height = 60
        total_text_height = len(lines) * line_height
        start_y = (self.img_height - total_text_height) // 2
        
        # Draw text (no shadow)
        for i, line in enumerate(lines):
            # Calculate x position for center alignment
            text_bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = text_bbox[2] - text_bbox[0]
            x = (self.img_width - text_width) // 2
            y = start_y + (i * line_height)
            
            draw.text((x, y), line, font=font_large, fill=colors['text'])
        
        # Add slide indicator
        if total_slides > 1:
            indicator_text = f"{slide_num}/{total_slides}"
            indicator_bbox = draw.textbbox((0, 0), indicator_text, font=font_small)
            indicator_width = indicator_bbox[2] - indicator_bbox[0]
            
            # Draw indicator background
            indicator_x = self.img_width - indicator_width - 30
            indicator_y = self.img_height - 60
            draw.rectangle([
                (indicator_x - 10, indicator_y - 5),
                (indicator_x + indicator_width + 10, indicator_y + 25)
            ], fill=colors['text'], outline=colors['text'])
            
            draw.text((indicator_x, indicator_y), indicator_text, 
                     font=font_small, fill=colors['bg'])
        
        # Add watermark
        watermark = "IITK QUICK CONFESSIONS"
        draw.text(((self.img_width) // 2, 50), 
                    watermark, font=font_medium, fill=colors['accent'], anchor="mm")
        
        if slide_num == 1:
            # Add confession ID and count on first slide
            id_text = f"#{count}"
            draw.text(((self.img_width) // 2, 100), 
                    id_text, font=font_medium, fill=colors['accent'], anchor="mm")
            
            # TODO: Add timestamp somewhere, need to think of the best place
        
        # Save image
        filename = f"confession_{row_num}_slide_{slide_num}.png"
        image_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
        img.save(image_path, quality=95, optimize=True)
        
        return image_path
    
    def add_decorative_elements(self, draw: ImageDraw.Draw, colors: Dict):
        """Add subtle decorative elements"""
        # Add corner decorations
        corner_size = 40
        
        # Top corners
        draw.arc([(20, 20), (20 + corner_size, 20 + corner_size)], 
                start=180, end=270, fill=colors['accent'], width=3)
        draw.arc([(self.img_width - 20 - corner_size, 20), 
                 (self.img_width - 20, 20 + corner_size)], 
                start=270, end=0, fill=colors['accent'], width=3)
        
        # Bottom corners
        draw.arc([(20, self.img_height - 20 - corner_size), 
                 (20 + corner_size, self.img_height - 20)], 
                start=90, end=180, fill=colors['accent'], width=3)
        draw.arc([(self.img_width - 20 - corner_size, self.img_height - 20 - corner_size), 
                 (self.img_width - 20, self.img_height - 20)], 
                start=0, end=90, fill=colors['accent'], width=3)
    
    def generate_confession_images(self, confession_text: str, row_num: str, confession_id: str, count: int) -> List[str]:
        """Generate single or carousel images based on text length"""
        # Choose color scheme based on confession ID for consistency
        color_scheme = {
                        'bg': (0, 0, 0),
                        'text': (255, 255, 255),
                        'accent': (220, 220, 220),
                        }
        
        # Split text into slides
        slides = self.split_text_into_slides(confession_text)
        
        print(f"Generating {len(slides)} slide(s) for confession {row_num}")
        
        image_paths = []
        for i, slide_text in enumerate(slides, 1):
            image_path = self.create_slide_image(
                slide_text, i, len(slides), color_scheme, row_num, confession_id, count
            )
            image_paths.append(image_path)
        
        return image_paths

def upload_images_to_cloudinary(image_paths: List[str], row_num: str) -> List[str]:
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

def create_instagram_carousel(image_urls: List[str], caption: str) -> str:
    """Create Instagram carousel post"""
    if not INSTAGRAM_PAGE_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("Instagram API credentials not set.")
        return ""
    
    # For single image, use regular post
    if len(image_urls) == 1:
        return create_single_instagram_post(image_urls[0], caption)
    
    # Create carousel container
    url = f"{FB_GRAPH_API_BASE}/me/media"
    
    # First, create media objects for each image
    media_ids = []
    for image_url in image_urls:

        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}"
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
        'caption': caption,
        'access_token': INSTAGRAM_ACCESS_TOKEN
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

def create_single_instagram_post(image_url: str, caption: str) -> str:
    """Create single Instagram post"""
    url = f"{FB_GRAPH_API_BASE}/{INSTAGRAM_PAGE_ID}/media"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}"
    }
    data = {
        'image_url': image_url,
        'caption': caption
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

def publish_instagram_post(media_container_id: str) -> bool:
    """Publish the media container to Instagram"""
    if not INSTAGRAM_PAGE_ID or not INSTAGRAM_ACCESS_TOKEN:
        return False

    url = f"{FB_GRAPH_API_BASE}/{INSTAGRAM_PAGE_ID}/media_publish"
    params = {
        'creation_id': media_container_id,
        'access_token': INSTAGRAM_ACCESS_TOKEN
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

def schedule_instagram_post(confession_data: Dict, count: int) -> bool:
    """Main function to process confession and post to Instagram"""
    print(f"Processing confession: {confession_data['id']}")
    
    # Initialize image generator
    generator = ConfessionImageGenerator()
    
    # Generate images (single or carousel)
    image_paths = generator.generate_confession_images(
        confession_data['text'], 
        confession_data['row_num'], 
        confession_id = confession_data['id'],
        count = count
    )
    
    if not image_paths:
        print("Failed to generate images.")
        return False
    
    # Upload to Cloudinary
    public_urls = upload_images_to_cloudinary(image_paths, confession_data['id'])
    if not public_urls:
        print("Failed to upload images to Cloudinary")
        return False
    
    # Create Instagram post (single or carousel)
    if len(public_urls) == 1:
        media_container_id = create_single_instagram_post(public_urls[0], confession_data['summary_caption'])
    else:
        media_container_id = create_instagram_carousel(public_urls, confession_data['summary_caption'])
    
    if media_container_id:
        print("Waiting for Instagram to process media...")
        time.sleep(20)  # Give Instagram time to process
        
        success = publish_instagram_post(media_container_id)
        if success:
            print(f"Successfully posted confession {confession_data['id']} to Instagram!")
            # Clean up local images
            for image_path in image_paths:
                try:
                    os.remove(image_path)
                except:
                    pass
            return True
    
    return False

# TODO: Implement post scheduling

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test with short text
    short_confession = {
        'id': '14/06/2025 19:30:55',
        'text': "I secretly love pineapple on pizza and I'm tired of pretending I don't!",
        'summary_caption': "🍕 Food confession time! #confessions #foodie #unpopularopinion",
        'row_num': 1
    }
    
    # Test with long text that will create a carousel
    long_confession = {
        'id': 'long_001',
        'text': """I've been living a double life for the past three years. By day, I'm a corporate lawyer working 80-hour weeks in a prestigious firm. Everyone thinks I'm this successful, put-together person. But by night, I'm a street artist creating murals in abandoned buildings around the city. I've never told anyone, not even my closest friends or family. The art world knows me by a completely different name, and I've even sold some pieces to galleries. The crazy part is that some of my corporate colleagues have unknowingly bought my art for their offices. I'm torn between two worlds - the financial security of my legal career and the creative fulfillment of my art. Sometimes I wonder what would happen if these two worlds collided. Would I lose everything I've worked for, or would people finally see the real me? I dream of the day I can just be an artist full-time, but the fear of disappointing everyone and losing my stable income keeps me trapped in this double life. It's exhausting pretending to be someone I'm not during the day, but I don't know how to break free from this cycle.""",
        'summary_caption': "🎨 Living a double life between corporate world and street art... #confessions #artist #doublelife #authentic #dreams",
        'row_num': 2
    }
    
    print("Testing short confession...")
    schedule_instagram_post(short_confession, 5111)
    
    print("\n" + "="*50 + "\n")
    
    print("Testing long confession (carousel)...")
    schedule_instagram_post(long_confession, 5111)