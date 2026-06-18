"""
scraper.py
Collects reviews from Google Play Store and Trustpilot.
No API keys needed. No dependency conflicts.
"""

import pandas as pd
from google_play_scraper import reviews as gplay_reviews, Sort
import streamlit as st
import requests
from bs4 import BeautifulSoup
import time


def _clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())


# ─── Google Play Store ───────────────────────────────────────────────────────

def fetch_play_store(count: int = 400) -> pd.DataFrame:
    rows = []
    try:
        for sort_order in [Sort.MOST_RELEVANT, Sort.NEWEST]:
            result, _ = gplay_reviews(
                "com.spotify.music",
                lang="en",
                country="us",
                sort=sort_order,
                count=count // 2,
                filter_score_with=None,
            )
            for r in result:
                if r.get("content") and len(r["content"]) > 40:
                    rows.append({
                        "source": "Play Store",
                        "text": _clean(r["content"]),
                        "rating": r.get("score"),
                        "date": r["at"].strftime("%Y-%m-%d") if r.get("at") else None,
                        "upvotes": r.get("thumbsUpCount", 0),
                    })
    except Exception as e:
        st.warning(f"Play Store scraping partial: {e}")
    return pd.DataFrame(rows)


# ─── Apple App Store (via Apple RSS API — no library needed) ─────────────────

def fetch_app_store(count: int = 200) -> pd.DataFrame:
    rows = []
    try:
        # Apple's official RSS feed — free, no key, no library
        for page in range(1, 11):  # 10 pages x 50 reviews = 500 max
            url = f"https://itunes.apple.com/us/rss/customerreviews/page={page}/id=324684580/sortby=mostrecent/json"
            response = requests.get(url, timeout=10)
            data = response.json()
            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break
            for entry in entries:
                # Skip the first entry which is app metadata not a review
                if "im:rating" not in entry:
                    continue
                text = _clean(entry.get("content", {}).get("label", ""))
                if len(text) > 40:
                    rows.append({
                        "source": "App Store",
                        "text": text,
                        "rating": int(entry.get("im:rating", {}).get("label", 0)),
                        "date": entry.get("updated", {}).get("label", "")[:10],
                        "upvotes": 0,
                    })
            if len(rows) >= count:
                break
            time.sleep(0.5)
    except Exception as e:
        st.warning(f"App Store scraping partial: {e}")
    return pd.DataFrame(rows[:count])


# ─── Trustpilot ──────────────────────────────────────────────────────────────

def fetch_trustpilot(pages: int = 10) -> pd.DataFrame:
    rows = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for page in range(1, pages + 1):
        try:
            url = f"https://www.trustpilot.com/review/www.spotify.com?page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            review_cards = soup.find_all("article", {"data-service-review-card-paper": True})

            for card in review_cards:
                text_el = card.find("p", {"data-service-review-text-typography": True})
                rating_el = card.find("div", {"data-service-review-rating": True})
                date_el = card.find("time")

                text = _clean(text_el.get_text()) if text_el else ""
                if len(text) > 40:
                    rows.append({
                        "source": "Trustpilot",
                        "text": text,
                        "rating": int(rating_el.get("data-service-review-rating", 0)) if rating_el else None,
                        "date": date_el.get("datetime", "")[:10] if date_el else None,
                        "upvotes": 0,
                    })
            time.sleep(0.8)
        except Exception:
            continue
    return pd.DataFrame(rows)


# ─── Master collector ─────────────────────────────────────────────────────────

def collect_all() -> pd.DataFrame:
    dfs = []

    with st.status("Collecting data from all sources...", expanded=True) as status:
        st.write("📱 Scraping Google Play Store reviews...")
        play_df = fetch_play_store(400)
        st.write(f"   ✓ {len(play_df)} Play Store reviews collected")
        dfs.append(play_df)
        time.sleep(1)

        st.write("🍎 Scraping Apple App Store reviews...")
        apple_df = fetch_app_store(200)
        st.write(f"   ✓ {len(apple_df)} App Store reviews collected")
        dfs.append(apple_df)
        time.sleep(1)

        st.write("⭐ Scraping Trustpilot reviews...")
        trust_df = fetch_trustpilot(10)
        st.write(f"   ✓ {len(trust_df)} Trustpilot reviews collected")
        dfs.append(trust_df)

        status.update(label="Data collection complete!", state="complete")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["text"])
    combined = combined[combined["text"].str.len() > 50]
    combined = combined.drop_duplicates(subset=["text"])
    combined = combined.reset_index(drop=True)

    return combined
