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
import time
import subprocess
import json
import os
from pathlib import Path


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
        # Track whether last user id resolution used cache (to skip delay)
        self._used_cache_for_user_id: bool = False

    def find_latest(self) -> Optional[XSpaceMeta]:
        username = self._normalize_username(self.profile)
        self.logger.info(f"XSpacesApiFinder: resolving username '{username}'")
        user_id = self._fetch_user_id(username)
        if not user_id:
            self.logger.warning("XSpacesApiFinder: user not found or unauthorized")
            return None

        # Delay only if user id was fetched via API (not cache)
        if not getattr(self, "_used_cache_for_user_id", False):
            delay_ms = getattr(self, "api_call_delay_ms", 60000)
            if delay_ms and delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

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

    def find_ended_spaces(self) -> list[XSpaceMeta]:
        """Find multiple recorded (ended) spaces from recent tweets.
        Returns a list sorted by published_at (desc). Limited by search_limit and lookback_hours.
        """
        results: list[XSpaceMeta] = []
        username = self._normalize_username(self.profile)
        self.logger.info(f"XSpacesApiFinder: resolving username '{username}' for multiple spaces")
        user_id = self._fetch_user_id(username)
        if not user_id:
            self.logger.warning("XSpacesApiFinder: user not found or unauthorized")
            return results

        # Delay only if user id was fetched via API (not cache)
        if not getattr(self, "_used_cache_for_user_id", False):
            delay_ms = getattr(self, "api_call_delay_ms", 60000)
            if delay_ms and delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        params = {
            "max_results": min(self.search_limit, 100),
            "tweet.fields": "created_at,entities,text",
        }
        url = f"{base}/users/{user_id}/tweets"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout, params=params)
            if resp.status_code in (401, 403):
                self.logger.error(
                    "X API auth error (%s) when fetching tweets: url=%s params=%s headers=%s body=%s",
                    resp.status_code,
                    url,
                    params,
                    dict(resp.headers),
                    resp.text,
                )
                return results
            if resp.status_code == 429:
                self.logger.error(
                    "X API rate limited (429) when fetching tweets: url=%s params=%s",
                    url,
                    params,
                )
                self.logger.error("Headers: %s", dict(resp.headers))
                self.logger.error("Body: %s", resp.text)
                return results
            if resp.status_code != 200:
                self.logger.error(
                    "X API tweets lookup failed: HTTP %s, url=%s params=%s headers=%s body=%s",
                    resp.status_code,
                    url,
                    params,
                    dict(resp.headers),
                    resp.text,
                )
                return results
            data = resp.json()
            tweets = data.get("data", [])
            import re
            pattern = re.compile(r"https?://(?:x|twitter)\.com/i/spaces/([A-Za-z0-9]+)")
            seen: set[str] = set()
            for tw in tweets:
                created_at = tw.get("created_at")
                entities = tw.get("entities") or {}
                urls = entities.get("urls") or []
                for u in urls:
                    expanded = u.get("expanded_url") or u.get("url") or ""
                    m = pattern.search(expanded)
                    if not m:
                        continue
                    space_id = m.group(1)
                    if space_id in seen:
                        continue
                    seen.add(space_id)
                    # Probe via yt-dlp to ensure recorded (no X API meta)
                    space_url = f"https://x.com/i/spaces/{space_id}"
                    probed = self._probe_space_recorded(space_url)
                    if not probed["is_recorded"]:
                        continue
                    published_iso = probed.get("published_at_iso") or created_at
                    pivot = self._parse_dt(published_iso)
                    if pivot and pivot >= (datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)):
                        results.append(
                            XSpaceMeta(
                                url=space_url,
                                title=probed.get("title"),
                                published_at=published_iso,
                                tweet_id=tw.get("id"),
                            )
                        )
            # Sort by published time desc
            def _key(m: XSpaceMeta):
                dt = self._parse_dt(m.published_at or "")
                return dt or datetime.fromtimestamp(0, tz=timezone.utc)
            results.sort(key=_key, reverse=True)
            return results
        except Exception as e:
            self.logger.error("X API tweets lookup exception: %s", e)
            return results

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
        # Try cache first
        cached = self._load_cached_user_id(username)
        if cached:
            self.logger.info("XSpacesApiFinder: cache hit for username '%s' -> id %s", username, cached)
            self._used_cache_for_user_id = True
            return cached

        # Base URL configurable via Config (default: https://api.twitter.com/2)
        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        # Primary: new-style lookup
        url_new = f"{base}/users/by/username/{username}"
        # Fallback: legacy casing/alt path (some proxies re-map)
        url_legacy = f"{base}/users/by/username/{username}?user.fields=id,username"
        try:
            self._used_cache_for_user_id = False
            resp = requests.get(url_new, headers=self._headers(), timeout=self.timeout)
            if resp.status_code == 401 or resp.status_code == 403:
                self.logger.error(
                    "X API auth error (%s) when fetching user id: headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code == 429:
                self.logger.error(
                    "X API rate limited (429) when fetching user id: headers=%s body=%s",
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code != 200:
                self.logger.error(
                    "X API user lookup failed: HTTP %s; headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                # try fallback once
                resp2 = requests.get(url_legacy, headers=self._headers(), timeout=self.timeout)
                if resp2.status_code != 200:
                    self.logger.error(
                        "X API user lookup fallback failed: HTTP %s; headers=%s body=%s",
                        resp2.status_code,
                        dict(resp2.headers),
                        resp2.text,
                    )
                    return None
                data = resp2.json()
                uid = data.get("data", {}).get("id")
                if uid:
                    self._save_cached_user_id(username, uid)
                return uid
            data = resp.json()
            uid = data.get("data", {}).get("id")
            if uid:
                self._save_cached_user_id(username, uid)
            return uid
        except Exception as e:
            self.logger.error("X API user lookup exception: %s", e)
            return None

    # Cache helpers
    def _xid_cache_path(self) -> Path:
        return Path("/Users/taroken/src/git/speech-to-text/logs/xid.json")

    def _load_cached_user_id(self, username: str) -> Optional[str]:
        try:
            p = self._xid_cache_path()
            if not p.exists():
                return None
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None
            for entry in data:
                if isinstance(entry, dict) and entry.get("account") == username:
                    val = entry.get("id")
                    if isinstance(val, str) and val:
                        return val
            return None
        except Exception:
            return None

    def _save_cached_user_id(self, username: str, user_id: str) -> None:
        try:
            p = self._xid_cache_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            records: list = []
            if p.exists():
                try:
                    with p.open("r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            records = loaded
                except Exception:
                    records = []
            # update or append
            updated = False
            for e in records:
                if isinstance(e, dict) and e.get("account") == username:
                    e["id"] = user_id
                    updated = True
                    break
            if not updated:
                records.append({"account": username, "id": user_id})
            tmp = p.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)
        except Exception:
            # silent cache failure
            pass

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
                    "X API auth error (%s) when fetching spaces: headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code == 429:
                self.logger.error(
                    "X API rate limited (429) when fetching spaces: headers=%s body=%s",
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code != 200:
                self.logger.error(
                    "X API spaces lookup failed: HTTP %s, headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
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
                self.logger.error(
                    "X API auth error (%s) when fetching tweets: headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code == 429:
                # log full request context as well
                self.logger.error("X API rate limited (429) when fetching tweets: url=%s params=%s", url, params)
                self.logger.error("Headers: %s", dict(resp.headers))
                self.logger.error("Body: %s", resp.text)
                return None
            if resp.status_code != 200:
                self.logger.error(
                    "X API tweets lookup failed: HTTP %s, headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
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
                        # Probe via yt-dlp to ensure it's recorded (no X API meta)
                        space_url = f"https://x.com/i/spaces/{space_id}"
                        probed = self._probe_space_recorded(space_url)
                        if not probed["is_recorded"]:
                            continue
                        # Prefer probed timestamp; fallback to tweet created_at
                        published_iso = probed.get("published_at_iso") or created_at
                        # Filter by lookback window against ended_at/created_at
                        pivot = self._parse_dt(published_iso)
                        if pivot and pivot >= (datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)):
                            return XSpaceMeta(
                                url=space_url,
                                title=probed.get("title"),
                                published_at=published_iso,
                                tweet_id=tw.get("id"),
                            )
                        # If outside window, continue scanning others
            return None
        except Exception as e:
            self.logger.error("X API tweets lookup exception: %s", e)
            return None

    def _fetch_space_meta(self, space_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Was used to fetch space meta from X API.
        Retained for backward compatibility but no longer used when probing via yt-dlp.
        """
        # Space out consecutive API calls
        delay_ms = getattr(self, "api_call_delay_ms", 60000)
        if delay_ms and delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        base = getattr(self, "api_base", None) or "https://api.twitter.com/2"
        fields = [
            "state",
            "created_at",
            "started_at",
            "ended_at",
            "title",
            "lang",
            "host_ids",
            "participant_count",
        ]
        params = {"space.fields": ",".join(fields)}
        url = f"{base}/spaces/{space_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout, params=params)
            if resp.status_code in (401, 403):
                self.logger.error(
                    "X API auth error (%s) when fetching space meta: headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code == 429:
                self.logger.error(
                    "X API rate limited (429) when fetching space meta: headers=%s body=%s",
                    dict(resp.headers),
                    resp.text,
                )
                return None
            if resp.status_code != 200:
                self.logger.error(
                    "X API space meta lookup failed: HTTP %s, headers=%s body=%s",
                    resp.status_code,
                    dict(resp.headers),
                    resp.text,
                )
                return None
            data = resp.json().get("data")
            return data
        except Exception as e:
            self.logger.error("X API space meta lookup exception: %s", e)
            return None

