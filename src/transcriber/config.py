"""Configuration management for speech-to-text transcriber."""

import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    """Configuration for transcription."""
    rss_url: str = ""
    local_dir: str = ""
    x_spaces_url: str = ""
    download_dir: str = ""
    output_dir: str = ""
    date_range: str = "today"
    output_format: str = "txt"
    whisper_model: str = "base"
    max_episodes: int = 5
    chunk_size_mb: int = 25
    overlap_seconds: int = 15
    delete_audio: bool = False
    delete_original: bool = False
    openai_api_key: str = ""
    use_openai_api: bool = False
    openai_fallback: bool = True
    author: str = ""
    contact: str = ""

    def __str__(self) -> str:
        """String representation with masked API key."""
        masked_key = self.openai_api_key[:7] + '*' * (len(self.openai_api_key) - 10) + self.openai_api_key[-3:] if len(self.openai_api_key) > 10 else '***'
        return f"Config(rss_url='{self.rss_url}', local_dir='{self.local_dir}', x_spaces_url='{self.x_spaces_url}', download_dir='{self.download_dir}', output_dir='{self.output_dir}', date_range='{self.date_range}', output_format='{self.output_format}', whisper_model='{self.whisper_model}', max_episodes={self.max_episodes}, chunk_size_mb={self.chunk_size_mb}, overlap_seconds={self.overlap_seconds}, delete_audio={self.delete_audio}, delete_original={self.delete_original}, openai_api_key='{masked_key}', use_openai_api={self.use_openai_api}, openai_fallback={self.openai_fallback}, author='{self.author}', contact='{self.contact}')"
    
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


@dataclass
class TranscriptResult:
    """Structured transcription result with metadata."""
    transcript: str
    filename: str
    date: str  # 発信日（ファイル名から抽出、なければファイル更新日）
    source: str = ""  # URL or filename only (not full path)
    duration: float = 0.0  # seconds
    size_mb: float = 0.0
    model: str = ""
    engine: str = ""  # 'local_whisper', 'openai_api'
    processed_at: str = ""
    processing_time: str = ""
    author: str = ""
    contact: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def get_config(**kwargs) -> Config:
    """Get configuration from environment variables and kwargs."""
    load_dotenv()
    
    return Config(
        rss_url=kwargs.get('rss_url') or os.getenv('STT_RSS_URL', ''),
        local_dir=kwargs.get('local_dir') or os.getenv('STT_LOCAL_DIR', ''),
        x_spaces_url=kwargs.get('x_spaces_url') or os.getenv('STT_X_SPACES_URL', ''),
        download_dir=kwargs.get('download_dir') or os.getenv('STT_DOWNLOAD_DIR', './downloads'),
        output_dir=kwargs.get('output_dir') or os.getenv('STT_OUTPUT_DIR', './transcripts'),
        date_range=kwargs.get('date_range') or os.getenv('STT_DATE_RANGE', 'latest'),
        output_format=kwargs.get('output_format') or os.getenv('STT_OUTPUT_FORMAT', 'json'),
        whisper_model=kwargs.get('whisper_model') or os.getenv('STT_WHISPER_MODEL', 'base'),
        max_episodes=int(kwargs.get('max_episodes') or os.getenv('STT_MAX_EPISODES', '5')),
        chunk_size_mb=int(kwargs.get('chunk_size_mb') or os.getenv('STT_CHUNK_SIZE_MB', '25')),
        overlap_seconds=int(kwargs.get('overlap_seconds') or os.getenv('STT_OVERLAP_SECONDS', '15')),
        delete_audio=kwargs.get('delete_audio', False),
        delete_original=kwargs.get('delete_original', False),
        openai_api_key=kwargs.get('openai_api_key') or os.getenv('OPENAI_API_KEY', ''),
        use_openai_api=kwargs.get('use_openai_api') or os.getenv('STT_USE_OPENAI_API', '').lower() == 'true',
        openai_fallback=kwargs.get('openai_fallback', True) if 'openai_fallback' in kwargs else os.getenv('STT_OPENAI_FALLBACK', 'true').lower() == 'true',
        author=kwargs.get('author') or os.getenv('STT_AUTHOR', ''),
        contact=kwargs.get('contact') or os.getenv('STT_CONTACT', '')
    )