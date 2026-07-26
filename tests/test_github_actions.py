from pathlib import Path


WORKFLOW = Path(".github/workflows/paper-trader.yml")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
PYPROJECT = Path("pyproject.toml")


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


def test_ci_workflow_runs_quality_gates_on_push_and_pull_request():
    text = CI_WORKFLOW.read_text()

    assert "push:" in text
    assert "pull_request:" in text
    assert "python -m pytest -q" in text
    assert "python -m ruff check src tests" in text
    assert "python-version: \"3.11\"" in text


def test_dev_dependencies_pin_ruff_for_reproducible_ci():
    assert '"ruff==0.15.20"' in PYPROJECT.read_text()


def test_paper_trader_workflow_can_send_weekly_report():
    text = WORKFLOW.read_text()

    assert "report_weekly:" in text
    assert "--report-weekly" in text
    assert "45 23 * * 0" in text
