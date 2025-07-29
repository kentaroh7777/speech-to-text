#!/usr/bin/env python3
"""Speech-to-text transcriber CLI."""

import click
import logging
import time
from pathlib import Path
from datetime import datetime
from .config import get_config, TranscriptResult
from .rss_parser import RSSParser
from .downloader import AudioDownloader
from .local_processor import find_audio_files
from .x_spaces_downloader import XSpacesDownloader  # 修正
from .transcriber import AudioTranscriber  # 正しいクラス名に修正

# Try to import pydub for duration extraction
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_broadcast_datetime(episode) -> str:
    """Get broadcast datetime from episode, handling different data types."""
    if hasattr(episode, 'published_date'):
        pub_date = episode.published_date
        if hasattr(pub_date, 'strftime'):
            # datetime object (from RSS) - return full datetime
            return pub_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # string (from local files or X Spaces) - return as is
            return str(pub_date)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds."""
    if not PYDUB_AVAILABLE:
        return 0.0
    
    try:
        audio = AudioSegment.from_file(str(audio_path))
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0

def save_transcript(result: TranscriptResult, config, episode):
    """Save transcript based on configuration."""
    sanitized_title = episode.title.replace('/', '_').replace('?', '_').replace(':', '_')
    
    # Handle published_date (could be datetime or string)
    if hasattr(episode.published_date, 'strftime'):
        date_str = episode.published_date.strftime('%Y%m%d')
    else:
        date_str = str(episode.published_date)
    
    if config.output_format == 'json':
        output_file = Path(config.output_dir) / f"{date_str}_{sanitized_title}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.to_json())
        logger.info(f"Transcript saved (JSON): {output_file}")
    else:
        output_file = Path(config.output_dir) / f"{date_str}_{sanitized_title}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.transcript)
        logger.info(f"Transcript saved (TXT): {output_file}")

@click.command()
@click.option('--rss-url', help='RSS feed URL')
@click.option('--local-dir', help='Local directory containing audio files to transcribe')
@click.option('--X-space', help='X Spaces URL (space URL or tweet URL)')  # 修正
@click.option('--download-dir', default='downloads', help='Directory to save audio files')
@click.option('--output-dir', default='transcripts', help='Directory to save transcripts')
@click.option('--output-format', type=click.Choice(['txt', 'json']), default='txt',
              help='Output format: txt or json (default: txt)')
@click.option('--date-range', default='today',
              type=click.Choice(['today', 'yesterday', 'last-week', 'latest']),
              help='Date range for filtering episodes')
@click.option('--whisper-model', default='base',
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              help='Whisper model size')
@click.option('--max-episodes', default=5, type=int,
              help='Maximum number of episodes to process')
@click.option('--chunk-size-mb', default=25, type=int,
              help='Audio chunk size in MB for processing')
@click.option('--overlap-seconds', default=15, type=int,
              help='Overlap seconds between chunks')
@click.option('--delete-audio', is_flag=True, help='Delete audio files after transcription')
@click.option('--delete-original', is_flag=True, help='Delete original audio files from downloads')
@click.option('--use-openai-api', is_flag=True, help='Use OpenAI API for transcription')
@click.option('--openai-api-key', help='OpenAI API key (can also be set via OPENAI_API_KEY env var)')
@click.option('--openai-fallback/--no-openai-fallback', default=True,
              help='Enable/disable OpenAI API fallback when local Whisper fails (default: enabled)')
@click.option('--author', type=str, default='',
              help='Author name for JSON metadata (can be set via STT_AUTHOR env var)')
@click.option('--contact', type=str, default='',
              help='Contact info for JSON metadata (can be set via STT_CONTACT env var)')
def main(rss_url, local_dir, x_space, download_dir, output_dir, date_range,
         whisper_model, max_episodes, chunk_size_mb, overlap_seconds,
         delete_audio, delete_original, use_openai_api, openai_api_key,
         openai_fallback, output_format, author, contact):
    """Speech-to-text transcriber CLI.
    
    Supports three input modes:
    1. RSS feeds (--rss-url or STT_RSS_URL env var)
    2. Local audio files (--local-dir or STT_LOCAL_DIR env var) 
    3. X Spaces (--X-space or STT_X_SPACES_URL env var)
    """
    try:
        # Validate CLI input options first (before considering environment variables)
        cli_input_sources = [rss_url, local_dir, x_space]
        specified_cli_sources = [src for src in cli_input_sources if src]
        
        if len(specified_cli_sources) > 1:
            raise click.ClickException("Error: Can only specify one input source at a time")

        # Get configuration (includes environment variables as fallback)
        config = get_config(
            rss_url=rss_url,
            local_dir=local_dir,
            x_spaces_url=x_space,
            download_dir=download_dir,
            output_dir=output_dir,
            date_range=date_range,
            output_format=output_format,
            whisper_model=whisper_model,
            max_episodes=max_episodes,
            chunk_size_mb=chunk_size_mb,
            overlap_seconds=overlap_seconds,
            delete_audio=delete_audio,
            delete_original=delete_original,
            use_openai_api=use_openai_api,
            openai_api_key=openai_api_key,
            openai_fallback=openai_fallback,
            author=author,
            contact=contact
        )

        # Final validation: ensure at least one source is available (CLI or env vars)
        final_input_sources = [config.rss_url, config.local_dir, config.x_spaces_url]
        specified_final_sources = [src for src in final_input_sources if src]
        
        if len(specified_final_sources) == 0:
            raise click.ClickException("Error: Must specify one of --rss-url, --local-dir, or --X-space (or set environment variables STT_RSS_URL, STT_LOCAL_DIR, or STT_X_SPACES_URL)")

        logger.debug(f"Configuration: {config}")

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Process based on input source
        if config.local_dir:
            episodes = process_local_directory(config)
        elif config.rss_url:
            episodes = process_rss_feed(config)
        elif config.x_spaces_url:
            episodes = process_x_spaces(config)

        if not episodes:
            logger.warning("No episodes found to process")
            return

        # Initialize transcriber
        transcriber = AudioTranscriber(config)

        # Process each episode
        for episode in episodes:
            logger.info(f"Processing: {episode.title}")
            
            # Record start time
            start_time = time.time()
            processing_start = datetime.now()
            
            # Determine audio path and source type
            if config.local_dir:
                audio_path = Path(episode.audio_url)
                source = audio_path.name  # ファイル名のみ（セキュリティ考慮）
            elif config.x_spaces_url:
                audio_path = Path(episode.audio_url)
                source = config.x_spaces_url
            else:
                # Download audio file
                downloader = AudioDownloader(config.download_dir)
                audio_path = downloader.download(episode.audio_url, episode.title, episode.published_date)
                source = config.rss_url
                if not audio_path:
                    logger.error(f"Failed to download audio for: {episode.title}")
                    continue

            # Get file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024) if audio_path.exists() else 0.0
            
            # Get audio duration
            duration_seconds = get_audio_duration(audio_path)
            
            # Get broadcast datetime
            broadcast_date = get_broadcast_datetime(episode)

            # Transcribe
            transcript = transcriber.transcribe(audio_path)
            if transcript:
                # Calculate processing time
                end_time = time.time()
                processing_time = f"{end_time - start_time:.1f}s"
                
                # Create structured result
                result = TranscriptResult(
                    transcript=transcript,
                    filename=episode.title,
                    date=broadcast_date,
                    source=source,
                    duration=round(duration_seconds, 1),
                    size_mb=round(file_size_mb, 2),
                    model=config.whisper_model,
                    engine=transcriber.get_engine_name(),
                    processed_at=processing_start.strftime("%Y-%m-%d %H:%M:%S"),
                    processing_time=processing_time,
                    author=config.author,
                    contact=config.contact
                )
                
                # Save transcript in requested format
                save_transcript(result, config, episode)

                # Clean up audio file if requested (only for downloaded files)
                if config.delete_audio and not config.local_dir:
                    try:
                        audio_path.unlink()
                        logger.info(f"Deleted audio file: {audio_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete audio file {audio_path}: {e}")
                
                # Clean up original audio file if requested (for X Spaces)
                if config.delete_original and config.x_spaces_url:
                    try:
                        audio_path.unlink()
                        logger.info(f"Deleted original audio file: {audio_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete original audio file {audio_path}: {e}")
            else:
                logger.error(f"Failed to transcribe: {episode.title}")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))

def process_x_spaces(config):
    """Process X Spaces URL and return episodes."""
    logger.info(f"Processing X Spaces: {config.x_spaces_url}")
    
    downloader = XSpacesDownloader(config)
    episode = downloader.download_and_convert(config.x_spaces_url)
    
    if episode:
        return [episode]
    else:
        logger.error("Failed to download from X Spaces")
        return []

def process_local_directory(config):
    """Process local directory."""
    logger.info(f"Processing local directory: {config.local_dir}")
    return find_audio_files(Path(config.local_dir), config.date_range)

def process_rss_feed(config):
    """Process RSS feed."""
    logger.info(f"Processing RSS feed: {config.rss_url}")
    parser = RSSParser()
    episodes = parser.fetch_episodes(config.rss_url)
    return parser.filter_by_date_range(episodes, config.date_range)

if __name__ == "__main__":
    main()