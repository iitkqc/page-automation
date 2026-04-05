import hashlib
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from content_taxonomy import (
    get_category_display_name,
    get_category_footer,
    get_category_intro_fallback,
    get_category_series_label,
    normalize_category,
)
from model import Confession

IMAGE_OUTPUT_DIR = "generated_images"
os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

THEMES_BY_SENTIMENT = {
    "positive": [
        {
            "name": "sunrise",
            "bg_top": (255, 141, 90),
            "bg_bottom": (97, 39, 82),
            "text": (252, 246, 238),
            "accent": (255, 224, 162),
            "panel": (20, 15, 26, 132),
            "outline": (255, 255, 255, 54),
            "glow_primary": (255, 203, 143, 150),
            "glow_secondary": (255, 116, 92, 100),
            "stroke": (255, 255, 255, 20),
        },
        {
            "name": "lime-light",
            "bg_top": (27, 79, 114),
            "bg_bottom": (16, 28, 56),
            "text": (246, 250, 250),
            "accent": (161, 255, 206),
            "panel": (7, 17, 24, 136),
            "outline": (255, 255, 255, 48),
            "glow_primary": (118, 255, 212, 135),
            "glow_secondary": (58, 187, 255, 95),
            "stroke": (255, 255, 255, 22),
        },
    ],
    "negative": [
        {
            "name": "midnight-ember",
            "bg_top": (18, 21, 32),
            "bg_bottom": (89, 20, 35),
            "text": (249, 243, 240),
            "accent": (255, 173, 144),
            "panel": (7, 8, 14, 152),
            "outline": (255, 255, 255, 34),
            "glow_primary": (255, 110, 89, 118),
            "glow_secondary": (127, 29, 29, 102),
            "stroke": (255, 255, 255, 18),
        },
        {
            "name": "storm",
            "bg_top": (34, 42, 59),
            "bg_bottom": (10, 13, 22),
            "text": (242, 247, 250),
            "accent": (148, 195, 255),
            "panel": (7, 13, 23, 148),
            "outline": (255, 255, 255, 32),
            "glow_primary": (91, 141, 239, 118),
            "glow_secondary": (55, 65, 81, 100),
            "stroke": (255, 255, 255, 16),
        },
    ],
    "mixed": [
        {
            "name": "violet-rush",
            "bg_top": (78, 59, 150),
            "bg_bottom": (19, 24, 54),
            "text": (248, 245, 255),
            "accent": (255, 205, 232),
            "panel": (15, 11, 31, 136),
            "outline": (255, 255, 255, 44),
            "glow_primary": (255, 123, 172, 126),
            "glow_secondary": (103, 80, 255, 118),
            "stroke": (255, 255, 255, 20),
        },
        {
            "name": "aurora",
            "bg_top": (7, 65, 92),
            "bg_bottom": (28, 15, 49),
            "text": (244, 251, 252),
            "accent": (160, 251, 230),
            "panel": (6, 14, 20, 138),
            "outline": (255, 255, 255, 42),
            "glow_primary": (76, 242, 194, 134),
            "glow_secondary": (146, 86, 255, 96),
            "stroke": (255, 255, 255, 18),
        },
    ],
    "neutral": [
        {
            "name": "campus-night",
            "bg_top": (25, 34, 53),
            "bg_bottom": (9, 13, 27),
            "text": (247, 249, 252),
            "accent": (255, 214, 126),
            "panel": (5, 10, 20, 145),
            "outline": (255, 255, 255, 36),
            "glow_primary": (96, 165, 250, 110),
            "glow_secondary": (253, 224, 71, 88),
            "stroke": (255, 255, 255, 18),
        },
        {
            "name": "sandstone",
            "bg_top": (92, 63, 46),
            "bg_bottom": (27, 22, 35),
            "text": (250, 245, 238),
            "accent": (253, 224, 170),
            "panel": (20, 13, 16, 142),
            "outline": (255, 255, 255, 38),
            "glow_primary": (254, 215, 170, 126),
            "glow_secondary": (251, 146, 60, 90),
            "stroke": (255, 255, 255, 18),
        },
    ],
}

MONOCHROME_COLORS = {
    "bg": (0, 0, 0),
    "text": (255, 255, 255),
    "accent": (220, 220, 220),
}


class ConfessionImageGenerator:
    def __init__(self, confession: Confession):
        self.confession = confession
        self.img_width = 1080
        self.img_height = 1080
        self.max_chars_per_slide = 360
        self.theme = self.select_theme()

    def select_theme(self) -> dict:
        sentiment = (self.confession.sentiment or "neutral").lower()
        theme_pool = THEMES_BY_SENTIMENT.get(sentiment, THEMES_BY_SENTIMENT["neutral"])
        category = normalize_category(self.confession.category)
        seed = f"{self.confession.timestamp}-{self.confession.row_num}-{sentiment}-{category}"
        theme_index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(theme_pool)
        return theme_pool[theme_index]

    def load_font(self, size: int):
        font_path = os.path.join("assets", "NotoSansDevanagari-Regular.ttf")
        try:
            return ImageFont.truetype(font_path, size)
        except Exception as exc:
            print(f"Font loading error: {exc}")
            return ImageFont.load_default()

    def interpolate_color(self, start: tuple[int, int, int], end: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
        return tuple(
            int(start[channel] + (end[channel] - start[channel]) * ratio)
            for channel in range(3)
        )

    def create_gradient_background(self, width: int, height: int) -> Image.Image:
        base = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(base)

        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = self.interpolate_color(self.theme["bg_top"], self.theme["bg_bottom"], ratio)
            draw.line([(0, y), (width, y)], fill=color + (255,))

        glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.ellipse(
            (-120, -80, int(width * 0.62), int(height * 0.55)),
            fill=self.theme["glow_primary"],
        )
        glow_draw.ellipse(
            (int(width * 0.45), int(height * 0.42), width + 120, height + 120),
            fill=self.theme["glow_secondary"],
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(110))
        composed = Image.alpha_composite(base, glow_layer)

        accent_draw = ImageDraw.Draw(composed)
        for offset in range(-220, width, 170):
            accent_draw.line(
                [(offset, int(height * 0.9)), (offset + 250, int(height * 0.55))],
                fill=self.theme["stroke"],
                width=2,
            )

        return composed

    def create_monochrome_background(self, width: int, height: int) -> Image.Image:
        return Image.new("RGB", (width, height), color=MONOCHROME_COLORS["bg"])

    def measure_text(self, draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def break_long_word(self, draw: ImageDraw.ImageDraw, word: str, font, max_width: int) -> list[str]:
        chunks = []
        current = ""

        for char in word:
            candidate = f"{current}{char}"
            candidate_width, _ = self.measure_text(draw, candidate, font)
            if candidate_width <= max_width or not current:
                current = candidate
            else:
                chunks.append(current)
                current = char

        if current:
            chunks.append(current)

        return chunks or [word]

    def wrap_text_by_width(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
        cleaned_text = [line.strip() for line in text.splitlines() if line.strip()]
        paragraphs = cleaned_text or [text.strip()]
        wrapped_lines = []

        for paragraph in paragraphs:
            current_line = ""
            for word in paragraph.split():
                candidate = f"{current_line} {word}".strip()
                candidate_width, _ = self.measure_text(draw, candidate, font)
                if candidate_width <= max_width:
                    current_line = candidate
                    continue

                if current_line:
                    wrapped_lines.append(current_line)
                    current_line = ""

                word_width, _ = self.measure_text(draw, word, font)
                if word_width > max_width:
                    wrapped_lines.extend(self.break_long_word(draw, word, font, max_width))
                else:
                    current_line = word

            if current_line:
                wrapped_lines.append(current_line)

        return wrapped_lines or [""]

    def get_confession_label(self) -> str:
        if self.confession.count:
            return f"CONFESSION #{self.confession.count}"
        return "IITK CONFESSION"

    def get_confession_number_label(self) -> str:
        if self.confession.count:
            return f"#{self.confession.count}"
        return ""

    def get_sentiment_label(self) -> str:
        sentiment = (self.confession.sentiment or "neutral").strip().upper()
        return sentiment if sentiment else "NEUTRAL"

    def get_category_label(self) -> str:
        return get_category_display_name(self.confession.category).upper()

    def get_series_label(self) -> str:
        return get_category_series_label(self.confession.category).upper()

    def clean_caption_text(self) -> str:
        caption = self.confession.summary_caption or ""
        without_hashtags = re.sub(r"#\w+", "", caption)
        cleaned = re.sub(r"\s+", " ", without_hashtags).strip(" .,-")
        return cleaned

    def build_intro_text(self) -> str:
        caption_text = self.clean_caption_text()
        if caption_text:
            intro_text = re.split(r"(?<=[.!?])\s+", caption_text)[0]
        else:
            intro_text = re.split(r"(?<=[.!?])\s+", self.confession.text.strip())[0]

        intro_text = intro_text.strip().strip('"')
        if len(intro_text) > 96:
            intro_text = intro_text[:96].rsplit(" ", 1)[0].strip() + "..."

        return intro_text or get_category_intro_fallback(self.confession.category)

    def truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        shortened = text[:limit].rsplit(" ", 1)[0].strip()
        return (shortened or text[:limit]).strip() + "..."

    def get_body_font_size(self, text: str, is_reel: bool = False) -> int:
        length = len(text)
        if is_reel:
            if length <= 90:
                return 62
            if length <= 180:
                return 54
            if length <= 260:
                return 48
            return 42

        if length <= 90:
            return 58
        if length <= 180:
            return 50
        if length <= 280:
            return 44
        return 40

    def fit_font_to_panel(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        start_size: int,
        min_size: int,
        max_width: int,
        max_height: int,
        line_height_factor: float,
    ):
        current_size = start_size

        while current_size >= min_size:
            font = self.load_font(current_size)
            lines = self.wrap_text_by_width(draw, text, font, max_width)
            size_value = font.size if hasattr(font, "size") else current_size
            line_height = int(size_value * line_height_factor)
            if len(lines) * line_height <= max_height:
                return font, lines, line_height
            current_size -= 2

        font = self.load_font(min_size)
        lines = self.wrap_text_by_width(draw, text, font, max_width)
        size_value = font.size if hasattr(font, "size") else min_size
        line_height = int(size_value * line_height_factor)
        return font, lines, line_height

    def draw_patterned_panel(
        self,
        image: Image.Image,
        bounds: tuple[int, int, int, int],
        radius: int,
        outline_width: int = 3,
    ) -> None:
        left, top, right, bottom = bounds
        panel_width = max(right - left, 1)
        panel_height = max(bottom - top, 1)
        panel_rgb = self.theme["panel"][:3]
        accent_rgb = self.theme["accent"][:3]
        text_rgb = self.theme["text"][:3]
        bg_bottom_rgb = self.theme["bg_bottom"]

        mask = Image.new("L", (panel_width, panel_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, panel_width - 1, panel_height - 1), radius=radius, fill=255)

        base_alpha = min(220, self.theme["panel"][3] + 34)
        panel = Image.new("RGBA", (panel_width, panel_height), panel_rgb + (base_alpha,))
        panel_draw = ImageDraw.Draw(panel)

        tile_size = max(56, min(panel_width, panel_height) // 6)
        light_tile = self.interpolate_color(panel_rgb, accent_rgb, 0.1)
        dark_tile = self.interpolate_color(panel_rgb, bg_bottom_rgb, 0.5)
        light_alpha = 18
        dark_alpha = 34

        for row, y in enumerate(range(-tile_size, panel_height + tile_size, tile_size)):
            for col, x in enumerate(range(-tile_size, panel_width + tile_size, tile_size)):
                is_light_tile = (row + col) % 2 == 0
                fill_color = light_tile if is_light_tile else dark_tile
                fill_alpha = light_alpha if is_light_tile else dark_alpha
                panel_draw.rectangle((x, y, x + tile_size, y + tile_size), fill=fill_color + (fill_alpha,))

        grid_alpha = 18
        grid_color = self.interpolate_color(panel_rgb, text_rgb, 0.3) + (grid_alpha,)
        for x in range(tile_size, panel_width, tile_size):
            panel_draw.line([(x, 0), (x, panel_height)], fill=grid_color, width=1)
        for y in range(tile_size, panel_height, tile_size):
            panel_draw.line([(0, y), (panel_width, y)], fill=grid_color, width=1)

        sheen = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        sheen_draw.ellipse(
            (-panel_width // 4, -panel_height // 3, panel_width // 2, panel_height // 3),
            fill=accent_rgb + (28,),
        )
        sheen_draw.ellipse(
            (panel_width // 3, panel_height // 2, panel_width + panel_width // 6, panel_height + panel_height // 4),
            fill=text_rgb + (10,),
        )
        sheen = sheen.filter(ImageFilter.GaussianBlur(max(18, tile_size // 2)))
        panel = Image.alpha_composite(panel, sheen)

        diagonal_overlay = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
        diagonal_draw = ImageDraw.Draw(diagonal_overlay)
        diagonal_color = bg_bottom_rgb + (26,)
        for offset in range(-panel_height, panel_width, tile_size):
            diagonal_draw.line(
                [(offset, panel_height), (offset + panel_height, 0)],
                fill=diagonal_color,
                width=2,
            )
        diagonal_overlay = diagonal_overlay.filter(ImageFilter.GaussianBlur(1))
        panel = Image.alpha_composite(panel, diagonal_overlay)

        clipped_panel = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
        clipped_panel.paste(panel, (0, 0), mask)
        image.paste(clipped_panel, (left, top), clipped_panel)

        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(bounds, radius=radius, outline=self.theme["outline"], width=outline_width)

    def build_story_share_text(self) -> str:
        slides = self.split_text_into_slides()
        story_text = slides[0] if slides else self.confession.text.strip()
        story_text = story_text.strip().strip('"')
        return self.truncate_text(story_text, 240)

    def draw_badge(self, draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font):
        text_width, text_height = self.measure_text(draw, text, font)
        padding_x = 28
        padding_y = 16
        bounds = (
            x,
            y,
            x + text_width + (padding_x * 2),
            y + text_height + (padding_y * 2),
        )
        draw.rounded_rectangle(bounds, radius=24, fill=self.theme["panel"], outline=self.theme["outline"], width=2)
        draw.text((x + padding_x, y + padding_y - 2), text, font=font, fill=self.theme["accent"])

    def draw_slide_indicator(self, draw: ImageDraw.ImageDraw, slide_num: int, total_slides: int, font, width: int, height: int):
        indicator = f"{slide_num}/{total_slides}"
        indicator_width, indicator_height = self.measure_text(draw, indicator, font)
        padding_x = 12
        padding_y = 8
        x = width - indicator_width - (padding_x * 2) - 30
        y = height - indicator_height - (padding_y * 2) - 28
        bounds = (
            x,
            y,
            x + indicator_width + (padding_x * 2),
            y + indicator_height + (padding_y * 2),
        )
        draw.rectangle(bounds, fill=MONOCHROME_COLORS["text"], outline=MONOCHROME_COLORS["text"])
        draw.text((x + padding_x, y + padding_y - 2), indicator, font=font, fill=MONOCHROME_COLORS["bg"])

    def draw_monochrome_header(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        title_y: int,
        count_y: int,
        title_size: int,
        count_size: int,
    ) -> None:
        title_font = self.load_font(title_size)
        count_font = self.load_font(count_size)

        draw.text(
            (width // 2, title_y),
            "IITK QUICK CONFESSIONS",
            font=title_font,
            fill=MONOCHROME_COLORS["accent"],
            anchor="mm",
        )

        count_label = self.get_confession_number_label()
        if count_label:
            draw.text(
                (width // 2, count_y),
                count_label,
                font=count_font,
                fill=MONOCHROME_COLORS["accent"],
                anchor="mm",
            )

    def draw_centered_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        bounds: tuple[int, int, int, int],
        start_size: int,
        min_size: int,
        line_height_factor: float,
        fill: tuple[int, int, int],
    ) -> None:
        max_text_width = bounds[2] - bounds[0]
        max_text_height = bounds[3] - bounds[1]
        body_font, lines, line_height = self.fit_font_to_panel(
            draw,
            text,
            start_size,
            min_size,
            max_text_width,
            max_text_height,
            line_height_factor,
        )
        total_height = len(lines) * line_height
        start_y = bounds[1] + ((bounds[3] - bounds[1] - total_height) // 2)

        for index, line in enumerate(lines):
            line_width, _ = self.measure_text(draw, line, body_font)
            x = (bounds[0] + bounds[2] - line_width) // 2
            y = start_y + (index * line_height)
            draw.text((x, y), line, font=body_font, fill=fill)

    def split_text_into_slides(self) -> list[str]:
        if len(self.confession.text) <= self.max_chars_per_slide:
            return [self.confession.text]

        sentences = self.confession.text.replace("!", ".").replace("?", ".").split(".")
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        slides = []
        current_slide = ""

        for sentence in sentences:
            if len(sentence) > self.max_chars_per_slide:
                comma_chunks = [chunk.strip() for chunk in sentence.split(",") if chunk.strip()]
                for chunk in comma_chunks:
                    if len(current_slide) + len(chunk) + 2 > self.max_chars_per_slide:
                        if current_slide:
                            slides.append(current_slide.strip())
                            current_slide = chunk + ","
                        else:
                            words = chunk.split()
                            temp_slide = ""
                            for word in words:
                                if len(temp_slide) + len(word) + 1 > self.max_chars_per_slide:
                                    if temp_slide:
                                        slides.append(temp_slide.strip() + ",")
                                        temp_slide = word
                                    else:
                                        slides.append(word[: self.max_chars_per_slide - 3] + "...")
                                        temp_slide = ""
                                else:
                                    temp_slide = f"{temp_slide} {word}".strip()
                            if temp_slide:
                                current_slide = temp_slide + ","
                    else:
                        current_slide = f"{current_slide} {chunk},".strip()
            else:
                if len(current_slide) + len(sentence) + 2 > self.max_chars_per_slide:
                    if current_slide:
                        slides.append(current_slide.strip())
                        current_slide = sentence + "."
                    else:
                        words = sentence.split()
                        temp_slide = ""
                        for word in words:
                            if len(temp_slide) + len(word) + 1 > self.max_chars_per_slide:
                                if temp_slide:
                                    slides.append(temp_slide.strip() + ".")
                                    temp_slide = word
                                else:
                                    slides.append(word[: self.max_chars_per_slide - 3] + "...")
                                    temp_slide = ""
                            else:
                                temp_slide = f"{temp_slide} {word}".strip()
                        if temp_slide:
                            current_slide = temp_slide + "."
                else:
                    current_slide = f"{current_slide} {sentence}.".strip()

        if current_slide:
            slides.append(current_slide.strip())

        return slides

    def create_intro_slide(self, total_slides: int) -> str:
        img = self.create_monochrome_background(self.img_width, self.img_height)
        draw = ImageDraw.Draw(img)

        helper_font = self.load_font(26)
        intro_text = self.build_intro_text()

        self.draw_monochrome_header(
            draw,
            self.img_width,
            title_y=52,
            count_y=104,
            title_size=30,
            count_size=28,
        )
        self.draw_centered_text_block(
            draw,
            intro_text,
            bounds=(120, 190, self.img_width - 120, self.img_height - 160),
            start_size=64 if len(intro_text) < 54 else 56,
            min_size=40,
            line_height_factor=1.18,
            fill=MONOCHROME_COLORS["text"],
        )

        draw.text(
            (self.img_width // 2, self.img_height - 110),
            "Swipe for the full confession",
            font=helper_font,
            fill=MONOCHROME_COLORS["accent"],
            anchor="mm",
        )

        self.draw_slide_indicator(draw, 1, total_slides, helper_font, self.img_width, self.img_height)

        image_path = os.path.join(IMAGE_OUTPUT_DIR, f"confession_{self.confession.row_num}_slide_1.png")
        img.save(image_path, optimize=True)
        return image_path

    def create_slide_image(self, text: str, slide_num: int, total_slides: int) -> str:
        img = self.create_monochrome_background(self.img_width, self.img_height)
        draw = ImageDraw.Draw(img)

        indicator_font = self.load_font(24)
        self.draw_monochrome_header(
            draw,
            self.img_width,
            title_y=52,
            count_y=104,
            title_size=30,
            count_size=28,
        )
        self.draw_centered_text_block(
            draw,
            text,
            bounds=(120, 180, self.img_width - 120, self.img_height - 110),
            start_size=min(self.get_body_font_size(text) + 12, 72),
            min_size=34,
            line_height_factor=1.18,
            fill=MONOCHROME_COLORS["text"],
        )

        if total_slides > 1:
            self.draw_slide_indicator(draw, slide_num, total_slides, indicator_font, self.img_width, self.img_height)

        filename = f"confession_{self.confession.row_num}_slide_{slide_num}.png"
        image_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
        img.save(image_path, optimize=True)
        return image_path

    def create_reel_image(self, text: str, colors: dict | None = None) -> str:
        del colors

        reel_width = 1080
        reel_height = 1920
        img = self.create_monochrome_background(reel_width, reel_height)
        draw = ImageDraw.Draw(img)

        self.draw_monochrome_header(
            draw,
            reel_width,
            title_y=132,
            count_y=188,
            title_size=34,
            count_size=32,
        )
        self.draw_centered_text_block(
            draw,
            text,
            bounds=(110, 330, reel_width - 110, reel_height - 200),
            start_size=min(self.get_body_font_size(text, is_reel=True) + 10, 78),
            min_size=36,
            line_height_factor=1.2,
            fill=MONOCHROME_COLORS["text"],
        )

        image_path = os.path.join(IMAGE_OUTPUT_DIR, f"confession_{self.confession.row_num}_reel.png")
        img.save(image_path, optimize=True)
        return image_path

    def create_story_image(
        self,
        text: str | None = None,
        footer_text: str = "Full context is available on the feed.",
        max_chars: int = 240,
        start_size: int = 64,
        min_size: int = 36,
        text_top: int = 330,
        bottom_padding: int = 180,
    ) -> str:
        story_width = 1080
        story_height = 1920
        img = self.create_monochrome_background(story_width, story_height)
        draw = ImageDraw.Draw(img)

        story_text = self.truncate_text((text or self.build_story_share_text()).strip(), max_chars)
        helper_font = self.load_font(30)
        has_footer = bool((footer_text or "").strip())
        text_bottom = story_height - 270 if has_footer else story_height - bottom_padding
        self.draw_monochrome_header(
            draw,
            story_width,
            title_y=132,
            count_y=188,
            title_size=34,
            count_size=32,
        )
        self.draw_centered_text_block(
            draw,
            story_text,
            bounds=(110, text_top, story_width - 110, text_bottom),
            start_size=start_size,
            min_size=min_size,
            line_height_factor=1.2,
            fill=MONOCHROME_COLORS["text"],
        )

        if has_footer:
            draw.text(
                (story_width // 2, story_height - 136),
                footer_text,
                font=helper_font,
                fill=MONOCHROME_COLORS["accent"],
                anchor="mm",
            )

        image_path = os.path.join(IMAGE_OUTPUT_DIR, f"confession_{self.confession.row_num}_story.png")
        img.save(image_path, optimize=True)
        return image_path

    def generate_confession_images(self) -> list[str]:
        body_slides = self.split_text_into_slides()

        max_body_slides = 10
        if len(body_slides) > max_body_slides:
            print(
                f"Warning: Confession {self.confession.row_num} has {len(body_slides)} slides. "
                f"Truncating body slides to {max_body_slides} to fit Instagram's carousel limit."
            )
            body_slides = body_slides[:max_body_slides]

        image_paths = []
        total_slides = len(body_slides)

        print(f"Generating {total_slides} slide(s) for confession {self.confession.row_num}")

        for offset, slide_text in enumerate(body_slides, start=1):
            image_paths.append(self.create_slide_image(slide_text, offset, total_slides))

        return image_paths
