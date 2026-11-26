import time
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger("opentrack.github")


class GitHubApiError(Exception):
    """Base exception for GitHub API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class GitHubUserNotFoundError(GitHubApiError):
    """Raised when a GitHub username is not found (404)."""
    pass


class GitHubRateLimitError(GitHubApiError):
    """Raised when GitHub API rate limit is exceeded."""
    def __init__(self, message: str, reset_time: Optional[int] = None):
        super().__init__(message, status_code=403)
        self.reset_time = reset_time


class GitHubClient:
    """Client for interacting with the GitHub REST API v3 with retries and rate limit handling."""

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.token = token if token is not None else settings.GITHUB_TOKEN
        self.base_url = (base_url or settings.GITHUB_API_BASE_URL).rstrip("/")
        self.max_retries = settings.GITHUB_MAX_RETRIES
        self.retry_backoff = settings.GITHUB_RETRY_BACKOFF

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "OpenTrack-Student-Tracker/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers = self._get_headers()
        backoff = self.retry_backoff

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.request(method, url, headers=headers, params=params)

                    # Check rate limits in headers
                    rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
                    rate_limit_reset = response.headers.get("x-ratelimit-reset")

                    if response.status_code == 404:
                        raise GitHubUserNotFoundError(f"Resource not found on GitHub: {path}", status_code=404)

                    if response.status_code in (403, 429):
                        # Detect rate limit or secondary rate limit
                        msg = response.text
                        reset_ts = int(rate_limit_reset) if rate_limit_reset and rate_limit_reset.isdigit() else None
                        
                        if rate_limit_remaining == "0" or "rate limit" in msg.lower():
                            logger.warning("GitHub rate limit reached: %s. Reset at: %s", msg, reset_ts)
                            raise GitHubRateLimitError(
                                f"GitHub rate limit exceeded. Reset timestamp: {reset_ts}",
                                reset_time=reset_ts
                            )
                        
                        # If secondary rate limit or abuse detection, wait and retry
                        if attempt < self.max_retries:
                            logger.warning("GitHub returned %d: retrying attempt %d after %.2fs", response.status_code, attempt, backoff)
                            time.sleep(backoff)
                            backoff *= 2
                            continue
                        raise GitHubApiError(f"GitHub API error {response.status_code}: {msg}", status_code=response.status_code)

                    if response.status_code >= 500:
                        if attempt < self.max_retries:
                            logger.warning("GitHub 5xx server error, retrying attempt %d after %.2fs", attempt, backoff)
                            time.sleep(backoff)
                            backoff *= 2
                            continue
                        raise GitHubApiError(f"GitHub server error {response.status_code}: {response.text}", status_code=response.status_code)

                    if not response.is_success:
                        raise GitHubApiError(f"GitHub API error {response.status_code}: {response.text}", status_code=response.status_code)

                    return response.json()

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries:
                    logger.warning("Network error on GitHub request: %s. Retrying attempt %d...", exc, attempt)
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise GitHubApiError(f"GitHub connection failed after {self.max_retries} attempts: {exc}")

        raise GitHubApiError("Maximum retry attempts reached.")

    def get_user(self, username: str) -> Dict[str, Any]:
        """Fetch user profile to validate GitHub username and obtain numeric ID."""
        return self._request("GET", f"/users/{username}")

    def search_pull_requests(
        self,
        query: str,
        page: int = 1,
        per_page: int = 100,
        sort: str = "created",
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Execute GitHub Search API query for pull requests.
        Endpoint: GET /search/issues
        """
        params = {
            "q": query,
            "page": page,
            "per_page": min(per_page, 100),
            "sort": sort,
            "order": order
        }
        return self._request("GET", "/search/issues", params=params)

    def get_pull_request_details(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """
        Fetch full details of an individual pull request.
        Endpoint: GET /repos/{owner}/{repo}/pulls/{pull_number}
        """
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")

    def build_query(
        self,
        author: str,
        scope_type: str = "global",
        scope_value: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        date_field: str = "created"
    ) -> str:
        """
        Construct qualified GitHub search query string.
        Examples:
          - is:pr author:alice
          - is:pr author:alice org:myorg
          - is:pr author:alice repo:myorg/myrepo
          - is:pr author:alice created:2024-01-01..2024-06-30
          - is:pr author:alice updated:>=2024-01-01
        """
        parts = ["is:pr", f"author:{author}"]

        if scope_type == "organization" and scope_value and scope_value != "*":
            parts.append(f"org:{scope_value}")
        elif scope_type == "repository" and scope_value and scope_value != "*":
            parts.append(f"repo:{scope_value}")

        field = date_field if date_field in ("created", "updated") else "created"
        if date_from and date_to:
            parts.append(f"{field}:{date_from}..{date_to}")
        elif date_from:
            parts.append(f"{field}:>={date_from}")
        elif date_to:
            parts.append(f"{field}:<={date_to}")

        return " ".join(parts)
