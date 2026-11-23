import logging
from typing import List, Dict, Any, Tuple
from app.services.github_client import GitHubClient

logger = logging.getLogger("opentrack.discovery")


class PRDiscoveryEngine:
    """
    Engine to discover Pull Requests authored by a student across GitHub
    using the Search API, handling pagination, organization scopes, repository
    scopes, and date partitioning for high volume results.
    """

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    def parse_repo_and_number_from_item(self, item: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        Extract (owner, repo, pr_number) from search result item.
        """
        number = item["number"]
        # Repository URL format: https://api.github.com/repos/owner/repo
        repo_url = item.get("repository_url", "")
        if repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[-2], parts[-1]
                return owner, repo, number

        # Fallback from html_url: https://github.com/owner/repo/pull/number
        html_url = item.get("html_url", "")
        parts = html_url.split("/")
        if len(parts) >= 7:
            return parts[3], parts[4], number

        return "unknown", "unknown", number

    def search_scope(
        self,
        username: str,
        scope_type: str = "global",
        scope_value: str = "*",
        date_from: str = None,
        date_to: str = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute search for a given scope, paginating until finished or capped.
        Returns: (items_list, is_complete)
        """
        items: List[Dict[str, Any]] = []
        is_complete = True
        page = 1
        per_page = 100

        query = self.client.build_query(
            author=username,
            scope_type=scope_type,
            scope_value=scope_value,
            date_from=date_from,
            date_to=date_to
        )

        logger.info("Executing GitHub search query: '%s'", query)

        while True:
            result = self.client.search_pull_requests(query=query, page=page, per_page=per_page)
            total_count = result.get("total_count", 0)
            if result.get("incomplete_results", False):
                is_complete = False

            batch = result.get("items", [])
            # Filter only PRs (items that have a pull_request object)
            pr_batch = [item for item in batch if item.get("pull_request") is not None]
            items.extend(pr_batch)

            # Check if all items fetched or reached GitHub 1000 result maximum
            if len(batch) < per_page or (page * per_page) >= total_count or page >= 10:
                if total_count > 1000 and (date_from is None and date_to is None):
                    # Flag that 1000 ceiling was hit and partitioning is recommended
                    is_complete = False
                break

            page += 1

        return items, is_complete

    def discover_all_for_student(
        self,
        username: str,
        active_scopes: List[Dict[str, Any]]
    ) -> Tuple[List[Tuple[str, str, int, Dict[str, Any]]], bool]:
        """
        Run discovery across all active scopes (Global, Organization, Repository).
        Deduplicates candidate PR pointers before fetching full details.
        
        Returns:
            discovered_prs: List of (owner, repo, pr_number, search_item)
            is_complete: bool (False if any search was incomplete or hit 1000 result ceiling)
        """
        discovered_map: Dict[str, Tuple[str, str, int, Dict[str, Any]]] = {}
        all_complete = True

        for scope in active_scopes:
            scope_type = scope.get("scope_type", "global")
            scope_val = scope.get("scope_value", "*")

            scope_items, complete = self.search_scope(
                username=username,
                scope_type=scope_type,
                scope_value=scope_val
            )

            if not complete:
                all_complete = False

            for item in scope_items:
                owner, repo, pr_number = self.parse_repo_and_number_from_item(item)
                # Deduplication key across scopes: repo_full_name#pr_number
                dedup_key = f"{owner.lower()}/{repo.lower()}#{pr_number}"
                if dedup_key not in discovered_map:
                    discovered_map[dedup_key] = (owner, repo, pr_number, item)

        return list(discovered_map.values()), all_complete
