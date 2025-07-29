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
    rss_url: str = ""  # Make RSS URL optional for local mode
    local_dir: str = ""
    x_spaces_url: str = ""  # 修正: twitter_spaces_url → x_spaces_url
    download_dir: str = "./downloads"
    output_dir: str = "./transcripts"
    date_range: str = "today"
    output_format: str = "txt"
    whisper_model: str = "base"
    max_episodes: int = 10
    chunk_size_mb: int = 50
    overlap_seconds: int = 15
    delete_audio: bool = False
    delete_original: bool = False
    # OpenAI API settings
    openai_api_key: str = ""
    use_openai_api: bool = False
    openai_fallback: bool = True  # Fallback to OpenAI API if local Whisper fails
    
    def __str__(self):
        """String representation with masked API key for security."""
        # Create a copy of the config with masked API key
        masked_config = self.__dict__.copy()
        if masked_config.get('openai_api_key'):
            key = masked_config['openai_api_key']
            if len(key) > 8:
                masked_config['openai_api_key'] = key[:4] + '***' + key[-4:]
            else:
                masked_config['openai_api_key'] = '***'
        
        return f"Config({', '.join(f'{k}={repr(v)}' for k, v in masked_config.items())})"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # RSS URL is no longer required for local mode
        # Validation will be done in CLI
        
        # Convert relative paths to absolute paths from original working directory
        self.download_dir = self._resolve_path(self.download_dir)
        self.output_dir = self._resolve_path(self.output_dir)
        
        # Ensure directories exist
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to original working directory."""
        path_obj = Path(path)
        
        # If it's already absolute, return as is
        if path_obj.is_absolute():
            return str(path_obj)
        
        # Get original working directory from environment (set by stt script)
        original_cwd = os.getenv('STT_ORIGINAL_CWD')
        if original_cwd:
            return str(Path(original_cwd) / path_obj)
        
        # Fallback to current working directory
        return str(Path.cwd() / path_obj)


@dataclass
class Episode:
    """Episode information from RSS feed or local file."""
    title: str
    audio_url: str  # For local files, this will be the absolute file path
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
    local_dir: Optional[str] = None,
    x_spaces_url: Optional[str] = None,  # 修正: twitter_spaces_url → x_spaces_url
    download_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    date_range: Optional[str] = None,
    output_format: Optional[str] = None,
    whisper_model: Optional[str] = None,
    max_episodes: Optional[int] = None,
    chunk_size_mb: Optional[int] = None,
    overlap_seconds: Optional[int] = None,
    delete_audio: Optional[bool] = None,
    delete_original: Optional[bool] = None,
    openai_api_key: Optional[str] = None,
    use_openai_api: Optional[bool] = None,
    openai_fallback: Optional[bool] = None,
    no_openai_fallback: Optional[bool] = None
) -> Config:
    """Get configuration with priority: CLI args > env vars > defaults."""
    
    def get_value(cli_value, env_key: str, default_value):
        """Get value with priority order."""
        if cli_value is not None:
            return cli_value
        return os.getenv(env_key, default_value)
    
    return Config(
        rss_url=get_value(rss_url, "STT_RSS_URL", ""),  # Default to empty string
        local_dir=local_dir or "",
        x_spaces_url=x_spaces_url or "",  # 修正: twitter_spaces_url → x_spaces_url
        download_dir=get_value(download_dir, "STT_DOWNLOAD_DIR", "./downloads"),
        output_dir=get_value(output_dir, "STT_OUTPUT_DIR", "./transcripts"),
        date_range=get_value(date_range, "STT_DATE_RANGE", "today"),
        output_format=get_value(output_format, "STT_OUTPUT_FORMAT", "txt"),
        whisper_model=get_value(whisper_model, "STT_WHISPER_MODEL", "base"),
        max_episodes=int(get_value(max_episodes, "STT_MAX_EPISODES", 10)),
        chunk_size_mb=int(get_value(chunk_size_mb, "STT_CHUNK_SIZE_MB", 50)),
        overlap_seconds=int(get_value(overlap_seconds, "STT_OVERLAP_SECONDS", 15)),
        delete_audio=bool(get_value(delete_audio, "STT_DELETE_AUDIO", False)),
        delete_original=delete_original or False,
        # OpenAI API settings
        openai_api_key=get_value(openai_api_key, "OPENAI_API_KEY", ""),
        use_openai_api=bool(get_value(use_openai_api, "STT_USE_OPENAI_API", False)),
        openai_fallback=not no_openai_fallback if no_openai_fallback is not None else bool(get_value(openai_fallback, "STT_OPENAI_FALLBACK", True))
    )