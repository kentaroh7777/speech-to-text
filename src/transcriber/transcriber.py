"""Audio transcription with chunking support."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

import whisper
from pydub import AudioSegment

from .config import Config, Episode


class AudioTranscriber:
    """Audio transcriber with chunking support for large files."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
    
    def _load_model(self):
        """Load Whisper model."""
        if self.model is None:
            self.logger.info(f"Loading Whisper model: {self.config.whisper_model}")
            self.model = whisper.load_model(self.config.whisper_model)
    
    def transcribe(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio file, splitting if necessary."""
        try:
            self._load_model()
            
            # Check file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Audio file size: {file_size_mb:.1f} MB")
            
            if file_size_mb <= self.config.chunk_size_mb:
                # File is small enough, transcribe directly
                self.logger.info("Transcribing audio file directly")
                return self._transcribe_file(audio_path)
            else:
                # File is too large, split and transcribe
                self.logger.info(f"File size exceeds {self.config.chunk_size_mb}MB, splitting into chunks")
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
    
    def get_output_path(self, episode: Episode) -> Path:
        """Get output path for transcript."""
        sanitized_title = episode.get_sanitized_title()
        date_str = episode.published_date.strftime("%Y%m%d")
        filename = f"{sanitized_title}_{date_str}.{self.config.output_format}"
        
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