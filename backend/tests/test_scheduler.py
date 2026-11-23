import pytest
from app.services.scheduler import get_auto_sync_status, start_scheduler, stop_scheduler


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """Verify background scheduler lifecycle and status reporting."""
    status = get_auto_sync_status()
    assert status["enabled"] is True
    assert status["interval_minutes"] == 30

    # Start scheduler
    start_scheduler()
    active_status = get_auto_sync_status()
    assert active_status["is_running"] is True

    # Stop scheduler
    stop_scheduler()
    import asyncio
    await asyncio.sleep(0)
    stopped_status = get_auto_sync_status()
    assert stopped_status["is_running"] is False


def test_sync_status_endpoint_returns_auto_sync_metadata(client):
    """Verify /api/sync-status exposes the auto-sync configuration to frontend."""
    res = client.get("/api/sync-status")
    assert res.status_code == 200
    data = res.json()
    assert "auto_sync" in data
    assert data["auto_sync"]["interval_minutes"] == 30
    assert data["auto_sync"]["enabled"] is True
