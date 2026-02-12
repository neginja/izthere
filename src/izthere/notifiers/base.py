from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar


class Notifier(ABC):
    _registry: ClassVar[dict[str, type["Notifier"]]] = {}

    def __init_subclass__(
        cls, *, notifier_type: str | None = None, **kwargs: Any
    ) -> None:
        super().__init_subclass__(**kwargs)
        if notifier_type:
            cls._registry[notifier_type] = cls
            cls.notifier_type: str = notifier_type

    @abstractmethod
    async def notify(
        self,
        what: str,
        where: str,
        answer: bool,
        ts: datetime,
        extra: str | None = None,
    ) -> None:
        """Send a human-readable notification."""
        ...

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "Notifier":
        """
        Factory that reads ``cfg["type"]`` and delegates to the concrete subclass.
        """
        notifier_type: str = cfg.get("type", "")
        if not notifier_type:
            raise ValueError("Notifier config missing required field 'type'")

        concrete_cls: type[Notifier] | None = cls._registry.get(notifier_type)
        if concrete_cls is None:
            raise ValueError(f"Unsupported notifier type: {notifier_type}")

        return concrete_cls.from_config(cfg)
