"""CLI entry point for speech-to-text transcriber."""

import click
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import Config, get_config
from .rss_parser import RSSParser
from .downloader import AudioDownloader
from .transcriber import AudioTranscriber
from .local_processor import LocalFileProcessor


def setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


@click.command()
@click.option('--rss-url', help='RSS feed URL')
@click.option('--local-dir', help='Local directory containing audio files to transcribe')
@click.option('--download-dir', help='Directory to save audio files')
@click.option('--output-dir', help='Directory to save transcripts')
@click.option('--date-range', 
              type=click.Choice(['today', 'yesterday', 'last-week', 'latest']),
              help='Date range for episodes')
@click.option('--output-format', 
              type=click.Choice(['txt', 'markdown', 'json']),
              help='Output format')
@click.option('--whisper-model', 
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              help='Whisper model to use (tiny: fastest/lowest quality, large: slowest/highest quality)')
@click.option('--max-episodes', type=int, help='Maximum number of episodes to process')
@click.option('--delete-audio', is_flag=True, help='Delete audio files after successful transcription')
@click.option('--use-openai-api', is_flag=True, help='Force use of OpenAI API instead of local Whisper')
@click.option('--openai-api-key', help='OpenAI API key (can also be set via OPENAI_API_KEY env var)')
@click.option('--no-openai-fallback', is_flag=True, help='Disable OpenAI API fallback when local Whisper fails')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(
    rss_url: Optional[str],
    local_dir: Optional[str],
    download_dir: Optional[str],
    output_dir: Optional[str],
    date_range: Optional[str],
    output_format: Optional[str],
    whisper_model: Optional[str],
    max_episodes: Optional[int],
    delete_audio: bool,
    use_openai_api: bool,
    openai_api_key: Optional[str],
    no_openai_fallback: bool,
    debug: bool
) -> None:
    """Speech-to-text transcriber CLI."""
    setup_logging(debug)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate input options - prioritize local-dir if specified
        if local_dir:
            # Local directory mode - ignore RSS URL even if specified
            logger.info("Local directory mode selected, ignoring RSS URL if specified")
        elif not rss_url:
            # If no local-dir and no RSS URL, show error
            logger.error("Must specify either --local-dir for local files or --rss-url for RSS feed.")
            sys.exit(1)
        
        # Load configuration
        config = get_config(
            rss_url=rss_url,
            download_dir=download_dir,
            output_dir=output_dir,
            date_range=date_range,
            output_format=output_format,
            whisper_model=whisper_model,
            max_episodes=max_episodes,
            delete_audio=delete_audio,
            openai_api_key=openai_api_key,
            use_openai_api=use_openai_api,
            openai_fallback=not no_openai_fallback
        )
        
        logger.info(f"Starting transcription with config: {config}")
        
        # Initialize transcriber
        transcriber = AudioTranscriber(config)
        
        # Get episodes from either RSS or local directory
        if local_dir:
            episodes = process_local_directory(local_dir, config, logger)
        else:
            episodes = process_rss_feed(config, logger)
        
        # Limit number of episodes
        if config.max_episodes:
            episodes = episodes[:config.max_episodes]
        
        logger.info(f"Found {len(episodes)} episodes to process")
        
        # Process each episode
        for episode in episodes:
            logger.info(f"Processing episode: {episode.title}")
            
            # Check if transcript already exists
            output_path = transcriber.get_output_path(episode)
            if output_path.exists():
                logger.info(f"Skip - File already exists: {output_path}")
                continue
            
            # For local files, audio_path is already the local file path
            if local_dir:
                audio_path = Path(episode.audio_url)
                if not audio_path.exists():
                    logger.error(f"Local audio file not found: {audio_path}")
                    continue
            else:
                # Download audio file from RSS
                downloader = AudioDownloader(config.download_dir)
                audio_path = downloader.download(episode.audio_url, episode.title, episode.published_date)
                if not audio_path:
                    logger.error(f"Failed to download audio for: {episode.title}")
                    continue
            
            # Transcribe audio
            transcript = transcriber.transcribe(audio_path)
            if not transcript:
                logger.error(f"Failed to transcribe audio for: {episode.title}")
                continue
            
            # Save transcript
            transcriber.save_transcript(transcript, episode)
            logger.info(f"Transcript saved: {output_path}")
            
            # Delete audio file if requested (only for downloaded files, not local originals)
            if config.delete_audio and not local_dir:
                try:
                    audio_path.unlink()
                    logger.info(f"Deleted audio file: {audio_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path.name}: {e}")
        
        logger.info("Transcription completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if debug:
            logger.exception("Full traceback:")
        sys.exit(1)


def process_local_directory(local_dir: str, config: Config, logger) -> list:
    """Process local directory to find audio files."""
    logger.info(f"Processing local directory: {local_dir}")
    
    local_processor = LocalFileProcessor()
    local_path = Path(local_dir)
    
    # Find audio files in the directory
    episodes = local_processor.find_audio_files(local_path, config.date_range)
    
    return episodes


def process_rss_feed(config: Config, logger) -> list:
    """Process RSS feed to get episodes."""
    logger.info(f"Fetching episodes from RSS: {config.rss_url}")
    
    # Initialize RSS components
    rss_parser = RSSParser()
    
    # Fetch episodes from RSS
    episodes = rss_parser.fetch_episodes(config.rss_url)
    
    # Filter episodes by date range
    filtered_episodes = rss_parser.filter_by_date_range(episodes, config.date_range)
    
    return filtered_episodes


if __name__ == '__main__':
    main()