# GitHub Actions Paper-Trader Setup

This is the no-VPS option. GitHub runs the paper bot on a schedule while your Mac sleeps.

## What it does

`.github/workflows/paper-trader.yml` runs on GitHub-hosted Ubuntu:

- every 15 minutes, best-effort
- once daily near 23:55 UTC with a daily report
- manually via **Actions → Paper Trader → Run workflow**

It runs:

```bash
python -m trader.cron_tick --config config/settings.kraken-paper.yaml --db data/github_actions_paper_journal.db --report-dir logs
```

## Notifications

GitHub repository secrets required:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The bot only sends Telegram messages for important events:

- filled paper order
- closed paper trade
- daily report
- script error from inside `trader.cron_tick`

## Important limitations

GitHub Actions is not a true always-on server:

- scheduled runs can be delayed
- public repos have the most generous free Actions behavior
- private repos may consume included minutes
- persistent state is restored/saved through Actions cache/artifacts, not a real disk
- this is acceptable for paper testing, not live-money execution

## Paper portfolio persistence

The SQLite journal now stores the simulated portfolio between GitHub runs:

- current paper equity
- daily realized PnL
- consecutive loss count
- open paper positions with stop loss / take profit

This means scheduled runs no longer forget open paper positions just because a new GitHub runner starts.

## Setup commands if GitHub CLI is authenticated

From `/Users/ifeanyi/ai-crypto-trader`:

```bash
git init
git add .
git commit -m "feat: add paper trading bot"
gh repo create ai-crypto-trader --private --source . --push

gh secret set TELEGRAM_BOT_TOKEN --body "<your_bot_token>"
gh secret set TELEGRAM_CHAT_ID --body "<your_chat_id>"

gh workflow run paper-trader.yml
```

## Setup without GitHub CLI

1. Create a private GitHub repo manually named `ai-crypto-trader`.
2. Push this folder to it.
3. In GitHub: repo → Settings → Secrets and variables → Actions → New repository secret.
4. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
5. Go to repo → Actions → Paper Trader → Run workflow.
