#!/usr/bin/env python3
"""Speech-to-text transcriber CLI."""

import click
import logging
from pathlib import Path
from .config import get_config
from .rss_parser import RSSParser
from .downloader import AudioDownloader
from .local_processor import find_audio_files
from .x_spaces_downloader import XSpacesDownloader  # 修正
from .transcriber import AudioTranscriber  # 正しいクラス名に修正

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--rss-url', help='RSS feed URL')
@click.option('--local-dir', help='Local directory containing audio files to transcribe')
@click.option('--X-space', help='X Spaces URL (space URL or tweet URL)')  # 修正
@click.option('--download-dir', default='downloads', help='Directory to save audio files')
@click.option('--output-dir', default='transcripts', help='Directory to save transcripts')
@click.option('--date-range', default='today',
              type=click.Choice(['today', 'yesterday', 'last-week', 'latest']),
              help='Date range for filtering episodes')
@click.option('--whisper-model', default='base', help='Whisper model to use')
@click.option('--delete-audio', is_flag=True, help='Delete downloaded audio files after transcription')
@click.option('--delete-original', is_flag=True, help='Delete original audio files after transcription')
@click.option('--use-openai-api', is_flag=True, help='Use OpenAI API for transcription')
@click.option('--openai-api-key', help='OpenAI API key (can also be set via OPENAI_API_KEY env var)')
@click.option('--no-openai-fallback', is_flag=True, help='Disable OpenAI API fallback if local Whisper fails')
def main(rss_url, local_dir, x_space, download_dir, output_dir, date_range, whisper_model, 
         delete_audio, delete_original, use_openai_api, openai_api_key, no_openai_fallback):
    """Speech-to-text transcriber CLI.
    
    Supports three input modes:
    1. RSS feeds (--rss-url)
    2. Local audio files (--local-dir) 
    3. X Spaces (--X-space)
    """
    try:
        # Validate input options - exactly one source must be specified
        input_sources = [rss_url, local_dir, x_space]
        specified_sources = [src for src in input_sources if src]
        
        if len(specified_sources) == 0:
            raise click.ClickException("Error: Must specify one of --rss-url, --local-dir, or --X-space")
        elif len(specified_sources) > 1:
            raise click.ClickException("Error: Can only specify one input source at a time")

        # Get configuration
        config = get_config(
            rss_url=rss_url,
            local_dir=local_dir,
            x_spaces_url=x_space,  # 修正
            download_dir=download_dir,
            output_dir=output_dir,
            date_range=date_range,
            whisper_model=whisper_model,
            delete_audio=delete_audio,
            delete_original=delete_original,
            use_openai_api=use_openai_api,
            openai_api_key=openai_api_key,
            openai_fallback=not no_openai_fallback
        )

        logger.info(f"Configuration: {config}")

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Process based on input source
        if local_dir:
            episodes = process_local_directory(config)
        elif rss_url:
            episodes = process_rss_feed(config)
        elif x_space:
            episodes = process_x_spaces(config)

        if not episodes:
            logger.warning("No episodes found to process")
            return

        # Initialize transcriber
        transcriber = AudioTranscriber(config)

        # Process each episode
        for episode in episodes:
            logger.info(f"Processing: {episode.title}")
            
            # Determine audio path
            if config.local_dir or config.x_spaces_url:  # 修正
                audio_path = Path(episode.audio_url)
            else:
                # Download audio file
                downloader = AudioDownloader(config)
                audio_path = downloader.download(episode)
                if not audio_path:
                    logger.error(f"Failed to download audio for: {episode.title}")
                    continue

            # Transcribe
            transcript = transcriber.transcribe(audio_path)
            if transcript:
                # Save transcript
                output_file = Path(config.output_dir) / f"{episode.published_date}_{episode.title.replace('/', '_')}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                logger.info(f"Transcript saved: {output_file}")

                # Clean up audio file if requested (only for downloaded files)
                if config.delete_audio and not config.local_dir:
                    try:
                        audio_path.unlink()
                        logger.info(f"Deleted audio file: {audio_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete audio file {audio_path}: {e}")
                
                # Clean up original audio file if requested (for X Spaces)
                if config.delete_original and config.x_spaces_url:  # 修正
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
    parser = RSSParser(config)
    return parser.parse()

if __name__ == "__main__":
    main()