from abc import ABC, abstractmethod
from typing import Type

from pokemon_sim.engine.event import Event


class Listener(ABC):
    """Base class for event listeners (abilities, moves, items, field effects)."""

    @abstractmethod
    def listens_to(self, event_type: Type[Event]) -> bool:
        """Return True if this listener cares about this event type."""
        pass

    @abstractmethod
    def resolve(self, event: Event) -> list[Event]:
        """
        React to an event and return any new events to queue.
        Must not modify the original event.
        """
        pass


class ListenerRegistry:
    """Registers and retrieves listeners for event types."""

    def __init__(self):
        self.listeners: list[Listener] = []

    def register(self, listener: Listener) -> None:
        """Register a listener."""
        self.listeners.append(listener)

    def get_listeners(self, event_type: Type[Event]) -> list[Listener]:
        """Get all listeners that care about this event type."""
        return [l for l in self.listeners if l.listens_to(event_type)]

    def clear(self) -> None:
        """Clear all registered listeners."""
        self.listeners.clear()
