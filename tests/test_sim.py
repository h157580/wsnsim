import pytest
from wsnsim.sim import EventScheduler


def test_events_run_in_time_order():
    """Verify that events are executed according to their scheduled simulation time."""
    scheduler = EventScheduler()
    execution_log = []

    def record_event(label: str):
        execution_log.append((scheduler.current_time, label))

    # Schedule events in non-chronological order of scheduling
    scheduler.schedule(2.0, record_event, "Late")
    scheduler.schedule(1.0, record_event, "Early")
    scheduler.run()

    assert execution_log == [(1.0, "Early"), (2.0, "Late")]


def test_same_time_stable_order():
    """Verify that events scheduled for the same time are executed in the order they were scheduled."""
    scheduler = EventScheduler()
    execution_log = []

    def record_event(label: str):
        execution_log.append(label)

    # Schedule multiple events for time 0.0
    scheduler.schedule(0.0, record_event, "First")
    scheduler.schedule(0.0, record_event, "Second")
    scheduler.run()

    assert execution_log == ["First", "Second"]


def test_schedule_in_past_raises():
    """Verify that scheduling an event with a negative delay raises a ValueError."""
    scheduler = EventScheduler()
    with pytest.raises(ValueError, match="Cannot schedule events in the past"):
        scheduler.schedule(-0.1, lambda: None)


def test_cancel_prevents_execution():
    """Verify that cancelled events are correctly skipped by the scheduler."""
    scheduler = EventScheduler()
    execution_log = []

    def record_event(label: str):
        execution_log.append(label)

    event_to_cancel = scheduler.schedule(1.0, record_event, "Cancelled")
    scheduler.schedule(2.0, record_event, "Not Cancelled")

    scheduler.cancel(event_to_cancel)
    scheduler.run()

    assert execution_log == ["Not Cancelled"]
    assert scheduler.current_time == 2.0


def test_run_until():
    """Verify that the 'until' parameter correctly stops the simulation execution."""
    scheduler = EventScheduler()
    execution_log = []

    def record_event(label: str):
        execution_log.append(label)

    scheduler.schedule(1.0, record_event, "Executes")
    scheduler.schedule(3.0, record_event, "Skips")
    scheduler.run(until=2.0)

    assert execution_log == ["Executes"]
    assert scheduler.current_time == 2.0
