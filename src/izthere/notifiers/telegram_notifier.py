import html
from datetime import datetime, timezone
from typing import Any, override
from urllib.parse import urlparse

from telegram import Bot
from telegram.helpers import escape_markdown

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

        parsed_where = urlparse(where)
        clean_display_url = (
            f"{parsed_where.scheme}://{parsed_where.netloc}{parsed_where.path}"
        )
        escaped_domain = escape_markdown(clean_display_url, version=2)

        text = (
            f"*What:* {escape_markdown(what, version=2)}\n"
            f"*Where:* [{escaped_domain}]({escape_markdown(where, version=2)})\n"
            f"*Answer:* {status}\n"
            f"*Checked at:* `{local_ts.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}`"
        )

        if extra:
            text = "\n\n".join([text, f"*Extra:* {escape_markdown(extra, version=2)}"])

        try:
            _ = await self.bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode="MarkdownV2"
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
