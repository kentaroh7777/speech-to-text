"""Audio transcription with chunking support."""

import json
import logging
import os
import ssl
import tempfile
import urllib.request
import warnings
from pathlib import Path
from typing import List, Optional

import whisper
from pydub import AudioSegment

from .config import Config, Episode

# Disable Whisper FP16 warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Configure SSL context for Whisper model downloads
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Try to import OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AudioTranscriber:
    """Audio transcriber with chunking support for large files."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.openai_client = None
        self.use_openai = False
        
        # Initialize OpenAI client if configured
        if self.config.openai_api_key:
            self._init_openai_client()
        
        # Determine transcription method
        if self.config.use_openai_api:
            self.use_openai = True
            self.logger.info("Configured to use OpenAI API")
        else:
            self.logger.info("Configured to use local Whisper with OpenAI fallback" if self.config.openai_fallback else "Configured to use local Whisper only")
    
    def _init_openai_client(self):
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI library not available. Install with: pip install openai")
            return False
        
        try:
            self.openai_client = OpenAI(api_key=self.config.openai_api_key)
            self.logger.info("OpenAI client initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            return False
    
    def _load_model(self):
        """Load Whisper model with fallback to OpenAI API if configured."""
        if self.use_openai:
            # Using OpenAI API, no need to load local model
            return True
        
        if self.model is None:
            self.logger.info(f"Loading local Whisper model: {self.config.whisper_model}")
            
            # Patch urllib for SSL certificate handling during model download
            old_urlopen = urllib.request.urlopen
            def patched_urlopen(*args, **kwargs):
                return old_urlopen(*args, context=ssl_context, **kwargs)
            urllib.request.urlopen = patched_urlopen
            
            try:
                self.model = whisper.load_model(self.config.whisper_model)
                self.logger.info("Local Whisper model loaded successfully")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load local Whisper model: {e}")
                
                # Try fallback to OpenAI API if configured
                if self.config.openai_fallback and self.config.openai_api_key:
                    self.logger.info("Attempting fallback to OpenAI API")
                    if self._init_openai_client():
                        self.use_openai = True
                        self.logger.info("Successfully switched to OpenAI API fallback")
                        return True
                    else:
                        self.logger.error("OpenAI API fallback also failed")
                        
                return False
            finally:
                # Restore original urlopen
                urllib.request.urlopen = old_urlopen
        
        return True
    
    def transcribe(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio file, splitting if necessary."""
        try:
            if not self._load_model():
                return None
            
            # Check file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Audio file size: {file_size_mb:.1f} MB")
            
            # OpenAI API has a 25MB limit
            openai_limit_mb = 25
            
            if self.use_openai:
                if file_size_mb <= openai_limit_mb:
                    self.logger.info("Transcribing with OpenAI API")
                    return self._transcribe_with_openai(audio_path)
                else:
                    self.logger.info(f"File size ({file_size_mb:.1f}MB) exceeds OpenAI API limit ({openai_limit_mb}MB), splitting into chunks")
                    return self._transcribe_large_file_with_openai(audio_path)
            else:
                # Using local Whisper
                if file_size_mb <= self.config.chunk_size_mb:
                    self.logger.info("Transcribing audio file directly with local Whisper")
                    return self._transcribe_file(audio_path)
                else:
                    self.logger.info(f"File size exceeds {self.config.chunk_size_mb}MB, splitting into chunks for local Whisper")
                    return self._transcribe_with_chunking(audio_path)
                    
        except Exception as e:
            self.logger.error(f"Failed to transcribe {audio_path}: {e}")
            return None
    
    def _transcribe_file(self, audio_path: Path) -> str:
        """Transcribe a single audio file."""
        result = self.model.transcribe(str(audio_path))
        return result["text"].strip()
    
    def _transcribe_with_chunking(self, audio_path: Path) -> str:
        """Transcribe large audio file by splitting into chunks."""
        # Load audio file
        audio = AudioSegment.from_file(str(audio_path))
        
        # Calculate chunk duration in milliseconds
        chunk_size_bytes = self.config.chunk_size_mb * 1024 * 1024
        overlap_ms = self.config.overlap_seconds * 1000
        
        # Estimate chunk duration based on file size and total duration
        total_size_bytes = audio_path.stat().st_size
        chunk_duration_ms = int((len(audio) * chunk_size_bytes) / total_size_bytes)
        
        # Ensure minimum chunk duration
        chunk_duration_ms = max(chunk_duration_ms, 30000)  # At least 30 seconds
        
        self.logger.info(f"Chunk duration: {chunk_duration_ms/1000:.1f} seconds, overlap: {overlap_ms/1000:.1f} seconds")
        
        chunks = self._split_audio(audio, chunk_duration_ms, overlap_ms)
        transcripts = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, chunk in enumerate(chunks):
                chunk_file = temp_path / f"chunk_{i:03d}.wav"
                
                # Export chunk to temporary file
                chunk.export(str(chunk_file), format="wav")
                
                self.logger.info(f"Transcribing chunk {i+1}/{len(chunks)} ({len(chunk)/1000:.1f}s)")
                
                # Transcribe chunk
                transcript = self._transcribe_file(chunk_file)
                transcripts.append(transcript)
        
        # Combine transcripts
        combined_transcript = self._combine_transcripts(transcripts)
        self.logger.info(f"Combined {len(transcripts)} transcript chunks")
        
        return combined_transcript
    
    def _split_audio(self, audio: AudioSegment, chunk_duration_ms: int, overlap_ms: int) -> List[AudioSegment]:
        """Split audio into overlapping chunks."""
        chunks = []
        start = 0
        step = chunk_duration_ms - overlap_ms
        
        while start < len(audio):
            end = min(start + chunk_duration_ms, len(audio))
            chunk = audio[start:end]
            chunks.append(chunk)
            
            if end >= len(audio):
                break
                
            start += step
        
        return chunks
    
    def _combine_transcripts(self, transcripts: List[str]) -> str:
        """Combine transcript chunks, handling overlaps."""
        if not transcripts:
            return ""
        
        if len(transcripts) == 1:
            return transcripts[0]
        
        combined = transcripts[0]
        
        for i in range(1, len(transcripts)):
            current = transcripts[i]
            
            # Simple combination - just add with space
            # In a more sophisticated implementation, we could try to detect
            # and remove overlapping text based on the overlap seconds
            if combined and current:
                combined += " " + current
            elif current:
                combined = current
        
        return combined.strip()
    
    def _transcribe_with_openai(self, audio_path: Path) -> str:
        """Transcribe audio file using OpenAI API."""
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return response.strip()
        except Exception as e:
            self.logger.error(f"OpenAI API transcription failed: {e}")
            raise
    
    def _transcribe_large_file_with_openai(self, audio_path: Path) -> str:
        """Transcribe large audio file by splitting into chunks for OpenAI API."""
        # Load audio file
        audio = AudioSegment.from_file(str(audio_path))
        
        # OpenAI API has 25MB limit, so we use smaller chunks
        openai_chunk_size_mb = 20  # Leave some margin
        overlap_ms = self.config.overlap_seconds * 1000
        
        # Calculate chunk duration based on smaller size limit
        total_size_bytes = audio_path.stat().st_size
        chunk_size_bytes = openai_chunk_size_mb * 1024 * 1024
        chunk_duration_ms = int((len(audio) * chunk_size_bytes) / total_size_bytes)
        
        # Ensure minimum chunk duration
        chunk_duration_ms = max(chunk_duration_ms, 30000)  # At least 30 seconds
        
        self.logger.info(f"OpenAI API chunk duration: {chunk_duration_ms/1000:.1f} seconds, overlap: {overlap_ms/1000:.1f} seconds")
        
        chunks = self._split_audio(audio, chunk_duration_ms, overlap_ms)
        transcripts = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, chunk in enumerate(chunks):
                chunk_file = temp_path / f"chunk_{i:03d}.mp3"
                
                # Export chunk to temporary file (mp3 for better compression)
                chunk.export(str(chunk_file), format="mp3", bitrate="64k")
                
                # Check chunk file size
                chunk_size_mb = chunk_file.stat().st_size / (1024 * 1024)
                self.logger.info(f"Transcribing chunk {i+1}/{len(chunks)} ({len(chunk)/1000:.1f}s, {chunk_size_mb:.1f}MB) with OpenAI API")
                
                if chunk_size_mb > 25:
                    self.logger.warning(f"Chunk {i+1} still too large ({chunk_size_mb:.1f}MB), skipping")
                    transcripts.append("")
                    continue
                
                # Transcribe chunk with OpenAI API
                transcript = self._transcribe_with_openai(chunk_file)
                transcripts.append(transcript)
        
        # Combine transcripts
        combined_transcript = self._combine_transcripts(transcripts)
        self.logger.info(f"Combined {len(transcripts)} transcript chunks")
        
        return combined_transcript
    
    def get_output_path(self, episode: Episode) -> Path:
        """Get output path for transcript."""
        sanitized_title = episode.get_sanitized_title()
        date_str = episode.published_date.strftime("%Y%m%d")
        filename = f"{date_str}_{sanitized_title}.{self.config.output_format}"
        
        return Path(self.config.output_dir) / filename
    
    def save_transcript(self, transcript: str, episode: Episode) -> None:
        """Save transcript to file."""
        output_path = self.get_output_path(episode)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.output_format == "json":
            # Save as JSON with metadata
            data = {
                "title": episode.title,
                "published_date": episode.published_date.isoformat(),
                "duration": episode.duration,
                "audio_url": episode.audio_url,
                "transcript": transcript,
                "whisper_model": self.config.whisper_model
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif self.config.output_format == "markdown":
            # Save as Markdown with metadata
            content = f"""# {episode.title}

**Published:** {episode.published_date.strftime('%Y-%m-%d %H:%M:%S')}  
**Duration:** {episode.duration}  
**Audio URL:** {episode.audio_url}  
**Whisper Model:** {self.config.whisper_model}

## Transcript

{transcript}
"""
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        else:  # txt format
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
        
        self.logger.info(f"Transcript saved: {output_path}")

    def get_engine_name(self) -> str:
        """Get the name of the transcription engine being used."""
        if self.use_openai:
            return "openai_api"
        else:
            return "local_whisper"