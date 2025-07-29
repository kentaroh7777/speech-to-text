"""Local audio file processor for speech-to-text transcriber."""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .config import Episode


class LocalFileProcessor:
    """Process local audio files for transcription."""
    
    # 対応する音声ファイル拡張子
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_audio_files(self, directory: Path, date_range: str = "today") -> List[Episode]:
        """Find audio files in directory and convert to Episode objects."""
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        self.logger.info(f"Scanning directory: {directory}")
        
        # Find all audio files
        audio_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.AUDIO_EXTENSIONS:
                audio_files.append(file_path)
        
        self.logger.info(f"Found {len(audio_files)} audio files")
        
        # Convert to Episode objects and track date sources
        episodes = []
        filename_date_count = 0
        mtime_date_count = 0
        
        for file_path in audio_files:
            episode = self._file_to_episode(file_path)
            if episode:
                episodes.append(episode)
                # Count date sources for statistics
                if hasattr(episode, 'date_source'):
                    if episode.date_source == "filename":
                        filename_date_count += 1
                    elif episode.date_source == "file_mtime":
                        mtime_date_count += 1
        
        # Log date source statistics
        if filename_date_count > 0 and mtime_date_count > 0:
            self.logger.info(f"Date sources: {filename_date_count} from filename, {mtime_date_count} from file modification time")
        elif mtime_date_count > 0:
            self.logger.info(f"All {mtime_date_count} files using file modification time (no dates in filenames)")
        elif filename_date_count > 0:
            self.logger.info(f"All {filename_date_count} files using filename dates")
        
        # Filter by date range
        filtered_episodes = self._filter_by_date_range(episodes, date_range)
        
        self.logger.info(f"After date filtering: {len(filtered_episodes)} files")
        
        # Sort by date (newest first)
        filtered_episodes.sort(key=lambda e: e.published_date, reverse=True)
        
        return filtered_episodes
    
    def _file_to_episode(self, file_path: Path) -> Optional[Episode]:
        """Convert file path to Episode object."""
        try:
            # Extract date from filename
            published_date = self._extract_date_from_filename(file_path.name)
            date_source = "filename"
            
            if not published_date:
                # If no date in filename, use file modification time
                published_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_source = "file_mtime"
                self.logger.debug(f"No date found in filename '{file_path.name}', using file modification time: {published_date}")
            else:
                self.logger.debug(f"Date extracted from filename '{file_path.name}': {published_date}")
            
            # Use filename (without extension) as title
            title = file_path.stem
            
            # Create Episode object with local file path as audio_url
            episode = Episode(
                title=title,
                audio_url=str(file_path.absolute()),
                published_date=published_date,
                duration=""  # Duration will be determined during transcription if needed
            )
            
            # Add metadata about date source for debugging
            episode.date_source = date_source
            
            return episode
            
        except Exception as e:
            self.logger.warning(f"Failed to process file {file_path}: {e}")
            return None
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename using various patterns."""
        # Common date patterns in filenames
        patterns = [
            r'(\d{8})',  # YYYYMMDD
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{4}_\d{2}_\d{2})',  # YYYY_MM_DD
            r'(\d{4}\d{2}\d{2})',  # YYYYMMDD (at start)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                try:
                    if '-' in date_str:
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    elif '_' in date_str:
                        return datetime.strptime(date_str, '%Y_%m_%d')
                    elif len(date_str) == 8:
                        return datetime.strptime(date_str, '%Y%m%d')
                except ValueError:
                    continue
        
        return None
    
    def _filter_by_date_range(self, episodes: List[Episode], date_range: str) -> List[Episode]:
        """Filter episodes by date range."""
        if date_range == "latest":
            # Return only the latest file
            # If multiple files have the same date, prioritize by file modification time
            if episodes:
                latest = self._get_latest_episode(episodes)
                return [latest]
            return []
        
        now = datetime.now()
        
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
            # Unknown date range, return all
            self.logger.debug(f"Unknown date range '{date_range}', returning all files")
            return episodes
        
        self.logger.debug(f"Date range: {start_date} to {end_date}")
        
        filtered = []
        for episode in episodes:
            self.logger.debug(f"Episode '{episode.title}' date: {episode.published_date}")
            if start_date <= episode.published_date < end_date:
                filtered.append(episode)
                self.logger.debug(f"  -> Included")
            else:
                self.logger.debug(f"  -> Excluded (outside date range)")
        
        return filtered
    
    def _get_latest_episode(self, episodes: List[Episode]) -> Episode:
        """Get the latest episode, prioritizing file modification time for same-date files."""
        from pathlib import Path
        
        # First, find the latest date
        latest_date = max(episodes, key=lambda e: e.published_date.date()).published_date.date()
        
        # Filter episodes with the latest date
        latest_date_episodes = [
            e for e in episodes 
            if e.published_date.date() == latest_date
        ]
        
        self.logger.debug(f"Found {len(latest_date_episodes)} files with latest date {latest_date}")
        
        # If only one episode with latest date, return it
        if len(latest_date_episodes) == 1:
            return latest_date_episodes[0]
        
        # Multiple episodes with same date - prioritize by file modification time
        self.logger.debug("Multiple files with same date, checking file modification times")
        
        def get_file_mtime(episode: Episode) -> float:
            """Get file modification time."""
            try:
                file_path = Path(episode.audio_url)
                if file_path.exists():
                    mtime = file_path.stat().st_mtime
                    self.logger.debug(f"  {episode.title}: mtime = {datetime.fromtimestamp(mtime)}")
                    return mtime
                else:
                    self.logger.warning(f"File not found: {file_path}")
                    return 0
            except Exception as e:
                self.logger.warning(f"Error getting mtime for {episode.title}: {e}")
                return 0
        
        # Return episode with latest modification time
        latest_episode = max(latest_date_episodes, key=get_file_mtime)
        self.logger.debug(f"Selected latest file: {latest_episode.title}")
        
        return latest_episode 