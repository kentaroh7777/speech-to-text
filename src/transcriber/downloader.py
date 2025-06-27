"""Audio file downloader with duplicate checking."""

import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .config import Episode


class AudioDownloader:
    """Audio file downloader."""
    
    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def download(self, audio_url: str, title: str, published_date: datetime) -> Optional[Path]:
        """Download audio file if it doesn't already exist."""
        try:
            # Generate file path
            file_path = self._generate_file_path(title, published_date, audio_url)
            
            # Check if file already exists
            if file_path.exists():
                self.logger.info(f"スキップ - ファイルが既に存在: {file_path.name}")
                return file_path
            
            self.logger.info(f"音声ダウンロード中: {title}")
            
            # Download file
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"ダウンロード完了: {file_path.name} ({file_size_mb:.1f} MB)")
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"音声ダウンロードに失敗 {audio_url}: {e}")
            return None
    
    def _generate_file_path(self, title: str, published_date: datetime, audio_url: str) -> Path:
        """Generate file path for audio file."""
        # Sanitize title
        sanitized_title = self._sanitize_filename(title)
        
        # Get date string
        date_str = published_date.strftime("%Y%m%d")
        
        # Get file extension from URL
        parsed_url = urlparse(audio_url)
        path = parsed_url.path
        extension = Path(path).suffix.lower()
        
        # Default to .m4a if no extension found
        if not extension or extension not in ['.mp3', '.m4a', '.wav', '.ogg']:
            extension = '.m4a'
        
        # Generate filename
        filename = f"{sanitized_title}_{date_str}{extension}"
        
        return self.download_dir / filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by replacing problematic characters."""
        # Characters to replace with underscores
        problematic_chars = ['/', '?', ':', '*', '"', '<', '>', '|', '\\']
        
        sanitized = filename
        for char in problematic_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove multiple consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Limit length to avoid filesystem issues
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def file_exists(self, title: str, published_date: datetime, audio_url: str) -> bool:
        """Check if audio file already exists."""
        file_path = self._generate_file_path(title, published_date, audio_url)
        return file_path.exists()