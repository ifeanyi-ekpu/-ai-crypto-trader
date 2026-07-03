from pathlib import Path


WORKFLOW = Path(".github/workflows/paper-trader.yml")


def test_paper_trader_workflow_exists_and_uses_github_secrets():
    text = WORKFLOW.read_text()

    assert "cron:" in text
    assert "workflow_dispatch:" in text
    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}" in text
    assert "TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}" in text
    assert "python -m trader.cron_tick" in text
    assert "config/settings.kraken-paper.yaml" in text


def test_paper_trader_workflow_caches_local_bot_state():
    text = WORKFLOW.read_text()

    assert "actions/cache" in text
    assert "path: |" in text
    assert "data" in text
    assert "logs" in text
