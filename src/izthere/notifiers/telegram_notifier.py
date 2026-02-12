from datetime import datetime, timezone
from typing import Any, override

from telegram import Bot

from izthere.logger import get_logger
from izthere.notifiers.base import Notifier

logger = get_logger()


class TelegramNotifier(Notifier, notifier_type="telegram"):
    def __init__(self, *, bot_token: str, chat_id: str):
        self.bot: Bot = Bot(token=bot_token)
        self.chat_id: str = chat_id

    @classmethod
    @override
    def from_config(cls, cfg: dict[str, Any]) -> "TelegramNotifier":
        return cls(bot_token=cfg["bot_token"], chat_id=cfg["chat_id"])

    @override
    async def notify(
        self,
        what: str,
        where: str,
        answer: bool,
        ts: datetime,
        extra: str | None = None,
    ) -> None:
        status = "✅ Yes" if answer else "❌ No"

        local_ts = datetime.now(timezone.utc).astimezone()
        tz_name = local_ts.tzname()

        text = (
            f"*What:* {what}\n"
            f"*Where:* {where}\n"
            f"*Answer:* {status}\n"
            f"*Checked at:* `{local_ts.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}`"
        )

        if extra:
            text = "\n\n".join([text, f"*Extra:* {extra}"])

        try:
            _ = await self.bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode="Markdown"
            )
        except Exception:
            logger.exception(
                "Failed to send Telegram message to chat_id=%s for what=%s",
                self.chat_id,
                what,
            )
            raise
        else:
            logger.info(
                f"[{self.notifier_type}] notified what={what}, answer={answer} to chat_id={self.chat_id}"
            )
