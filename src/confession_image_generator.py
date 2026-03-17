import hashlib
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
        seed = f"{self.confession.timestamp}-{self.confession.row_num}-{sentiment}"
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

    def get_sentiment_label(self) -> str:
        sentiment = (self.confession.sentiment or "neutral").strip().upper()
        return sentiment if sentiment else "NEUTRAL"

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

        return intro_text or "A campus confession worth reading."

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
        padding_x = 18
        padding_y = 12
        x = width - indicator_width - (padding_x * 2) - 54
        y = height - indicator_height - (padding_y * 2) - 46
        bounds = (
            x,
            y,
            x + indicator_width + (padding_x * 2),
            y + indicator_height + (padding_y * 2),
        )
        draw.rounded_rectangle(bounds, radius=22, fill=self.theme["panel"], outline=self.theme["outline"], width=2)
        draw.text((x + padding_x, y + padding_y - 1), indicator, font=font, fill=self.theme["text"])

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
        img = self.create_gradient_background(self.img_width, self.img_height)
        draw = ImageDraw.Draw(img)

        brand_font = self.load_font(28)
        badge_font = self.load_font(24)
        helper_font = self.load_font(26)
        quote_font = self.load_font(150)
        intro_text = self.build_intro_text()

        draw.text((self.img_width // 2, 92), "IITK QUICK CONFESSIONS", font=brand_font, fill=self.theme["text"], anchor="mm")
        self.draw_badge(draw, 72, 126, self.get_confession_label(), badge_font)

        sentiment_width, _ = self.measure_text(draw, self.get_sentiment_label(), badge_font)
        self.draw_badge(draw, self.img_width - sentiment_width - 172, 126, self.get_sentiment_label(), badge_font)

        panel_bounds = (88, 260, self.img_width - 88, self.img_height - 178)
        draw.rounded_rectangle(panel_bounds, radius=42, fill=self.theme["panel"], outline=self.theme["outline"], width=3)
        draw.text((148, 282), '"', font=quote_font, fill=self.theme["accent"])

        max_text_width = panel_bounds[2] - panel_bounds[0] - 150
        max_text_height = panel_bounds[3] - panel_bounds[1] - 120
        intro_font, intro_lines, line_height = self.fit_font_to_panel(
            draw,
            intro_text,
            64 if len(intro_text) < 54 else 56,
            40,
            max_text_width,
            max_text_height,
            1.22,
        )
        total_height = len(intro_lines) * line_height
        start_y = panel_bounds[1] + ((panel_bounds[3] - panel_bounds[1] - total_height) // 2) + 18

        for index, line in enumerate(intro_lines):
            line_width, _ = self.measure_text(draw, line, intro_font)
            x = (self.img_width - line_width) // 2
            y = start_y + (index * line_height)
            draw.text((x, y), line, font=intro_font, fill=self.theme["text"])

        draw.text(
            (self.img_width // 2, self.img_height - 110),
            "Swipe for the full confession",
            font=helper_font,
            fill=self.theme["accent"],
            anchor="mm",
        )

        self.draw_slide_indicator(draw, 1, total_slides, badge_font, self.img_width, self.img_height)

        image_path = os.path.join(IMAGE_OUTPUT_DIR, f"confession_{self.confession.row_num}_slide_1.png")
        img.save(image_path, optimize=True)
        return image_path

    def create_slide_image(self, text: str, slide_num: int, total_slides: int) -> str:
        img = self.create_gradient_background(self.img_width, self.img_height)
        draw = ImageDraw.Draw(img)

        brand_font = self.load_font(28)
        badge_font = self.load_font(24)
        helper_font = self.load_font(22)
        quote_font = self.load_font(110)

        draw.text((self.img_width // 2, 88), "IITK QUICK CONFESSIONS", font=brand_font, fill=self.theme["text"], anchor="mm")
        self.draw_badge(draw, 72, 122, self.get_confession_label(), badge_font)

        panel_bounds = (88, 205, self.img_width - 88, self.img_height - 152)
        draw.rounded_rectangle(panel_bounds, radius=40, fill=self.theme["panel"], outline=self.theme["outline"], width=3)
        draw.text((136, 230), '"', font=quote_font, fill=self.theme["accent"])

        max_text_width = panel_bounds[2] - panel_bounds[0] - 144
        max_text_height = panel_bounds[3] - panel_bounds[1] - 120
        body_font, text_lines, line_height = self.fit_font_to_panel(
            draw,
            text,
            self.get_body_font_size(text),
            34,
            max_text_width,
            max_text_height,
            1.24,
        )
        total_height = len(text_lines) * line_height
        start_y = panel_bounds[1] + ((panel_bounds[3] - panel_bounds[1] - total_height) // 2) + 12

        for index, line in enumerate(text_lines):
            line_width, _ = self.measure_text(draw, line, body_font)
            x = (self.img_width - line_width) // 2
            y = start_y + (index * line_height)
            draw.text((x, y), line, font=body_font, fill=self.theme["text"])

        draw.text((110, self.img_height - 92), self.theme["name"].upper(), font=helper_font, fill=self.theme["accent"])
        self.draw_slide_indicator(draw, slide_num, total_slides, badge_font, self.img_width, self.img_height)

        filename = f"confession_{self.confession.row_num}_slide_{slide_num}.png"
        image_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
        img.save(image_path, optimize=True)
        return image_path

    def create_reel_image(self, text: str, colors: dict | None = None) -> str:
        del colors

        reel_width = 1080
        reel_height = 1920
        img = self.create_gradient_background(reel_width, reel_height)
        draw = ImageDraw.Draw(img)

        brand_font = self.load_font(34)
        badge_font = self.load_font(26)
        hook_font = self.load_font(30)
        helper_font = self.load_font(28)
        quote_font = self.load_font(170)

        draw.text((reel_width // 2, 128), "IITK QUICK CONFESSIONS", font=brand_font, fill=self.theme["text"], anchor="mm")
        self.draw_badge(draw, 88, 182, self.get_confession_label(), badge_font)

        hook_text = self.truncate_text(self.build_intro_text(), 42)
        hook_width, _ = self.measure_text(draw, hook_text, hook_font)
        hook_x = max(88, reel_width - hook_width - 180)
        self.draw_badge(draw, hook_x, 182, hook_text, hook_font)

        panel_bounds = (96, 410, reel_width - 96, reel_height - 240)
        draw.rounded_rectangle(panel_bounds, radius=48, fill=self.theme["panel"], outline=self.theme["outline"], width=3)
        draw.text((150, 454), '"', font=quote_font, fill=self.theme["accent"])

        max_text_width = panel_bounds[2] - panel_bounds[0] - 152
        max_text_height = panel_bounds[3] - panel_bounds[1] - 170
        body_font, lines, line_height = self.fit_font_to_panel(
            draw,
            text,
            self.get_body_font_size(text, is_reel=True),
            34,
            max_text_width,
            max_text_height,
            1.28,
        )
        total_text_height = len(lines) * line_height
        start_y = panel_bounds[1] + ((panel_bounds[3] - panel_bounds[1] - total_text_height) // 2) + 20

        for index, line in enumerate(lines):
            line_width, _ = self.measure_text(draw, line, body_font)
            x = (reel_width - line_width) // 2
            y = start_y + (index * line_height)
            draw.text((x, y), line, font=body_font, fill=self.theme["text"])

        draw.text(
            (reel_width // 2, reel_height - 118),
            "One slide. One campus mood.",
            font=helper_font,
            fill=self.theme["accent"],
            anchor="mm",
        )

        image_path = os.path.join(IMAGE_OUTPUT_DIR, f"confession_{self.confession.row_num}_reel.png")
        img.save(image_path, optimize=True)
        return image_path

    def generate_confession_images(self) -> list[str]:
        body_slides = self.split_text_into_slides()

        image_paths = []
        if len(body_slides) > 1:
            max_body_slides = 9
            if len(body_slides) > max_body_slides:
                print(
                    f"Warning: Confession {self.confession.row_num} has {len(body_slides)} slides. "
                    f"Truncating body slides to {max_body_slides} so the intro card still fits."
                )
                body_slides = body_slides[:max_body_slides]

            total_slides = len(body_slides) + 1
            image_paths.append(self.create_intro_slide(total_slides))
            start_index = 2
        else:
            total_slides = len(body_slides)
            start_index = 1

        print(f"Generating {total_slides} slide(s) for confession {self.confession.row_num}")

        for offset, slide_text in enumerate(body_slides, start=start_index):
            image_paths.append(self.create_slide_image(slide_text, offset, total_slides))

        return image_paths
