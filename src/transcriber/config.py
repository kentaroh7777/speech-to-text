"""Configuration management for speech-to-text transcriber."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    """Configuration for the transcriber."""
    rss_url: str
    download_dir: str = "./downloads"
    output_dir: str = "./transcripts"
    date_range: str = "today"
    output_format: str = "txt"
    whisper_model: str = "base"
    max_episodes: int = 10
    chunk_size_mb: int = 25
    overlap_seconds: int = 15
    delete_audio: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.rss_url:
            raise ValueError("RSS URL is required")
        
        # Ensure directories exist
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class Episode:
    """Episode information from RSS feed."""
    title: str
    audio_url: str
    published_date: datetime
    duration: str = ""
    
    def get_sanitized_title(self) -> str:
        """Get sanitized title for file naming."""
        # Replace problematic characters with underscores
        problematic_chars = ['/', '?', ':', '*', '"', '<', '>', '|']
        sanitized = self.title
        for char in problematic_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized


def get_config(
    rss_url: Optional[str] = None,
    download_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    date_range: Optional[str] = None,
    output_format: Optional[str] = None,
    whisper_model: Optional[str] = None,
    max_episodes: Optional[int] = None,
    chunk_size_mb: Optional[int] = None,
    overlap_seconds: Optional[int] = None,
    delete_audio: Optional[bool] = None
) -> Config:
    """Get configuration with priority: CLI args > env vars > defaults."""
    
    def get_value(cli_value, env_key: str, default_value):
        """Get value with priority order."""
        if cli_value is not None:
            return cli_value
        return os.getenv(env_key, default_value)
    
    return Config(
        rss_url=get_value(rss_url, "STT_RSS_URL", ""),
        download_dir=get_value(download_dir, "STT_DOWNLOAD_DIR", "./downloads"),
        output_dir=get_value(output_dir, "STT_OUTPUT_DIR", "./transcripts"),
        date_range=get_value(date_range, "STT_DATE_RANGE", "today"),
        output_format=get_value(output_format, "STT_OUTPUT_FORMAT", "txt"),
        whisper_model=get_value(whisper_model, "STT_WHISPER_MODEL", "base"),
        max_episodes=int(get_value(max_episodes, "STT_MAX_EPISODES", 10)),
        chunk_size_mb=int(get_value(chunk_size_mb, "STT_CHUNK_SIZE_MB", 25)),
        overlap_seconds=int(get_value(overlap_seconds, "STT_OVERLAP_SECONDS", 15)),
        delete_audio=bool(get_value(delete_audio, "STT_DELETE_AUDIO", False))
    )