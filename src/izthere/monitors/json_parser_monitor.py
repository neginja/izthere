from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from typing_extensions import override

from izthere.logger import get_logger
from izthere.monitors.base import Monitor
from izthere.monitors.web_utils import fetch_json

logger = get_logger()


@dataclass
class SubParser:
    items_path: str
    predicates: list["Predicate"] = field(default_factory=list)

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "SubParser":
        return cls(
            items_path=data["items_path"],
            predicates=[Predicate.from_config(p) for p in data.get("predicates", [])],
        )


@dataclass
class Predicate:
    op: str
    path: str | None = None
    value: str | int | list[str] | None = None
    # If op is 'sub_parser', this contains the nested configuration
    parser: SubParser | None = None

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "Predicate":
        parser_data: dict[str, Any] | None = data.get("parser")
        return cls(
            op=data.get("op", ""),
            path=data.get("path"),
            value=data.get("value"),
            parser=SubParser.from_config(parser_data) if parser_data else None,
        )


class JSONParserMonitor(Monitor, monitor_type="json_api"):
    """
    A generic JSON API monitor that evaluates a list of predicates,
    including nested sub-parsers for array-based filtering.
    """

    # map of predicates operator evaluation logic
    OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
        "equal_insensitive": lambda val, target: (
            str(val).lower() == str(target).lower()
        ),
        "contains_insensitive": lambda val, target: (
            str(target).lower() in str(val).lower()
        ),
        "contains_any_insensitive": lambda val, targets: any(
            str(t).lower() in str(val).lower() for t in targets
        ),
    }

    def __init__(
        self,
        name: str,
        url: str,
        items_path: str,
        predicates: list[Predicate],
        extras_path: str | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self.question: str = name
        self.url: str = url
        self.items_path: str = items_path
        self.extras_path: str | None = extras_path
        self.predicates: list[Predicate] = predicates
        self.timeout_seconds: int = timeout_seconds
        self._last_checked: datetime | None = None

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "JSONParserMonitor":
        return cls(
            name=cfg["question"],
            url=cfg["url"],
            items_path=cfg["items_path"],
            predicates=[Predicate.from_config(p) for p in cfg["predicates"]],
            timeout_seconds=cfg.get("timeout_seconds", 15),
        )

    def _evaluate_predicate(self, item: Any, pred: Predicate) -> bool:
        if pred.op == "sub_parser" and pred.parser:
            sub_items: list[Any] | None = item.get(pred.parser.items_path, [])
            if not isinstance(sub_items, list):
                return False
            return any(
                all(self._evaluate_predicate(si, sp) for sp in pred.parser.predicates)
                for si in sub_items
            )

        actual_value = item.get(pred.path) if pred.path else item
        op_func = self.OPERATORS.get(pred.op)

        if not op_func:
            # fallback for typos like 'contains_insensiteve' in your YAML
            return False

        return op_func(actual_value, pred.value)

    @override
    async def run(self) -> tuple[bool, str | None]:
        self._last_checked = datetime.now(timezone.utc)

        try:
            data = await fetch_json(url=self.url, timeout=self.timeout_seconds)
            items = data.get(self.items_path, [])
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {self.url}: {e}")
            return False, f"unexpected error fix me! {e}"

        matches: list[str] = []
        for item in items:
            if all(self._evaluate_predicate(item, p) for p in self.predicates):
                # extract the extras if any
                if self.extras_path:
                    m = item.get(self.extras_path)
                    if m:
                        matches.append(str(m))

        found = len(matches) > 0
        return found, "\n".join(matches) if found else None

    @property
    @override
    def last_checked(self) -> datetime | None:
        return self._last_checked

    @property
    @override
    def what(self) -> str:
        return self.question

    @property
    @override
    def where(self) -> str:
        return self.url


if __name__ == "__main__":
    import asyncio

    monitor = JSONParserMonitor(
        name="test",
        url="https://api.ashbyhq.com/posting-api/job-board/duck-duck-go",
        items_path="jobs",
        predicates=[
            Predicate("equal_insensitive", path="employmentType", value="fulltime"),
            Predicate("equal_insensitive", path="location", value="remote"),
            Predicate(
                "sub_parser",  # can work from usa
                parser=SubParser(
                    items_path="secondaryLocations",
                    predicates=[
                        Predicate(
                            op="contains_insensitive", path="location", value="usa"
                        )
                    ],
                ),
            ),
            Predicate(
                op="contains_any_insensitive",
                path="title",
                value=["engineer", "backend", "platform"],
            ),
        ],
        extras_path="jobUrl",
    )

    result = asyncio.run(monitor.run())
    print(f"result: {result}")
