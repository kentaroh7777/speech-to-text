"""RSS parser for fetching and filtering episodes."""

import logging
import requests
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List
from urllib.parse import urlparse

import feedparser

from .config import Episode

# Disable SSL certificate warnings and configure feedparser for SSL issues
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure SSL context for feedparser
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class RSSParser:
    """RSS feed parser for audio episodes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fetch_episodes(self, rss_url: str) -> List[Episode]:
        """Fetch episodes from RSS feed."""
        try:
            self.logger.info(f"Fetching RSS feed from: {rss_url}")
            
            # Use requests to fetch RSS content with SSL handling
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(rss_url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
            
            # Parse RSS feed from response content
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                self.logger.warning("No episodes found in RSS feed")
                return []
            
            episodes = []
            for entry in feed.entries:
                try:
                    episode = self._parse_entry(entry)
                    if episode:
                        episodes.append(episode)
                except Exception as e:
                    self.logger.warning(f"Failed to parse entry: {e}")
                    continue
            
            self.logger.info(f"Parsed {len(episodes)} episodes from RSS feed")
            return episodes
            
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed: {e}")
            raise
    
    def _parse_entry(self, entry) -> Episode:
        """Parse RSS entry into Episode object."""
        # Get title
        title = entry.get('title', 'Unknown Title')
        
        # Find audio URL (look for enclosures or links)
        audio_url = None
        
        # Check enclosures first (preferred)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type and 'audio' in enclosure.type:
                    audio_url = enclosure.href
                    break
        
        # Fallback to links
        if not audio_url and hasattr(entry, 'links'):
            for link in entry.links:
                if link.type and 'audio' in link.type:
                    audio_url = link.href
                    break
        
        # Last resort - use first link if it looks like audio
        if not audio_url and hasattr(entry, 'link'):
            link = entry.link
            if any(ext in link.lower() for ext in ['.mp3', '.m4a', '.wav', '.ogg']):
                audio_url = link
        
        if not audio_url:
            raise ValueError(f"No audio URL found for episode: {title}")
        
        # Parse published date
        published_date = self._parse_date(entry)
        
        # Get duration if available
        duration = ""
        if hasattr(entry, 'itunes_duration'):
            duration = entry.itunes_duration
        elif hasattr(entry, 'duration'):
            duration = str(entry.duration)
        
        return Episode(
            title=title,
            audio_url=audio_url,
            published_date=published_date,
            duration=duration
        )
    
    def _parse_date(self, entry) -> datetime:
        """Parse published date from RSS entry."""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                time_struct = getattr(entry, field)
                # Convert GMT to JST (+9 hours)
                utc_time = datetime(*time_struct[:6], tzinfo=timezone.utc)
                jst_time = utc_time.astimezone(timezone(timedelta(hours=9)))
                return jst_time.replace(tzinfo=None)  # Remove timezone info for comparison
        
        # Fallback to current time
        self.logger.warning(f"No date found for entry: {entry.get('title', 'Unknown')}")
        return datetime.now()
    
    def filter_by_date_range(self, episodes: List[Episode], date_range: str) -> List[Episode]:
        """Filter episodes by date range."""
        now = datetime.now()
        
        if date_range == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif date_range == "yesterday":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif date_range == "last-week":
            start_date = now - timedelta(days=7)
            end_date = now
        elif date_range == "latest":
            # Return the most recent episode(s)
            if not episodes:
                return []
            # Sort by date and return the latest
            sorted_episodes = sorted(episodes, key=lambda x: x.published_date, reverse=True)
            return [sorted_episodes[0]]
        else:
            # Unknown date range, return all
            self.logger.warning(f"Unknown date range: {date_range}, returning all episodes")
            return episodes
        
        filtered = [
            ep for ep in episodes 
            if start_date <= ep.published_date < end_date
        ]
        
        self.logger.info(f"Filtered to {len(filtered)} episodes for date range: {date_range}")
        return filtered