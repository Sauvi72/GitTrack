import datetime
import logging
import threading
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.pull_request import PullRequest
from app.models.tracking_scope import TrackingScope
from app.models.sync_log import SyncLog
from app.services.github_client import GitHubClient, GitHubApiError
from app.services.pr_discovery import PRDiscoveryEngine
from app.services.pr_processor import process_pull_request_payload

logger = logging.getLogger("opentrack.sync")

# In-memory synchronization lock set to prevent overlapping syncs for the same student
_active_sync_locks: set[int] = set()
_lock_mutex = threading.Lock()


class StudentAlreadySyncingError(Exception):
    """Raised when a sync is already running for the given student."""
    pass


class SyncService:
    """
    Orchestrates full and incremental pull request synchronization for students.
    Maintains a complete local contribution database with accurate timestamps.
    """

    def __init__(self, db: Session, github_client: Optional[GitHubClient] = None):
        self.db = db
        self.github_client = github_client or GitHubClient()
        self.discovery_engine = PRDiscoveryEngine(self.github_client)

    def _acquire_student_lock(self, student_id: int) -> bool:
        with _lock_mutex:
            if student_id in _active_sync_locks:
                return False
            _active_sync_locks.add(student_id)
            return True

    def _release_student_lock(self, student_id: int):
        with _lock_mutex:
            _active_sync_locks.discard(student_id)

    def sync_student(self, student_id: int, force_full: bool = False) -> Dict[str, Any]:
        """
        Synchronize pull requests for an individual student.
        - If first sync or force_full=True: runs initial full historical sync.
        - Otherwise: runs smart incremental sync (recent activity + refreshes previously open PRs).
        Idempotent and thread-safe.
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"Student with ID {student_id} not found.")

        if not self._acquire_student_lock(student_id):
            raise StudentAlreadySyncingError(
                f"Synchronization is already in progress for student {student.github_username}."
            )

        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        sync_log = SyncLog(
            student_id=student_id,
            started_at=now_utc,
            status="IN_PROGRESS",
            discovered_count=0,
            new_pr_count=0,
            updated_pr_count=0,
            is_complete=True
        )
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)

        is_full_sync = force_full or (student.last_synced_at is None)

        try:
            # Step 1: Gather active scopes
            active_scope_models = self.db.query(TrackingScope).filter(TrackingScope.is_active == True).all()
            if not active_scope_models:
                scopes_data = [{"scope_type": "global", "scope_value": "*"}]
            else:
                scopes_data = [
                    {"scope_type": s.scope_type, "scope_value": s.scope_value}
                    for s in active_scope_models
                ]

            discovered_prs: List[tuple] = []
            is_complete = True

            # Step 2: PR Discovery
            if is_full_sync:
                logger.info("Executing FULL historical sync for student %s", student.github_username)
                discovered_prs, is_complete = self.discovery_engine.discover_all_for_student(
                    username=student.github_username,
                    active_scopes=scopes_data
                )
            else:
                # Incremental sync: search recent PRs (since last_synced_at - 2 days buffer)
                overlap_buffer = datetime.timedelta(days=2)
                since_dt = student.last_synced_at - overlap_buffer if student.last_synced_at else None
                since_str = since_dt.strftime("%Y-%m-%d") if since_dt else None

                logger.info("Executing INCREMENTAL sync for student %s (since %s)", student.github_username, since_str)
                # Discover new or updated PRs in date window
                for scope in scopes_data:
                    scope_type = scope.get("scope_type", "global")
                    scope_val = scope.get("scope_value", "*")
                    items, complete = self.discovery_engine.search_scope(
                        username=student.github_username,
                        scope_type=scope_type,
                        scope_value=scope_val,
                        date_from=since_str,
                        date_field="updated"
                    )
                    if not complete:
                        is_complete = False
                    for item in items:
                        owner, repo, pr_num = self.discovery_engine.parse_repo_and_number_from_item(item)
                        discovered_prs.append((owner, repo, pr_num, item))

            sync_log.is_complete = is_complete

            # Deduplicate discovered pointers
            dedup_targets: Dict[str, tuple] = {}
            for owner, repo, pr_number, item in discovered_prs:
                key = f"{owner.lower()}/{repo.lower()}#{pr_number}"
                dedup_targets[key] = (owner, repo, pr_number, item)

            # Step 3 (For Incremental): Recheck all currently OPEN PRs from the DB
            # This ensures that if an open PR was merged or closed, we capture the status change!
            if not is_full_sync:
                open_db_prs = (
                    self.db.query(PullRequest)
                    .filter(
                        PullRequest.student_id == student.id,
                        PullRequest.status == "OPEN"
                    )
                    .all()
                )
                for open_pr in open_db_prs:
                    key = f"{open_pr.repository_owner.lower()}/{open_pr.repository_name.lower()}#{open_pr.pr_number}"
                    if key not in dedup_targets:
                        dedup_targets[key] = (open_pr.repository_owner, open_pr.repository_name, open_pr.pr_number, None)

            sync_log.discovered_count = len(dedup_targets)
            new_count = 0
            updated_count = 0

            # Step 4: Upsert into database (use search item directly when complete to avoid N+1 API calls)
            for key, (owner, repo, pr_number, search_item) in dedup_targets.items():
                has_full_search_data = (
                    isinstance(search_item, dict)
                    and "id" in search_item
                    and "node_id" in search_item
                    and "created_at" in search_item
                    and isinstance(search_item.get("pull_request"), dict)
                )
                if has_full_search_data:
                    pr_details = search_item
                else:
                    try:
                        pr_details = self.github_client.get_pull_request_details(owner, repo, pr_number)
                    except Exception as fetch_err:
                        logger.warning("Could not fetch details for %s/%s#%d: %s. Using search summary.", owner, repo, pr_number, fetch_err)
                        if search_item:
                            pr_details = search_item
                        else:
                            continue

                processed = process_pull_request_payload(
                    pr_payload=pr_details,
                    student_id=student.id,
                    author_username=student.github_username
                )

                # Look up existing PR by node_id or repo + pr_number
                existing_pr = (
                    self.db.query(PullRequest)
                    .filter(
                        (PullRequest.github_node_id == processed["github_node_id"]) |
                        (
                            (PullRequest.repository_full_name == processed["repository_full_name"]) &
                            (PullRequest.pr_number == processed["pr_number"])
                        )
                    )
                    .first()
                )

                if existing_pr:
                    # Update fields
                    for field_name, field_val in processed.items():
                        setattr(existing_pr, field_name, field_val)
                    updated_count += 1
                else:
                    new_pr = PullRequest(**processed)
                    self.db.add(new_pr)
                    new_count += 1

            # Step 5: Finalize sync log and update student last_synced_at
            finished_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            sync_log.finished_at = finished_utc
            sync_log.new_pr_count = new_count
            sync_log.updated_pr_count = updated_count
            sync_log.status = "SUCCESS" if sync_log.is_complete else "PARTIAL"

            student.last_synced_at = finished_utc

            self.db.commit()
            self.db.refresh(sync_log)

            return {
                "sync_log_id": sync_log.id,
                "student_id": student.id,
                "username": student.github_username,
                "sync_type": "FULL" if is_full_sync else "INCREMENTAL",
                "status": sync_log.status,
                "discovered": sync_log.discovered_count,
                "new_prs": new_count,
                "updated_prs": updated_count,
                "is_complete": sync_log.is_complete
            }

        except Exception as e:
            self.db.rollback()
            finished_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            sync_log.finished_at = finished_utc
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            self.db.commit()
            logger.error("Synchronization failed for student %s: %s", student.github_username, e, exc_info=True)
            raise

        finally:
            self._release_student_lock(student_id)

    def sync_all_active_students(self, force_full: bool = False) -> List[Dict[str, Any]]:
        """Synchronize all active students sequentially."""
        active_students = self.db.query(Student).filter(Student.is_active == True).all()
        results = []
        for s in active_students:
            try:
                res = self.sync_student(s.id, force_full=force_full)
                results.append(res)
            except Exception as e:
                results.append({
                    "student_id": s.id,
                    "username": s.github_username,
                    "status": "FAILED",
                    "error": str(e)
                })
        return results
