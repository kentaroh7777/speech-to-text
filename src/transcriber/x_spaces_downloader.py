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
            
            # Step 1: Download best audio without postprocessing to avoid HLS live quirks
            cmd = [
                "python3", "-m", "yt_dlp",
                "-o", output_template,
                "-f", "bestaudio",
                "--no-part",  # write final file directly
                url,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Find the downloaded file (any audio extension)
            candidates = sorted(self.download_dir.glob(f"x_spaces_{timestamp}_*"))
            candidates = [p for p in candidates if p.is_file() and not p.suffix.endswith('.part')]
            if not candidates:
                logger.error("No audio file was downloaded")
                return None

            source_file = candidates[0]
            logger.info(f"Successfully downloaded: {source_file}")

            # Step 2: Post-process locally with ffmpeg (silence removal + mp3 high quality)
            output_mp3 = source_file.with_suffix('.mp3')
            ffmpeg_cmd = [
                "ffmpeg", "-hide_banner", "-y",
                "-i", str(source_file),
                "-af", "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB",
                "-c:a", "libmp3lame", "-q:a", "0",
                str(output_mp3)
            ]
            try:
                pp = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                if pp.returncode != 0:
                    logger.error("ffmpeg postprocess failed: %s", pp.stderr)
                    return None
            except Exception as e:
                logger.error("ffmpeg execution failed: %s", e)
                return None

            if not output_mp3.exists() or output_mp3.stat().st_size == 0:
                logger.error("Postprocessed audio file not created")
                return None

            # Return episode and attach original source path for optional cleanup
            episode = self._create_episode_from_file(output_mp3, url, original_path=source_file)
            return episode
            
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

    def _create_episode_from_file(self, file_path: Path, original_url: str, original_path: Optional[Path] = None) -> Episode:
        """Create Episode object from downloaded file."""
        # Extract title from filename (remove extension)
        title = file_path.stem
        
        # Use current datetime as published date (TODO: Extract actual space time from API)
        published_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        ep = Episode(
            title=title,
            audio_url=str(file_path.absolute()),
            published_date=published_date,
            duration=""
        )
        if original_path is not None:
            try:
                setattr(ep, "original_audio_path", str(original_path.absolute()))
            except Exception:
                pass
        return ep