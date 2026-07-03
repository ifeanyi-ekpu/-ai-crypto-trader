from trader.notifications import TelegramNotifier, telegram_notifier_from_env


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"ok":true}'


class FakeUrlopen:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout=10):
        self.requests.append((request, timeout))
        return FakeResponse()


def test_telegram_notifier_sends_message_without_exposing_token():
    fake = FakeUrlopen()
    notifier = TelegramNotifier(token="123:secret", chat_id="456", urlopen=fake)

    notifier.send("Paper trade opened")

    request, timeout = fake.requests[0]
    assert timeout == 10
    assert request.full_url.endswith("/bot123:secret/sendMessage")
    body = request.data.decode()
    assert "Paper+trade+opened" in body
    assert "chat_id=456" in body


def test_telegram_notifier_from_env_returns_none_when_missing_credentials():
    assert telegram_notifier_from_env({}) is None


def test_telegram_notifier_from_env_builds_notifier_when_credentials_exist():
    notifier = telegram_notifier_from_env({"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"})
    assert isinstance(notifier, TelegramNotifier)
