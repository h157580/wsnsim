from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class Event:
    """Represents a single event in the discrete-event simulation.

    Events are ordered primarily by time and secondarily by sequence_number
    to ensure stable execution order for simultaneous events.
    """
    time: float
    sequence_number: int
    callback: Callable[..., Any] = field(compare=False)
    args: tuple[Any, ...] = field(compare=False)
    cancelled: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        """Validate event initialization."""
        if self.time < 0:
            raise ValueError("Event time cannot be negative.")

    def __lt__(self, other: Any) -> bool:
        """Compare events primarily by time, secondarily by sequence_number."""
        if not isinstance(other, Event):
            return NotImplemented
        if self.time != other.time:
            return self.time < other.time
        return self.sequence_number < other.sequence_number


class EventScheduler:
    """Core engine for managing and executing simulation events."""

    def __init__(self) -> None:
        """Initialize the scheduler with an empty queue and zeroed clock."""
        self._event_queue: List[Event] = []
        self._current_time: float = 0.0
        self._next_sequence: int = 0

    @property
    def current_time(self) -> float:
        """Return the current simulation time in seconds."""
        return self._current_time

    def schedule(self, delay: float, callback: Callable[..., Any], *args: Any) -> Event:
        """Schedule a new event to occur after a given delay.

        Args:
            delay: Time from now (in seconds) when the event should trigger.
            callback: Function to execute.
            *args: Arguments to pass to the callback.

        Returns:
            The created Event object, which can be used for cancellation.

        Raises:
            ValueError: If delay is negative.
        """
        if delay < 0:
            raise ValueError("Cannot schedule events in the past (negative delay).")

        event_time = self._current_time + delay
        event = Event(
            time=event_time,
            sequence_number=self._next_sequence,
            callback=callback,
            args=args
        )
        self._next_sequence += 1
        heapq.heappush(self._event_queue, event)
        return event

    def cancel(self, event: Event) -> None:
        """Mark an event as cancelled so it won't execute when popped.

        Args:
            event: The event object returned by schedule().
        """
        event.cancelled = True

    def run(self, until: Optional[float] = None) -> None:
        """Execute events in the queue until a specified time or queue exhaustion.

        Args:
            until: Simulation time (seconds) to stop at. If None, runs until empty.
        """
        while self._event_queue:
            # Peek at the next event
            if until is not None and self._event_queue[0].time > until:
                break

            event = heapq.heappop(self._event_queue)
            
            if event.cancelled:
                continue

            # Advance clock and execute
            self._current_time = event.time
            event.callback(*event.args)

        # Ensure clock hits 'until' if specified and simulation finished early
        if until is not None:
            self._current_time = max(self._current_time, until)
