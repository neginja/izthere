import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import lxml.html
from typing_extensions import override

from izthere.logger import get_logger
from izthere.monitors.base import Monitor
from izthere.web_utils import fetch_html, fetch_html_no_js

logger = get_logger()


class XpathWordMonitor(Monitor, monitor_type="xpath_word"):
    def __init__(
        self,
        *,
        name: str,
        url: str,
        xpath: str,
        keywords: list[str],
        user_agent: str | None = None,
        timeout_seconds: int = 10,
        case_sensitive: bool = False,
        use_javascript: bool = False,
    ) -> None:
        self.question: str = name
        self.url: str = url
        self.xpath: str = xpath
        self.keywords: list[str] = keywords
        self.case_sensitive: bool = case_sensitive
        self.use_javascript: bool = use_javascript
        self.headers: dict[str, str] = {"User-Agent": user_agent} if user_agent else {}
        self.timeout: int = timeout_seconds
        self._last_checked: datetime | None = None

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "XpathWordMonitor":
        return cls(
            name=cfg["question"],
            url=cfg["url"],
            xpath=cfg["xpath"],
            keywords=cfg["keywords"],
            user_agent=cfg.get("user_agent"),
            timeout_seconds=cfg.get("timeout_seconds", 10),
            case_sensitive=cfg.get("case_sensitive", False),
        )

    @staticmethod
    def _extract_from_xpath(html: str, xpath: str) -> str:
        tree = lxml.html.fromstring(html)
        matches = tree.xpath(xpath)

        texts: list[str] = []
        for node in matches:
            if isinstance(node, lxml.html.HtmlElement):
                texts.append(node.text_content())
            elif isinstance(node, (str, bytes)):
                texts.append(str(node))

        combined = " ".join(texts)
        return re.sub(r"\s+", " ", combined).strip()

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

        if self.use_javascript:
            html = await fetch_html(
                url=self.url, timeout=self.timeout, headers=self.headers
            )
        else:
            html = await fetch_html_no_js(
                url=self.url, timeout=self.timeout, headers=self.headers
            )

        visible_text: str = self._extract_from_xpath(html, self.xpath)

        logger.debug(f"[{self.monitor_type}] visible text in xpath={visible_text}")

        if self.case_sensitive:
            haystack = visible_text
            needles = self.keywords
        else:
            haystack = visible_text.lower()
            needles = [kw.lower() for kw in self.keywords]

        answer = any(needle in haystack for needle in needles)

        logger.info(
            f"[{self.monitor_type}] monitor '{self.question}' executed, answer={answer}"
        )
        return answer, None


if __name__ == "__main__":
    w = XpathWordMonitor(
        name="test",
        url="https://duckduckgo.com",
        xpath='//*[@id="__next"]/div/main/div[1]/div[2]/div[1]/div/div[1]/fieldset/label[1]/span',
        keywords=["search"],
        use_javascript=False,
    )

    r, _ = asyncio.run(w.run())
    print(r)
