import requests
import os
import time
from PIL import Image, ImageDraw, ImageFont # For simple image generation
import textwrap # For wrapping text on images

# --- Configuration (use GitHub Secrets for these) ---
FB_GRAPH_API_BASE = "https://graph.facebook.com/v19.0/" # Or the latest version
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN") # Page Access Token
IMAGE_OUTPUT_DIR = "generated_images"

if not os.path.exists(IMAGE_OUTPUT_DIR):
    os.makedirs(IMAGE_OUTPUT_DIR)

def generate_confession_image(confession_text, filename="confession.png"):
    """
    Generates a simple image with the confession text.
    You might want to use a more sophisticated image generation library or service.
    """
    img_width, img_height = 1080, 1080 # Standard Instagram square
    background_color = (240, 240, 240) # Light grey
    text_color = (30, 30, 30) # Dark grey

    img = Image.new('RGB', (img_width, img_height), color=background_color)
    d = ImageDraw.Draw(img)

    # Load a font (ensure you have one available on your runner, or provide it)
    try:
        font_path = "arial.ttf" # Example font. You might need to include a .ttf file in your repo
        font = ImageFont.truetype(font_path, 40)
    except IOError:
        font = ImageFont.load_default()
        print("Warning: arial.ttf not found, using default font. Image might look different.")

    margin = 80
    max_width = img_width - 2 * margin

    # Wrap text
    wrapped_text = textwrap.fill(confession_text, width=int(max_width / (font.getbbox("W")[2] - font.getbbox("W")[0]) * 1.5)) # Estimate width based on W

    # Calculate text size and position
    # text_bbox = d.textbbox((0,0), wrapped_text, font=font) # This is newer, requires Pillow 9.2+
    # text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    
    # Older way for text size
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    lines = wrapped_text.split('\n')
    line_heights = [dummy_draw.textbbox((0,0), line, font=font)[3] - dummy_draw.textbbox((0,0), line, font=font)[1] for line in lines]
    text_height = sum(line_heights)
    
    y_text = (img_height - text_height) / 2 # Center vertically

    # Draw each line of text
    for line in lines:
        line_width = d.textbbox((0,0), line, font=font)[2] - d.textbbox((0,0), line, font=font)[0]
        x_text = (img_width - line_width) / 2 # Center horizontally
        d.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += dummy_draw.textbbox((0,0), line, font=font)[3] - dummy_draw.textbbox((0,0), line, font=font)[1] # Move to next line

    image_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
    img.save(image_path)
    print(f"Generated image: {image_path}")
    return image_path

def upload_image_to_instagram(image_path, caption):
    """
    Uploads an image to Instagram via the Graph API.
    Returns the media_id if successful, None otherwise.
    """
    if not INSTAGRAM_PAGE_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("Instagram API credentials not set.")
        return None

    # Step 1: Upload the image to get a container ID
    url = f"{FB_GRAPH_API_BASE}{INSTAGRAM_PAGE_ID}/media"
    
    # For local image upload, you'd typically need to host it publicly
    # or use a multi-part form data upload, which is more complex with requests.
    # The simplest way for GitHub Actions is to upload to a temporary public URL (e.g., imgur, AWS S3)
    # or to make the image accessible from the GitHub Actions runner.
    # For this boilerplate, we'll assume the image is locally accessible by the runner.
    # The Instagram API requires an image_url.
    # For GitHub Actions, you'd need to upload this image to a publicly accessible URL (e.g., a simple web server
    # within the action, or an S3 bucket) and provide that URL.
    
    # Placeholder: In a real scenario, `image_url` would be a public URL
    # For demonstration, we'll simulate a public URL for now.
    # You'd need a separate step in your workflow to make the image public.
    # E.g., push to a GitHub Pages branch, or upload to a CDN.
    
    # For simplicity of this boilerplate, we'll skip the actual hosting for now and assume it's available
    # However, for a real project, this is a critical step!
    print(f"To publish, the image needs to be publicly accessible at a URL.")
    print(f"Simulating public URL for: {image_path}")
    
    # A common approach is to upload to a temporary storage or CDN.
    # Let's mock a success for boilerplate.
    
    # Example using a dummy public URL for local testing:
    # In a real GitHub Action, you'd have uploaded the image to a publicly accessible place first.
    # For instance, a simple way is to have a GitHub Pages branch and push generated images there.
    # Then the URL would be: `https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/generated_images/confession.png`
    
    # FOR DEMO PURPOSES: This will FAIL in real Graph API without a public URL.
    # Replace this with your actual public image URL
    mock_image_url = "https://example.com/your_publicly_hosted_image.png" 
    
    params = {
        'image_url': mock_image_url, 
        'caption': caption,
        'access_token': INSTAGRAM_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors
        media_container_id = response.json().get('id')
        print(f"Media container created with ID: {media_container_id}")
        return media_container_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating media container: {e}")
        print(f"Response: {response.text}")
        return None

def publish_instagram_post(media_container_id):
    """
    Publishes the media container to Instagram.
    """
    if not INSTAGRAM_PAGE_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("Instagram API credentials not set.")
        return False

    url = f"{FB_GRAPH_API_BASE}{INSTAGRAM_PAGE_ID}/media_publish"
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
        print(f"Response: {response.text}")
        return False

def schedule_instagram_post(confession_data):
    """
    Orchestrates the image generation and Instagram publishing.
    """
    print(f"Processing confession: {confession_data['id']}")
    
    # Generate image
    image_filename = f"confession_{confession_data['id']}.png"
    image_path = generate_confession_image(confession_data['text'], image_filename)
    
    if not image_path:
        print("Failed to generate image.")
        return False

    # This part requires the image to be publicly accessible.
    # For a GitHub Action, you'd need to push `image_path` to a public URL (e.g., GitHub Pages, S3).
    # For this boilerplate, the `upload_image_to_instagram` function has a placeholder for `mock_image_url`.
    # You MUST replace this with a real public URL where your generated image is hosted.
    
    media_container_id = upload_image_to_instagram(image_path, confession_data['summary_caption'])
    if media_container_id:
        # Instagram API typically publishes immediately once the container is ready.
        # There's no direct "schedule for later" in the basic Graph API, you schedule the *run* of your script.
        # However, for a confession page, you'd likely want to publish as soon as a good one is found.
        # If you truly need future scheduling, you'd have to manage that logic in your script
        # (e.g., store the container ID and publish it with a separate GitHub Action at a later time).
        
        # For simplicity, we publish immediately after container creation.
        print("Waiting a few seconds for media container to process...")
        time.sleep(10) # Give Instagram some time to process the container
        success = publish_instagram_post(media_container_id)
        if success:
            print(f"Successfully posted confession {confession_data['id']} to Instagram!")
            # Optionally, you might want to delete the local image file after successful upload.
            # os.remove(image_path)
            return True
    return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    # Dummy data for testing
    dummy_confession = {
        'id': 'test_123',
        'submitted_at': '2025-06-01T12:00:00Z',
        'text': "This is a dummy confession to test the Instagram posting functionality. I hope it works!",
        'summary_caption': "A test confession for automation."
    }
    schedule_instagram_post(dummy_confession)