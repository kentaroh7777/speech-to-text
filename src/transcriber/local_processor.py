"""Local audio file processing for speech-to-text transcriber."""

import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
from .config import Episode

logger = logging.getLogger(__name__)

def find_audio_files(directory: Path, date_range: str) -> List[Episode]:
    """Find and filter audio files in the specified directory."""
    logger.info(f"Scanning directory: {directory}")
    logger.info(f"Date range filter: {date_range}")
    
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return []
    
    # Supported audio extensions
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
    
    # Find all audio files
    episodes = []
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
            episode = _file_to_episode(file_path)
            episodes.append(episode)
    
    logger.info(f"Found {len(episodes)} audio files")
    
    # Filter by date range
    filtered_episodes = _filter_by_date_range(episodes, date_range)
    logger.info(f"After date filtering: {len(filtered_episodes)} files")
    
    # Log episode details for debugging
    for episode in filtered_episodes:
        logger.debug(f"Episode: {episode.title}, Date: {episode.published_date}, Source: {episode.date_source}")
    
    return filtered_episodes

def _file_to_episode(file_path: Path) -> Episode:
    """Convert a file path to an Episode object."""
    # Try to extract date from filename
    filename = file_path.stem
    extracted_date = _extract_date_from_filename(filename)
    
    if extracted_date:
        published_date = extracted_date
        date_source = "filename"
    else:
        # Use file modification time if no date in filename
        mtime = file_path.stat().st_mtime
        published_date = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        date_source = "mtime"
    
    # Get file modification time for latest sorting
    st_mtime = file_path.stat().st_mtime
    
    episode = Episode(
        title=filename,
        audio_url=str(file_path.absolute()),
        published_date=published_date,
        duration=""
    )
    
    # Add custom attributes for local processing
    episode.date_source = date_source
    episode.st_mtime = st_mtime
    
    return episode

def _extract_date_from_filename(filename: str) -> str:
    """Extract date from filename in YYYYMMDD format."""
    # Pattern for YYYYMMDD (20240729)
    pattern1 = r'(\d{4})(\d{2})(\d{2})'
    match1 = re.search(pattern1, filename)
    if match1:
        return match1.group(1) + match1.group(2) + match1.group(3)
    
    # Pattern for YYYY-MM-DD or YYYY_MM_DD
    pattern2 = r'(\d{4})[-_](\d{2})[-_](\d{2})'
    match2 = re.search(pattern2, filename)
    if match2:
        return match2.group(1) + match2.group(2) + match2.group(3)
    
    return ""

def _filter_by_date_range(episodes: List[Episode], date_range: str) -> List[Episode]:
    """Filter episodes by date range."""
    now = datetime.now()
    
    if date_range == "latest":
        return _get_latest_episode(episodes)
    
    # Calculate date boundaries
    if date_range == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif date_range == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif date_range == "last-week":
        start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    else:
        logger.warning(f"Unknown date range: {date_range}, returning all episodes")
        return episodes
    
    # Filter episodes
    filtered = []
    for episode in episodes:
        try:
            episode_date = datetime.strptime(episode.published_date, "%Y%m%d")
            logger.debug(f"Checking episode {episode.title}: {episode_date} in range {start_date} - {end_date}")
            if start_date <= episode_date < end_date:
                filtered.append(episode)
                logger.debug(f"  -> Included")
            else:
                logger.debug(f"  -> Excluded (outside date range)")
        except ValueError:
            logger.warning(f"Invalid date format for episode {episode.title}: {episode.published_date}")
    
    return filtered

def _get_latest_episode(episodes: List[Episode]) -> List[Episode]:
    """Get the latest episode(s). If multiple episodes have the same date, return the one with the most recent mtime."""
    if not episodes:
        return []
    
    # Sort by published_date first, then by st_mtime for tie-breaking
    sorted_episodes = sorted(episodes, key=lambda e: (e.published_date, e.st_mtime), reverse=True)
    
    latest_date = sorted_episodes[0].published_date
    logger.debug(f"Latest date found: {latest_date}")
    
    # Get all episodes with the latest date
    latest_episodes = [ep for ep in sorted_episodes if ep.published_date == latest_date]
    
    if len(latest_episodes) > 1:
        # Multiple files with same date - return the one with most recent mtime
        latest_episode = max(latest_episodes, key=lambda e: e.st_mtime)
        logger.debug(f"Multiple episodes on {latest_date}, selected by mtime: {latest_episode.title}")
        return [latest_episode]
    else:
        logger.debug(f"Single latest episode: {latest_episodes[0].title}")
        return latest_episodes 