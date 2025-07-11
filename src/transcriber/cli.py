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
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(
    rss_url: Optional[str],
    download_dir: Optional[str],
    output_dir: Optional[str],
    date_range: Optional[str],
    output_format: Optional[str],
    whisper_model: Optional[str],
    max_episodes: Optional[int],
    delete_audio: bool,
    debug: bool
) -> None:
    """Speech-to-text transcriber CLI."""
    setup_logging(debug)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = get_config(
            rss_url=rss_url,
            download_dir=download_dir,
            output_dir=output_dir,
            date_range=date_range,
            output_format=output_format,
            whisper_model=whisper_model,
            max_episodes=max_episodes,
            delete_audio=delete_audio
        )
        
        logger.info(f"Starting transcription with config: {config}")
        
        # Initialize components
        rss_parser = RSSParser()
        downloader = AudioDownloader(config.download_dir)
        transcriber = AudioTranscriber(config)
        
        # Fetch episodes from RSS
        logger.info(f"Fetching episodes from RSS: {config.rss_url}")
        episodes = rss_parser.fetch_episodes(config.rss_url)
        
        # Filter episodes by date range
        filtered_episodes = rss_parser.filter_by_date_range(episodes, config.date_range)
        
        # Limit number of episodes
        if config.max_episodes:
            filtered_episodes = filtered_episodes[:config.max_episodes]
        
        logger.info(f"Found {len(filtered_episodes)} episodes to process")
        
        # Process each episode
        for episode in filtered_episodes:
            logger.info(f"Processing episode: {episode.title}")
            
            # Check if transcript already exists
            output_path = transcriber.get_output_path(episode)
            if output_path.exists():
                logger.info(f"Skip - File already exists: {output_path}")
                continue
            
            # Download audio file
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
            
            # Delete audio file if requested
            if config.delete_audio:
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


if __name__ == '__main__':
    main()