from __future__ import annotations

import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Mapping


Urlopen = Callable[[urllib.request.Request, int], object]


@dataclass
class TelegramNotifier:
    token: str
    chat_id: str
    urlopen: Callable = urllib.request.urlopen

    def send(self, text: str, timeout: int = 10) -> None:
        if not text.strip():
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = urllib.parse.urlencode(
            {
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        request = urllib.request.Request(url, data=payload, method="POST")
        with self.urlopen(request, timeout=timeout) as response:
            response.read()


def telegram_notifier_from_env(env: Mapping[str, str] | None = None) -> TelegramNotifier | None:
    values = env or os.environ
    token = values.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = values.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return None
    return TelegramNotifier(token=token, chat_id=chat_id)
