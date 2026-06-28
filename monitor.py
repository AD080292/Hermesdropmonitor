name: Hermes Stock Monitor

on:
  schedule:
    - cron: "0 9 * * *"         # 1pm Dubai, daily
    - cron: "0 10 * * *"        # 2pm Dubai, daily
    - cron: "*/15 12-18 * * *"  # every 15 min, 4pm-10pm Dubai, daily
    - cron: "*/5 13-18 * * 1-5" # every 5 min, 5pm-10:30pm Dubai, weekdays only
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Playwright
        run: |
          pip install playwright
          playwright install chromium
          playwright install-deps chromium

      - name: Run monitor
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python monitor.py
