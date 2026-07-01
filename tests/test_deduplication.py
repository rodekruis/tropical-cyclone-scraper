from __future__ import annotations

from pathlib import Path
import tempfile

from gdacs_events_scraper.deduplication import DeduplicationTracker


def test_deduplication_tracker_saves_and_loads():
    """Test that the tracker persists event IDs correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_file = Path(tmpdir) / "tracker.json"
        tracker = DeduplicationTracker(tracker_file)
        
        # Mark some events as exported
        tracker.mark_exported(["event-1", "event-2", "event-3"])
        
        # Verify they're tracked
        assert tracker.is_already_exported("event-1")
        assert tracker.is_already_exported("event-2")
        assert tracker.is_already_exported("event-3")
        assert not tracker.is_already_exported("event-4")
        
        # Create a new tracker instance and verify it loads from disk
        tracker2 = DeduplicationTracker(tracker_file)
        assert tracker2.is_already_exported("event-1")
        assert tracker2.is_already_exported("event-2")
        assert tracker2.is_already_exported("event-3")
        assert not tracker2.is_already_exported("event-4")


def test_deduplication_tracker_returns_exported_ids():
    """Test that get_exported_ids returns all tracked IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_file = Path(tmpdir) / "tracker.json"
        tracker = DeduplicationTracker(tracker_file)
        
        tracker.mark_exported(["event-1", "event-2"])
        exported_ids = tracker.get_exported_ids()
        
        assert exported_ids == {"event-1", "event-2"}


def test_deduplication_tracker_clear():
    """Test that clear removes all tracked IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_file = Path(tmpdir) / "tracker.json"
        tracker = DeduplicationTracker(tracker_file)
        
        tracker.mark_exported(["event-1", "event-2"])
        assert tracker.is_already_exported("event-1")
        
        tracker.clear()
        assert not tracker.is_already_exported("event-1")
        assert len(tracker.get_exported_ids()) == 0
        assert not tracker_file.exists()


def test_deduplication_tracker_handles_missing_file():
    """Test that tracker handles missing file gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_file = Path(tmpdir) / "nonexistent" / "tracker.json"
        tracker = DeduplicationTracker(tracker_file)
        
        # Should start with empty set
        assert len(tracker.get_exported_ids()) == 0
        
        # Should be able to add events
        tracker.mark_exported(["event-1"])
        assert tracker.is_already_exported("event-1")


def test_deduplication_tracker_idempotent():
    """Test that marking the same event multiple times works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_file = Path(tmpdir) / "tracker.json"
        tracker = DeduplicationTracker(tracker_file)
        
        tracker.mark_exported(["event-1"])
        tracker.mark_exported(["event-1"])
        tracker.mark_exported(["event-1", "event-2"])
        
        exported_ids = tracker.get_exported_ids()
        assert exported_ids == {"event-1", "event-2"}
