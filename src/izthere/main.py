import asyncio
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from izthere.logger import get_logger
from izthere.monitors.base import Monitor
from izthere.notifiers.base import Notifier

CONFIG_DIR = Path(__file__).parent / "config"

logger = get_logger()


def load_config(file_path: Path) -> Any:
    """Simple safe loader – returns a list of dicts (empty list if file missing)."""
    if not file_path.is_file():
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


async def setup() -> None:
    config_path = Path(os.environ.get("IS_CONFIG_PATH", "./config.yaml"))
    if not config_path.exists():
        raise FileNotFoundError(
            "Configuration file not found, set IS_CONFIG_PATH to a valid path"
        )
    configs: dict[str, Any] = load_config(config_path)

    notifier_cfgs = configs.get("notifiers", [])
    notifiers: dict[str, Notifier] = {
        cfg["name"]: Notifier.from_config(cfg) for cfg in notifier_cfgs
    }

    monitor_cfgs = configs.get("monitors", [])
    monitors: list[tuple[str, list[str], str, Monitor]] = [
        (cfg["question"], cfg["notifiers"], cfg["schedule"], Monitor.from_config(cfg))
        for cfg in monitor_cfgs
    ]

    scheduler = AsyncIOScheduler()
    for question, notifier_names, schedule, monitor in monitors:
        logger.debug(f"setting up monitor '{question}' with notifiers {notifier_names}")
        associated_notifiers: list[Notifier] = []
        for notifier_name in notifier_names:
            notifier: Notifier | None = notifiers.get(notifier_name)
            if notifier is None:
                raise RuntimeError(
                    f"Notifier '{notifier_name}' referenced but not defined"
                )
            associated_notifiers.append(notifier)

        async def job(
            m: Monitor = monitor,
            ns: list[Notifier] = associated_notifiers,
        ) -> None:  # default args capture current loop values
            answer, extra = await m.run()
            ts: datetime = datetime.now(timezone.utc)
            for n in ns:
                await n.notify(
                    what=m.what, where=m.where, answer=answer, ts=ts, extra=extra
                )

        trigger: CronTrigger = CronTrigger.from_crontab(schedule)
        logger.info(
            f"loaded one monitor '{question}' with {len(associated_notifiers)} notifiers"
        )
        name = re.sub(r"[^a-z0-9_]+", "", re.sub(r"[ \t]+", "_", question.lower()))
        scheduler.add_job(job, trigger, name=name, max_instances=1)
        logger.info(f"monitor '{question}' scheduled")

    scheduler.start()
    logger.info("🚀 notification engine started - press Ctrl+C to stop.")
    try:
        _ = await asyncio.Event().wait()  # keep the loop alive forever
    finally:
        scheduler.shutdown()


def main() -> None:
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        logger.info("stopped")
