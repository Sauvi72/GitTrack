import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("opentrack.processor")


class PRStatus:
    MERGED = "MERGED"
    OPEN = "OPEN"
    CLOSED_UNMERGED = "CLOSED_UNMERGED"


def parse_github_datetime(date_str: Optional[str]) -> Optional[datetime.datetime]:
    """Parse GitHub ISO 8601 datetime strings to UTC datetime."""
    if not date_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Ensure UTC timezone awareness converted or normalized
        if dt.tzinfo is not None:
            return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception as e:
        logger.warning("Failed to parse GitHub datetime '%s': %s", date_str, e)
        return None


def classify_pr_status(state: str, merged_at: Optional[str]) -> str:
    """
    Classify pull request status according to project rules:
    - IF merged_at IS NOT NULL: status = MERGED
    - ELSE IF state == "open": status = OPEN
    - ELSE: status = CLOSED_UNMERGED
    """
    if merged_at is not None:
        return PRStatus.MERGED
    elif (state or "").lower() == "open":
        return PRStatus.OPEN
    else:
        return PRStatus.CLOSED_UNMERGED


def process_pull_request_payload(
    pr_payload: Dict[str, Any],
    student_id: int,
    author_username: str
) -> Dict[str, Any]:
    """
    Extract and normalize detailed GitHub pull request data for database persistence.
    """
    # Repo information
    base_info = pr_payload.get("base", {})
    repo_info = base_info.get("repo") or {}
    owner_info = repo_info.get("owner") or {}

    repo_full_name = repo_info.get("full_name")
    if not repo_full_name:
        # Fallback parse from html_url e.g. https://github.com/owner/repo/pull/12
        parts = pr_payload.get("html_url", "").split("/")
        if len(parts) >= 5:
            repo_full_name = f"{parts[3]}/{parts[4]}"
        else:
            repo_full_name = "unknown/unknown"

    repo_parts = repo_full_name.split("/")
    repo_owner = repo_parts[0] if len(repo_parts) > 1 else owner_info.get("login", "unknown")
    repo_name = repo_parts[1] if len(repo_parts) > 1 else repo_info.get("name", "unknown")

    # Determine organization name if owner is an organization or external
    org_name = None
    if owner_info.get("type") == "Organization":
        org_name = repo_owner
    elif repo_owner and repo_owner.lower() != (author_username or "").lower():
        org_name = repo_owner

    # Author
    user_info = pr_payload.get("user") or {}
    actual_author = user_info.get("login", author_username)
    author_id = user_info.get("id")

    # Status classification
    state = pr_payload.get("state", "open")
    merged_at_raw = pr_payload.get("merged_at")
    if merged_at_raw is None and isinstance(pr_payload.get("pull_request"), dict):
        merged_at_raw = pr_payload["pull_request"].get("merged_at")
    status = classify_pr_status(state, merged_at_raw)

    # Merged by
    merged_by_info = pr_payload.get("merged_by")
    merged_by = merged_by_info.get("login") if isinstance(merged_by_info, dict) else None

    # Branches
    base_branch = base_info.get("ref")
    head_info = pr_payload.get("head") or {}
    head_branch = head_info.get("ref")

    return {
        "github_id": pr_payload["id"],
        "github_node_id": pr_payload["node_id"],
        "student_id": student_id,
        "repository_full_name": repo_full_name,
        "repository_owner": repo_owner,
        "repository_name": repo_name,
        "organization_name": org_name,
        "pr_number": pr_payload.get("number"),
        "title": (pr_payload.get("title") or "").strip()[:500],
        "html_url": pr_payload.get("html_url", "")[:500],
        "state": state.lower(),
        "status": status,
        "is_draft": bool(pr_payload.get("draft", False)),
        "author_username": actual_author,
        "author_github_id": author_id,
        "created_at_github": parse_github_datetime(pr_payload.get("created_at")),
        "updated_at_github": parse_github_datetime(pr_payload.get("updated_at")),
        "closed_at": parse_github_datetime(pr_payload.get("closed_at")),
        "merged_at": parse_github_datetime(merged_at_raw),
        "merged_by": merged_by,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "commits": int(pr_payload.get("commits", 0)),
        "additions": int(pr_payload.get("additions", 0)),
        "deletions": int(pr_payload.get("deletions", 0)),
        "changed_files": int(pr_payload.get("changed_files", 0)),
        "comments": int(pr_payload.get("comments", 0)),
        "review_comments": int(pr_payload.get("review_comments", 0)),
        "last_checked_at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    }
