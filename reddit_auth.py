# -*- coding: utf-8 -*-
"""
Reddit authentication helper for Sherlock.
"""

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import find_dotenv, load_dotenv
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, RequestException, Timeout

# Resolve .env relative to the repo root (where this file lives)
DOTENV_PATH = find_dotenv()
if DOTENV_PATH:
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class TokenExpiredError(Exception):
    """Raised when access token has expired."""


class RateLimitError(Exception):
    """Raised when the API rate limit is exceeded."""


class RedditAuthenticator:
    """
    Handles OAuth2 authentication for the Reddit API using the client
    credentials flow.
    """

    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    BASE_URL = "https://oauth.reddit.com"

    # Reddit allows 600 requests per 10 minutes – stay under that aggressively.
    MAX_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(self):
        dotenv_hint = DOTENV_PATH or Path(".env").resolve()
        self.client_id = os.environ.get("REDDIT_CLIENT_ID")
        self.client_secret = os.environ.get("REDDIT_SECRET")
        self.user_agent = os.environ.get("REDDIT_USER_AGENT", "sherlock/1.0")

        if not self.client_id or not self.client_secret:
            hint = (
                f"Ensure REDDIT_CLIENT_ID/REDDIT_SECRET are set in your environment "
                f"or .env file ({dotenv_hint})."
            )
            raise AuthenticationError(
                "REDDIT_CLIENT_ID and REDDIT_SECRET must be set in environment variables. "
                + hint
            )

        self.access_token = None
        self.token_expires_at = None
        self.requests_this_window = 0
        self.window_start_time = time.time()
        self.session = requests.Session()

    def _is_token_expired(self):
        if not self.token_expires_at:
            return True
        # refresh one minute before expiry to be safe
        return time.time() >= (self.token_expires_at - 60)

    def _reset_rate_limit_window(self):
        now = time.time()
        if now - self.window_start_time >= self.RATE_LIMIT_WINDOW:
            self.requests_this_window = 0
            self.window_start_time = now

    def _check_rate_limit(self):
        self._reset_rate_limit_window()
        if self.requests_this_window >= self.MAX_REQUESTS_PER_MINUTE:
            raise RateLimitError(
                "Rate limit exceeded. Please wait before making more requests."
            )

    def _increment_request_count(self):
        self._reset_rate_limit_window()
        self.requests_this_window += 1

    def authenticate(self):
        """
        Obtain an access token using the client credentials flow.
        """
        logger.info("Authenticating with Reddit API...")

        data = {"grant_type": "client_credentials"}
        auth = HTTPBasicAuth(self.client_id, self.client_secret)
        headers = {"User-Agent": self.user_agent}

        try:
            response = self.session.post(
                self.TOKEN_URL,
                auth=auth,
                data=data,
                headers=headers,
                timeout=30,
            )
        except (Timeout, ConnectionError) as exc:
            logger.error("Network error during authentication: %s", exc)
            raise AuthenticationError(str(exc)) from exc
        except RequestException as exc:
            logger.error("Request error during authentication: %s", exc)
            raise AuthenticationError(str(exc)) from exc

        if response.status_code != 200:
            error_msg = (
                f"Authentication failed with status {response.status_code}: "
                f"{response.text}"
            )
            logger.error(error_msg)
            raise AuthenticationError(error_msg)

        token_data = response.json()
        self.access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        self.token_expires_at = time.time() + expires_in
        logger.info("Successfully authenticated with Reddit API.")
        return self.access_token

    def _ensure_valid_token(self):
        if not self.access_token or self._is_token_expired():
            logger.info("Access token missing/expired; refreshing...")
            self.authenticate()

    def get_headers(self):
        """
        Return the headers required to call the Reddit API.
        """
        self._ensure_valid_token()
        return {
            "Authorization": f"bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

    def make_request(
        self,
        endpoint,
        params=None,
        max_retries=3,
        backoff_factor=2,
    ):
        """
        Make an authenticated GET request with retry and rate-limit handling.
        """
        self._check_rate_limit()
        self._ensure_valid_token()

        url = f"{self.BASE_URL}{endpoint}"
        headers = self.get_headers()

        for attempt in range(max_retries + 1):
            try:
                logger.debug("GET %s (attempt %s)", url, attempt + 1)
                response = self.session.get(
                    url, headers=headers, params=params, timeout=30
                )
                self._increment_request_count()
            except (Timeout, ConnectionError) as exc:
                if attempt < max_retries:
                    wait = backoff_factor**attempt
                    logger.warning(
                        "Network error (%s). Retrying in %s seconds.", exc, wait
                    )
                    time.sleep(wait)
                    continue
                raise RequestException(
                    f"Network error after {max_retries + 1} attempts: {exc}"
                ) from exc
            except RequestException as exc:
                if attempt < max_retries:
                    wait = backoff_factor**attempt
                    logger.warning(
                        "Request error (%s). Retrying in %s seconds.", exc, wait
                    )
                    time.sleep(wait)
                    continue
                raise

            if response.status_code == 200:
                return response.json()
            if response.status_code == 401:
                logger.warning("Token rejected, refreshing and retrying...")
                self.access_token = None
                self._ensure_valid_token()
                headers = self.get_headers()
                continue
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "Rate limit hit from Reddit. Waiting %s seconds.", retry_after
                )
                time.sleep(retry_after)
                continue

            error_msg = (
                f"API request failed with status {response.status_code}: "
                f"{response.text}"
            )
            logger.error(error_msg)
            raise RequestException(error_msg)

        raise RequestException(
            f"Failed to complete request to {endpoint} after {max_retries + 1} attempts"
        )

    def __del__(self):
        if hasattr(self, "session"):
            self.session.close()

