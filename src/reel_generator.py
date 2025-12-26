import subprocess
import os

class FfmpegReelGenerator:
    def __init__(self, image_path: str, output_path: str, music_path: str = "assets/audio1.mp3"):
        self.image_path = image_path
        self.output_path = output_path
        self.music_path = music_path
        self.duration = 60  # seconds

    def create_reel(self):
        """
        Uses FFmpeg to create a video:
        1. Loops image (already 9:16, 1080x1920)
        2. Adds audio
        3. Cuts to shortest stream (usually audio or fixed duration)
        """
        if not os.path.exists(self.music_path):
            print(f"Music file not found at {self.music_path}.")
            return None

        # FFmpeg command breakdown:
        # -loop 1 -i img    : Input image, looped infinitely
        # -i audio          : Input audio
        # -c:v libx264      : Video codec
        # -tune stillimage  : Optimization for static images (tiny file size, low CPU)
        # -c:a aac          : Audio codec
        # -b:a 128k         : Audio bitrate
        # -pix_fmt yuv420p  : Pixel format for compatibility
        # -t 60             : Duration (60 seconds)
        # -shortest         : End when the shortest input ends

        cmd = [
            'ffmpeg',
            '-y',                  # Overwrite output file
            '-loop', '1',          # Loop the image
            '-i', self.image_path, # Input 0: Image (already 9:16)
            '-i', self.music_path, # Input 1: Audio
            '-c:v', 'libx264',     # H.264 Video
            '-tune', 'stillimage', # OPTIMIZATION: Critical for performance
            '-c:a', 'aac',         # AAC Audio
            '-b:a', '128k',        # Audio bitrate
            '-pix_fmt', 'yuv420p', # Ensure mobile compatibility
            '-t', str(self.duration), # Force duration
            '-shortest',           # Stop if audio is shorter than duration
            self.output_path
        ]

        try:
            # Run command, suppress output unless error
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"Reel generated successfully: {self.output_path}")
            return self.output_path
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            print("FFmpeg not found. Ensure it is installed in GitHub Actions.")
            return None