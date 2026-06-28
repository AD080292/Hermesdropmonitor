import asyncio
import os
import urllib.request
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

URLS = [
    ("🇫🇷 France - Picotin",  "https://www.hermes.com/fr/fr/category/maroquinerie/sacs-et-pochettes/sacs-et-pochettes-femme/",   "Picotin"),
    ("🇬🇧 UK - Picotin",      "https://www.hermes.com/uk/en/category/leather-goods/bags-and-clutches/womens-bags-and-clutches/",   "Picotin"),
    ("🇫🇷 France - Kelly",    "https://www.hermes.com/fr/fr/category/maroquinerie/petite-maroquinerie/portefeuilles-to-go/",        "Kelly Classique To Go"),
    ("🇬🇧 UK - Kelly",        "https://www.hermes.com/uk/en/category/leather-goods/small-leather-goods/to-go-wallets/",             "Kelly Classique To Go"),
]

SKIP_TAGS = ["available soon", "coming soon", "bientôt disponible", "prossimamente"]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode()
    urllib.request.urlopen(url, data, timeout=10)
    print("Telegram alert sent!")


async def check_url(page, label, url, keyword):
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception:
        await page.goto(url, timeout=45000)

    await page.wait_for_timeout(2000)

    # Dismiss redirect / cookie popups
    for text_fragment in ["Stay", "Rester", "Resta", "Bleiben", "Blijf", "Permanecer",
                          "Close", "Fermer", "Chiudi", "Schließen", "Sluiten",
                          "sans accepter", "Tout refuser", "Reject all", "Ablehnen"]:
        try:
            btn = page.get_by_role("button", name=text_fragment, exact=False)
            if await btn.first.is_visible(timeout=1500):
                await btn.first.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass

    # Click Load More until exhausted
    for _ in range(15):
        try:
            btn = page.get_by_role("button").filter(
                has_text_regex="Load more|Voir plus|Vedere più|Ver más|Meer items|Mehr Artikel"
            )
            if await btn.first.is_visible(timeout=1500):
                await btn.first.scroll_into_view_if_needed()
                await btn.first.click()
                await page.wait_for_timeout(2500)
            else:
                break
        except Exception:
            break

    text = await page.inner_text("body")

    if keyword not in text:
        return None

    idx = text.index(keyword)
    snippet = text[max(0, idx - 300): idx + 500].lower()

    if any(tag in snippet for tag in SKIP_TAGS):
        return None  # "Available soon" — not a real drop

    if any(x in text.lower() for x in ["add to cart", "ajouter au panier", "aggiungi al carrello"]):
        return "🔴 ADD TO CART"
    elif any(x in text.lower() for x in ["notify me", "me prévenir", "avvisami"]):
        return "🟡 NOTIFY ME"
    else:
        return "🟠 PRODUCT VISIBLE"


async def main():
    timestamp = datetime.utcnow().strftime("%d %b %Y at %H:%M UTC")
    alerts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="en-GB",
        )
        page = await ctx.new_page()

        for label, url, keyword in URLS:
            print(f"Checking {label}...")
            try:
                status = await check_url(page, label, url, keyword)
                if status:
                    print(f"  *** {status} ***")
                    alerts.append((label, url, keyword, status))
                else:
                    print(f"  Clear")
            except Exception as e:
                print(f"  Error: {e}")

        await browser.close()

    urgency_map = {
        "🔴 ADD TO CART":    "Go to Hermès immediately and add to cart — sells out within minutes.",
        "🟡 NOTIFY ME":      "Register your interest on Hermès NOW.",
        "🟠 PRODUCT VISIBLE": "Go check Hermès immediately — it may be available to order.",
    }

    for label, url, keyword, status in alerts:
        msg = (
            f"🚨 HERMÈS ALERT — {keyword}\n\n"
            f"{status}\n\n"
            f"Region: {label}\n"
            f"URL: {url}\n"
            f"Detected: {timestamp}\n\n"
            f"{urgency_map.get(status, 'Check Hermès now.')}"
        )
        send_telegram(msg)

    if not alerts:
        print(f"✓ No stock found — {timestamp}")


asyncio.run(main())
