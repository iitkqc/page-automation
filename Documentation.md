## File Documentation 

### 1. `GeminiProcessor` (gemini_processor.py)
**Purpose**: Handles all Gemini AI operations for content moderation and selection.

**Key Methods**:
- `__init__()`: Initializes Gemini API client
- `select_top_confessions(confessions, max_count=4)`: Selects best confessions using AI
- `moderate_and_shortlist_confession(confession_text)`: Moderates content for safety

**Usage**:
```python
processor = GeminiProcessor()
result = processor.moderate_and_shortlist_confession("Some confession text")
```

### 2. `GoogleFormReader` (google_form_reader.py)
**Purpose**: Manages all Google Sheets operations and Instagram token management.

**Key Methods**:
- `__init__(sheet_url, credentials_path)`: Initializes with sheet URL and credentials
- `get_latest_confessions_from_sheet()`: Fetches new confessions
- `mark_confession_as_processed(row, status)`: Marks confessions as processed
- `get_updated_count()`: Updates and returns confession count
- `get_instagram_access_token()`: Retrieves Instagram token
- `set_instagram_access_token(token)`: Updates Instagram token

**Usage**:
```python
reader = GoogleFormReader(sheet_url, credentials_path)
confessions = reader.get_latest_confessions_from_sheet()
```

### 3. `InstagramPoster` (insta_poster.py)
**Purpose**: Handles all Instagram posting operations and image uploads.

**Key Methods**:
- `__init__()`: Initializes with Instagram configuration
- `schedule_instagram_post(confession_data, count)`: Main posting method
- `upload_images_to_cloudinary(image_paths, row_num)`: Uploads images
- `refresh_instagram_access_token()`: Refreshes access token

**Usage**:
```python
poster = InstagramPoster()
success = poster.schedule_instagram_post(confession_data, count)
```

### 4. `ConfessionImageGenerator` (insta_poster.py)
**Purpose**: Generates confession images for Instagram posts.

**Key Methods**:
- `generate_confession_images(text, row_num, confession_id, count)`: Creates images
- `split_text_into_slides(text)`: Splits long text into slides
- `create_slide_image(...)`: Creates individual slide images

### 5. `ConfessionAutomation` (main.py)
**Purpose**: Main orchestrator class that coordinates all components.

**Key Methods**:
- `__init__()`: Initializes all configuration
- `process_confessions()`: Main workflow method
- `setup_components()`: Initializes all component classes
- `moderate_confessions(confessions)`: Processes moderation
- `schedule_posts(posts, confessions)`: Handles posting

**Usage**:
```python
automation = ConfessionAutomation()
automation.process_confessions()
```