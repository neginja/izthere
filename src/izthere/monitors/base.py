from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar


class Monitor(ABC):
    _registry: ClassVar[dict[str, type["Monitor"]]] = {}

    def __init_subclass__(
        cls, *, monitor_type: str | None = None, **kwargs: Any
    ) -> None:
        """
        Automatically registers every subclass that supplies a `monitor_type`
        Example:
            class HtmlWordMonitor(Monitor, monitor_type"): …
        """
        super().__init_subclass__(**kwargs)
        if monitor_type:
            cls._registry[monitor_type] = cls
            cls.monitor_type: str = monitor_type

    @abstractmethod
    async def run(self) -> tuple[bool, str | None]:
        """Fetch the target, evaluate the condition and return True/False."""
        ...

    @property
    @abstractmethod
    def last_checked(self) -> datetime | None: ...

    @property
    @abstractmethod
    def what(self) -> str: ...

    @property
    @abstractmethod
    def where(self) -> str: ...

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "Monitor":
        """
        Factory that looks at ``cfg["type"]`` and forwards the dict to the correct
        concrete subclass.
        """
        monitor_type: str = cfg.get("type", "")
        if not monitor_type:
            raise ValueError("Monitor config missing required field 'type'")

        concrete_cls: type[Monitor] | None = cls._registry.get(monitor_type)
        if concrete_cls is None:
            raise ValueError(f"Unsupported monitor type: {monitor_type}")

        return concrete_cls.from_config(cfg)
