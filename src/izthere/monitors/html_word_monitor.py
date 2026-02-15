import re
from datetime import datetime, timezone
from typing import Any, override

from bs4 import BeautifulSoup  # <-- new dependency

from izthere.logger import get_logger
from izthere.monitors.web_utils import fetch_html

from .base import Monitor

logger = get_logger()


class HtmlWordMonitor(Monitor, monitor_type="html_word"):
    """
    Detects the presence of one or more keywords in the *visible* text of an HTML page.
    """

    def __init__(
        self,
        *,
        name: str,
        url: str,
        keywords: list[str],
        user_agent: str | None = None,
        timeout_seconds: int = 10,
        case_sensitive: bool = False,
    ) -> None:
        self.question: str = name
        self.url: str = url
        self.keywords: list[str] = keywords
        self.case_sensitive: bool = case_sensitive
        self.headers: dict[str, str] = {"User-Agent": user_agent} if user_agent else {}
        self.timeout: int = timeout_seconds
        self._last_checked: datetime | None = None

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "HtmlWordMonitor":
        return cls(
            name=cfg["question"],
            url=cfg["url"],
            keywords=cfg["keywords"],
            user_agent=cfg.get("user_agent", None),
            timeout_seconds=cfg.get("timeout_seconds", 10),
            case_sensitive=cfg.get("case_sensitive", False),
        )

    @staticmethod
    def _extract_visible_text(html: str) -> str:
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")

        # initial trim of uninteresting invisible content
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # retrieve text we are interested in
        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text)

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

    @override
    async def run(self) -> tuple[bool, str | None]:
        logger.debug(f"[{self.monitor_type}] executing monitor '{self.question}'")
        self._last_checked = datetime.now(timezone.utc)

        html = await fetch_html(
            url=self.url, timeout=self.timeout, headers=self.headers
        )

        visible_text: str = self._extract_visible_text(html)

        if self.case_sensitive:
            haystack = visible_text
            needles = self.keywords
        else:
            haystack = visible_text.lower()
            needles = [kw.lower() for kw in self.keywords]

        answer: bool = any(needle in haystack for needle in needles)
        logger.info(
            f"[{self.monitor_type}] monitor '{self.question}' executed, answer={answer}"
        )
        return answer, None
