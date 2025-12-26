from PIL import Image, ImageDraw, ImageFont
import textwrap
from model import Confession
import os
IMAGE_OUTPUT_DIR = "generated_images"

if not os.path.exists(IMAGE_OUTPUT_DIR):
    os.makedirs(IMAGE_OUTPUT_DIR)

class ConfessionImageGenerator:
    def __init__(self, confession: Confession):
        self.confession = confession
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
    
    def create_solid_background(self, colors: dict) -> Image.Image:
        """Create a solid background image"""
        img = Image.new('RGB', (self.img_width, self.img_height), color=colors['bg'])
        return img
    
    def split_text_into_slides(self) -> list[str]:
        """Split long text into readable slides"""
        if len(self.confession.text) <= self.max_chars_per_slide:
            return [self.confession.text]
        
        # Split by sentences first
        sentences = self.confession.text.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        slides = []
        current_slide = ""
        
        for sentence in sentences:
            # If sentence is too long, split by commas
            if len(sentence) > self.max_chars_per_slide:
                comma_chunks = sentence.split(',')
                comma_chunks = [c.strip() for c in comma_chunks if c.strip()]
                for chunk in comma_chunks:
                    if len(current_slide) + len(chunk) + 2 > self.max_chars_per_slide:
                        if current_slide:
                            slides.append(current_slide.strip())
                            current_slide = chunk + ","
                        else:
                            # Single chunk is too long, split by words
                            words = chunk.split()
                            temp_slide = ""
                            for word in words:
                                if len(temp_slide) + len(word) + 1 > self.max_chars_per_slide:
                                    if temp_slide:
                                        slides.append(temp_slide.strip() + ",")
                                        temp_slide = word
                                    else:
                                        # Single word too long, truncate
                                        slides.append(word[:self.max_chars_per_slide-3] + "...")
                                        temp_slide = ""
                                else:
                                    temp_slide += " " + word if temp_slide else word
                            if temp_slide:
                                current_slide = temp_slide + ","
                    else:
                        current_slide += " " + chunk + "," if current_slide else chunk + ","
            else:
                # Normal sentence handling
                if len(current_slide) + len(sentence) + 2 > self.max_chars_per_slide:
                    if current_slide:
                        slides.append(current_slide.strip())
                        current_slide = sentence + "."
                    else:
                        # Single sentence is too long, split by words
                        words = sentence.split()
                        temp_slide = ""
                        for word in words:
                            if len(temp_slide) + len(word) + 1 > self.max_chars_per_slide:
                                if temp_slide:
                                    slides.append(temp_slide.strip() + ".")
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
                          colors: dict) -> str:
        """Create a single slide image"""
        font_large, font_medium, font_small = self.load_fonts()
        
        # Create background
        img = self.create_solid_background(colors)
        draw = ImageDraw.Draw(img)
        
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
            id_text = f"#{self.confession.count}"
            draw.text(((self.img_width) // 2, 100), 
                    id_text, font=font_medium, fill=colors['accent'], anchor="mm")
            
            # TODO: Add timestamp somewhere, need to think of the best place
        
        # Save image
        filename = f"confession_{self.confession.row_num}_slide_{slide_num}.png"
        image_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
        img.save(image_path, quality=95, optimize=True)
        
        return image_path
    
    def generate_confession_images(self) -> list[str]:
        """Generate single or carousel images based on text length"""
        # Choose color scheme based on confession ID for consistency
        color_scheme = {
                        'bg': (0, 0, 0),
                        'text': (255, 255, 255),
                        'accent': (220, 220, 220),
                        }
        
        # Split text into slides
        slides = self.split_text_into_slides()
        
        if len(slides) > 10:
            print(f"Warning: Confession {self.confession.row_num} has {len(slides)} slides, which exceeds the limit of 10. Truncating to 10 slides.")
            slides = slides[:10]
        
        print(f"Generating {len(slides)} slide(s) for confession {self.confession.row_num}")
        
        image_paths = []
        for i, slide_text in enumerate(slides, 1):
            image_path = self.create_slide_image(
                slide_text, i, len(slides), color_scheme
            )
            image_paths.append(image_path)
        
        return image_paths
