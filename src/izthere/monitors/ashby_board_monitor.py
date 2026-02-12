import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from typing_extensions import override

from izthere.logger import get_logger
from izthere.monitors.base import Monitor
from izthere.web_utils import fetch_json

logger = get_logger()


class AshbyBoardMonitor(Monitor, monitor_type="ashby_board"):
    def __init__(
        self,
        *,
        name: str,
        url: str,
        keywords: list[str],
        location_name: str | None = None,
        remote_only: bool = True,
        employment_type: str | None = "FullTime",  # "FullTime", "Contract", "PartTime"
        timeout_seconds: int = 10,
    ) -> None:
        self.question: str = name
        self.url: str = url
        self.keywords: list[str] = keywords
        self.location_name: str | None = location_name
        self.remote_only: bool = remote_only
        self.employment_type: str | None = employment_type
        self.timeout_seconds: int = timeout_seconds
        self._last_checked: datetime | None = None

        path = urlparse(url).path.strip("/")
        self.company_slug: str = path.split("?")[0]
        self.api_url: str = (
            f"https://api.ashbyhq.com/posting-api/job-board/{self.company_slug}"
        )

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "AshbyBoardMonitor":
        return cls(
            name=cfg["question"],
            url=cfg["url"],
            keywords=cfg["keywords"],
            location_name=cfg.get("location_name"),
            timeout_seconds=cfg.get("timeout", 10),
        )

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
        logger.debug(
            f"[{self.monitor_type}] checking Ashby board for '{self.company_slug}'"
        )
        self._last_checked = datetime.now(timezone.utc)

        try:
            data = await fetch_json(url=self.api_url, timeout=self.timeout_seconds)
            jobs = data.get("jobs", [])
        except Exception as e:
            logger.error(f"[{self.monitor_type}] Ashby API request failed: {e}")
            return False, None

        found_match = False
        extras: list[str] = []
        for job in jobs:
            title = job.get("title", "").lower()

            if (
                self.employment_type
                and job.get("employmentType", "").lower()
                != self.employment_type.lower()
            ):
                continue

            if self.remote_only and "remote" not in job.get("location", "").lower():
                continue

            job_locations = job.get("secondaryLocations", [])
            if not any(
                self.location_name in loc.get("location", "").lower()
                for loc in job_locations
            ):
                continue

            if any(keyword in title for keyword in self.keywords):
                job_url = job.get("jobUrl")
                logger.debug(
                    f"[{self.monitor_type}] match found: {job.get('title')} ({job_url})"
                )
                found_match = True
                if job_url:
                    extras.append(job_url)

        return found_match, "\n".join(extras)


if __name__ == "__main__":
    monitor = AshbyBoardMonitor(
        name="test",
        url="https://jobs.ashbyhq.com/duck-duck-go",
        location_name="usa",
        remote_only=True,
        keywords=["engineer"],
    )

    result = asyncio.run(monitor.run())
    print(f"Job found: {result}")
