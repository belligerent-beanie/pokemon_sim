from collections import deque
from typing import Deque

from pokemon_sim.engine.event import Event
from pokemon_sim.engine.listener import ListenerRegistry


class EventQueue:
    """Event queue for turn-based resolution."""

    def __init__(self, listener_registry: ListenerRegistry):
        self.queue: Deque[Event] = deque()
        self.listener_registry = listener_registry
        self.max_iterations = 1000  # Safeguard against infinite loops

    def enqueue(self, event: Event) -> None:
        """Add an event to the queue."""
        self.queue.append(event)

    def enqueue_many(self, events: list[Event]) -> None:
        """Add multiple events to the queue."""
        self.queue.extend(events)

    def resolve_all(self) -> None:
        """
        Resolve all events in the queue.
        Listeners react to each event and may spawn new events.
        Continues until queue is empty.
        """
        iterations = 0
        while self.queue and iterations < self.max_iterations:
            iterations += 1

            # Sort queue by priority and speed
            events = sorted(list(self.queue), key=lambda e: (e.priority if hasattr(e, 'priority') else 0,
                                                               e.speed_source.speed.raw_value if e.speed_source else 0), reverse=True)
            self.queue.clear()

            # Resolve each event
            for event in events:
                listeners = self.listener_registry.get_listeners(type(event))

                # Invoke each listener
                for listener in listeners:
                    new_events = listener.resolve(event)
                    self.enqueue_many(new_events)

        if iterations >= self.max_iterations:
            raise RuntimeError("Event queue exceeded max iterations; possible infinite loop")

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.queue) == 0

    def clear(self) -> None:
        """Clear the queue."""
        self.queue.clear()
