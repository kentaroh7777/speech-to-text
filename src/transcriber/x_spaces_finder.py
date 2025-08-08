"""Finder for latest X Spaces using X API v2.

This module provides XSpacesApiFinder which resolves a username or profile URL
to user_id, queries Spaces by creator, and returns the latest ended (recorded)
space as a shareable URL usable by yt-dlp/ffmpeg.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests
import logging


@dataclass
class XSpaceMeta:
    url: str
    title: Optional[str]
    published_at: Optional[str]  # UTC ISO8601 string
    tweet_id: Optional[str]


class XSpacesApiFinder:
    def __init__(
        self,
        profile: str,
        search_limit: int,
        lookback_hours: int,
        bearer_token: str,
        request_timeout_ms: int,
    ) -> None:
        self.profile = profile.strip()
        self.search_limit = max(1, search_limit)
        self.lookback_hours = max(1, lookback_hours)
        self.bearer_token = bearer_token.strip()
        self.timeout = max(1000, request_timeout_ms) / 1000.0

        if not self.bearer_token:
            raise ValueError("X API Bearer token is required")

        self.logger = logging.getLogger(__name__)

    def find_latest(self) -> Optional[XSpaceMeta]:
        username = self._normalize_username(self.profile)
        self.logger.info(f"XSpacesApiFinder: resolving username '{username}'")
        user_id = self._fetch_user_id(username)
        if not user_id:
            self.logger.warning("XSpacesApiFinder: user not found or unauthorized")
            return None

        # Fetch recent tweets and detect latest space URL from URLs
        meta = self._fetch_latest_space_from_tweets(user_id)
        if meta:
            self.logger.info(
                "XSpacesApiFinder: selected space %s (published_at=%s)",
                meta.url,
                meta.published_at or "",
            )
        else:
            self.logger.info("XSpacesApiFinder: no space URL found in recent tweets")
        return meta

    # Internal helpers
    def _normalize_username(self, profile: str) -> str:
        if profile.startswith("http://") or profile.startswith("https://"):
            parsed = urlparse(profile)
            # path like /username or /username/status/123...
            path = (parsed.path or "/").lstrip("/")
            username = path.split("/")[0]
            return username
        # raw username (with or without @)
        return profile.lstrip("@")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "speech-to-text-x-finder/1.0",
        }

    def _fetch_user_id(self, username: str) -> Optional[str]:
        # Base URL configurable via Config (default: https://api.twitter.com/2)
        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        # Primary: new-style lookup
        url_new = f"{base}/users/by/username/{username}"
        # Fallback: legacy casing/alt path (some proxies re-map)
        url_legacy = f"{base}/users/by/username/{username}?user.fields=id,username"
        try:
            resp = requests.get(url_new, headers=self._headers(), timeout=self.timeout)
            if resp.status_code == 401 or resp.status_code == 403:
                self.logger.error("X API auth error (%s) when fetching user id", resp.status_code)
                return None
            if resp.status_code == 429:
                self.logger.error("X API rate limited (429) when fetching user id")
                return None
            if resp.status_code != 200:
                self.logger.error("X API user lookup failed: HTTP %s; body=%s", resp.status_code, resp.text)
                # try fallback once
                resp2 = requests.get(url_legacy, headers=self._headers(), timeout=self.timeout)
                if resp2.status_code != 200:
                    self.logger.error("X API user lookup fallback failed: HTTP %s; body=%s", resp2.status_code, resp2.text)
                    return None
                data = resp2.json()
                return data.get("data", {}).get("id")
            data = resp.json()
            return data.get("data", {}).get("id")
        except Exception as e:
            self.logger.error("X API user lookup exception: %s", e)
            return None

    def _fetch_spaces_by_creator(self, user_id: str) -> Optional[list[Dict[str, Any]]]:
        fields = [
            "state",
            "created_at",
            "scheduled_start",
            "started_at",
            "ended_at",
            "title",
            "lang",
            "host_ids",
            "participant_count",
        ]
        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        # Per /2/spaces/by/creator_ids spec, only send supported params
        params = {
            "user_ids": user_id,
            "space.fields": ",".join(fields),
        }

        try:
            resp = requests.get(
                f"{base}/spaces/by/creator_ids",
                headers=self._headers(),
                timeout=self.timeout,
                params=params,
            )
            if resp.status_code in (401, 403):
                self.logger.error(
                    "X API auth error (%s) when fetching spaces: %s",
                    resp.status_code,
                    resp.text,
                )
                return None
            if resp.status_code == 429:
                self.logger.error("X API rate limited (429) when fetching spaces")
                return None
            if resp.status_code != 200:
                self.logger.error(
                    "X API spaces lookup failed: HTTP %s, body=%s",
                    resp.status_code,
                    resp.text,
                )
                return None
            data = resp.json()
            spaces = data.get("data", [])
            self.logger.info("XSpacesApiFinder: request params used: %s", params)
            self.logger.info("XSpacesApiFinder: raw response body: %s", resp.text)
            self.logger.info("XSpacesApiFinder: API returned %d spaces", len(spaces))
            return spaces
        except Exception as e:
            self.logger.error("X API spaces lookup exception: %s", e)
            return None

    def _parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            # Accept Z or +00:00 style
            norm = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(norm)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def _fetch_latest_space_from_tweets(self, user_id: str) -> Optional[XSpaceMeta]:
        """Fetch recent tweets and find latest X Spaces URL.
        Scans tweet.entities.urls.expanded_url for https://x.com/i/spaces/<id> (or twitter.com).
        """
        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        params = {
            "max_results": min(self.search_limit, 100),
            "tweet.fields": "created_at,entities,text",
        }
        url = f"{base}/users/{user_id}/tweets"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout, params=params)
            if resp.status_code in (401, 403):
                self.logger.error("X API auth error (%s) when fetching tweets: %s", resp.status_code, resp.text)
                return None
            if resp.status_code == 429:
                self.logger.error("X API rate limited (429) when fetching tweets")
                return None
            if resp.status_code != 200:
                self.logger.error("X API tweets lookup failed: HTTP %s, body=%s", resp.status_code, resp.text)
                return None
            data = resp.json()
            tweets = data.get("data", [])
            # Debug: remove raw tweets body dump for normal run (kept minimal)
            self.logger.info("XSpacesApiFinder: request params used (tweets): %s", params)
            # Tweets are returned most-recent first; scan in order
            import re
            pattern = re.compile(r"https?://(?:x|twitter)\.com/i/spaces/([A-Za-z0-9]+)")
            for tw in tweets:
                created_at = tw.get("created_at")
                entities = tw.get("entities") or {}
                urls = entities.get("urls") or []
                for u in urls:
                    expanded = u.get("expanded_url") or u.get("url") or ""
                    m = pattern.search(expanded)
                    if m:
                        space_id = m.group(1)
                        space_url = f"https://x.com/i/spaces/{space_id}"
                        # Filter by lookback window
                        pivot = self._parse_dt(created_at)
                        if pivot and pivot >= (datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)):
                            return XSpaceMeta(url=space_url, title=None, published_at=created_at, tweet_id=tw.get("id"))
                        # If outside window, continue scanning others
            return None
        except Exception as e:
            self.logger.error("X API tweets lookup exception: %s", e)
            return None

