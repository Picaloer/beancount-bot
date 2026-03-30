"""
Simple in-memory synchronous event bus.
Handlers are called synchronously in registration order.
For async/distributed scenarios, replace with Celery signals or Redis Pub/Sub.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4


@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransactionImported(DomainEvent):
    import_id: str = ""
    user_id: str = ""
    transaction_ids: list[str] = field(default_factory=list)


@dataclass
class TransactionClassified(DomainEvent):
    transaction_id: str = ""
    category_l1: str = ""
    category_l2: str | None = None
    source: str = ""


@dataclass
class MonthlyReportRequested(DomainEvent):
    user_id: str = ""
    year_month: str = ""  # '2025-03'


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception as exc:
                # Log but don't crash on handler errors
                import logging
                logging.getLogger(__name__).error(
                    "Event handler %s failed for %s: %s",
                    handler.__name__,
                    type(event).__name__,
                    exc,
                )


event_bus = EventBus()
