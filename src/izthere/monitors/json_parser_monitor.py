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
        "any_item_contains_insensitive": lambda val, target: any(
            str(target).lower() in str(item).lower() for item in val
        ),
        "any_item_contains_any_insensitive": lambda val, targets: any(
            str(t).lower() in str(item).lower() for t in targets for item in val
        ),
    }

    def __init__(
        self,
        name: str,
        url: str,
        items_path: str | None,
        predicates: list[Predicate],
        extras_path: str | None = None,
        timeout_seconds: int = 15,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.question: str = name
        self.url: str = url
        self.items_path: str | None = items_path
        self.extras_path: str | None = extras_path
        self.predicates: list[Predicate] = predicates
        self.timeout_seconds: int = timeout_seconds
        self.headers: dict[str, str] | None = headers
        self._last_checked: datetime | None = None

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "JSONParserMonitor":
        return cls(
            name=cfg["question"],
            url=cfg["url"],
            items_path=cfg["items_path"],
            predicates=[Predicate.from_config(p) for p in cfg["predicates"]],
            extras_path=cfg.get("extras_path"),
            headers=cfg.get("headers"),
            timeout_seconds=cfg.get("timeout_seconds", 15),
        )

    def _evaluate_predicate(self, item: Any, pred: Predicate) -> bool:
        if pred.op == "sub_parser" and pred.parser:
            sub_items: Any | None = item.get(pred.parser.items_path)
            if not sub_items:
                return False

            if isinstance(sub_items, list):
                return any(
                    all(
                        self._evaluate_predicate(si, sp)
                        for sp in pred.parser.predicates
                    )
                    for si in sub_items
                )
            elif isinstance(sub_items, dict):
                return all(
                    self._evaluate_predicate(sub_items, sp)
                    for sp in pred.parser.predicates
                )
            else:
                return False

        actual_value = item.get(pred.path) if pred.path else item
        op_func = self.OPERATORS.get(pred.op)

        if not op_func:
            raise ValueError(f"operator not valid {pred.op}")

        res = op_func(actual_value, pred.value)
        logger.debug(
            f"evaluation of predicate {pred.op} using actual={actual_value}, predicate_value={pred.value}, result={res}"
        )
        return res

    @override
    async def run(self) -> tuple[bool, str | None]:
        self._last_checked = datetime.now(timezone.utc)

        try:
            data: dict[str, Any] | list[dict[str, Any]] = await fetch_json(
                url=self.url, timeout=self.timeout_seconds, headers=self.headers
            )
            if isinstance(data, dict):
                items = data.get(self.items_path) if self.items_path else data
            else:
                items = data

        except Exception as e:
            logger.error(f"Failed to fetch JSON from {self.url}: {e}")
            return False, f"unexpected error fix me! {e}"

        matches: list[str] = []
        found = False

        if not items:
            return False, "no data retrieved, fix me!"

        if isinstance(items, list):
            for item in items:
                if all(self._evaluate_predicate(item, p) for p in self.predicates):
                    found = True
                    # extract the extras if any
                    if self.extras_path:
                        extras_sub_paths = self.extras_path.strip(".").split(".")
                        extra_data = item
                        for sp in extras_sub_paths:
                            if not isinstance(extra_data, dict):
                                break
                            extra_data = extra_data.get(sp) if extra_data else None
                        if extra_data:
                            matches.append(str(extra_data))
        elif isinstance(items, dict):
            if all(self._evaluate_predicate(items, p) for p in self.predicates):
                found = True
                if self.extras_path:
                    extras_sub_paths = self.extras_path.split(".")
                    extra_data = items
                    for sp in extras_sub_paths:
                        if not isinstance(extra_data, dict):
                            break
                        extra_data = extra_data.get(sp) if extra_data else None
                    if extra_data:
                        matches.append(str(extra_data))

        return found, "\n".join(matches) if matches else None

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
                            op="contains_insensitive", path="location", value="japan"
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
