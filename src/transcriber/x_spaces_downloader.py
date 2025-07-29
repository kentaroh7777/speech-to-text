"""X Spaces audio downloader using yt-dlp."""

import subprocess
import re
import logging
from pathlib import Path
from datetime import datetime
from .config import Config, Episode
from typing import Optional

logger = logging.getLogger(__name__)

class XSpacesDownloader:
    """Downloads audio from X Spaces using yt-dlp."""
    
    def __init__(self, config: Config):
        self.config = config
        self.download_dir = Path(config.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_and_convert(self, url: str) -> Optional[Episode]:
        """Download audio from X Spaces and return Episode object."""
        try:
            # Validate URL patterns
            if not self._is_valid_x_spaces_url(url):
                logger.error(f"Invalid X Spaces URL format: {url}")
                return None
            
            logger.info(f"Downloading audio from X Spaces: {url}")
            logger.info("Auto-removing silence from beginning of audio (threshold: -50dB, min duration: 0.1s)")
            
            # Generate output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = str(self.download_dir / f"x_spaces_{timestamp}_%(title)s.%(ext)s")
            
            # Run yt-dlp to download audio
            cmd = [
                "python3", "-m", "yt_dlp",
                "-o", output_template,
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",  # Best quality
                "--postprocessor-args", "ffmpeg:-af silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB",  # 冒頭無音削除
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Find the downloaded file
            downloaded_files = list(self.download_dir.glob(f"x_spaces_{timestamp}_*.mp3"))
            if not downloaded_files:
                logger.error("No audio file was downloaded")
                return None
            
            downloaded_file = downloaded_files[0]
            logger.info(f"Successfully downloaded: {downloaded_file}")
            
            return self._create_episode_from_file(downloaded_file, url)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download X Spaces audio: {e}")
            logger.error(f"yt-dlp stderr: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading X Spaces: {e}")
            return None

    def _is_valid_x_spaces_url(self, url: str) -> bool:
        """Validate if URL is a valid X Spaces URL."""
        x_spaces_patterns = [
            r'https?://x\.com/i/spaces/\w+',
            r'https?://twitter\.com/i/spaces/\w+',
            r'https?://x\.com/.+/status/\d+',
            r'https?://twitter\.com/.+/status/\d+'
        ]
        
        return any(re.match(pattern, url) for pattern in x_spaces_patterns)

    def _create_episode_from_file(self, file_path: Path, original_url: str) -> Episode:
        """Create Episode object from downloaded file."""
        # Extract title from filename (remove extension)
        title = file_path.stem
        
        # Use current datetime as published date (TODO: Extract actual space time from API)
        published_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return Episode(
            title=title,
            audio_url=str(file_path.absolute()),
            published_date=published_date,
            duration=""
        ) 