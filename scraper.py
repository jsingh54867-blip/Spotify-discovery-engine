"""
scraper.py
Collects reviews from Google Play Store, Apple App Store, and Trustpilot.
All sources feed into one unified, clean format.
"""

import pandas as pd
from google_play_scraper import reviews as gplay_reviews, Sort
from itunes_app_scraper.scraper import AppStoreScraper
import streamlit as st
import requests
from bs4 import BeautifulSoup
import time


def _clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())


# ─── Google Play Store ───────────────────────────────────────────────────────

def fetch_play_store(count: int = 300) -> pd.DataFrame:
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


# ─── Apple App Store ─────────────────────────────────────────────────────────

def fetch_app_store(count: int = 200) -> pd.DataFrame:
    rows = []
    try:
        scraper = AppStoreScraper()
        reviews = scraper.get_app_reviews(
            app_id="324684580",
            countries=["us", "gb", "in"],
            num=count
        )
        for r in reviews:
            text = _clean(r.get("review", ""))
            if len(text) > 40:
                rows.append({
                    "source": "App Store",
                    "text": text,
                    "rating": r.get("rating"),
                    "date": str(r.get("date", ""))[:10],
                    "upvotes": 0,
                })
    except Exception as e:
        st.warning(f"App Store scraping partial: {e}")
    return pd.DataFrame(rows)


# ─── Trustpilot ──────────────────────────────────────────────────────────────

def fetch_trustpilot(pages: int = 8) -> pd.DataFrame:
    rows = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for page in range(1, pages + 1):
        try:
            url = f"https://www.trustpilot.com/review/www.spotify.com?page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            reviews = soup.find_all("div", {"data-service-review-text-typography": True})
            ratings = soup.find_all("div", {"data-service-review-rating": True})
            dates = soup.find_all("time")

            for i, review in enumerate(reviews):
                text = _clean(review.get_text())
                if len(text) > 40:
                    rows.append({
                        "source": "Trustpilot",
                        "text": text,
                        "rating": int(ratings[i].get("data-service-review-rating", 0)) if i < len(ratings) else None,
                        "date": dates[i].get("datetime", "")[:10] if i < len(dates) else None,
                        "upvotes": 0,
                    })
            time.sleep(0.5)
        except Exception:
            continue
    return pd.DataFrame(rows)


# ─── Master collector ─────────────────────────────────────────────────────────

def collect_all() -> pd.DataFrame:
    dfs = []

    with st.status("Collecting data from all sources...", expanded=True) as status:
        st.write("📱 Scraping Google Play Store reviews...")
        play_df = fetch_play_store(300)
        st.write(f"   ✓ {len(play_df)} Play Store reviews collected")
        dfs.append(play_df)
        time.sleep(1)

        st.write("🍎 Scraping Apple App Store reviews...")
        apple_df = fetch_app_store(200)
        st.write(f"   ✓ {len(apple_df)} App Store reviews collected")
        dfs.append(apple_df)
        time.sleep(1)

        st.write("⭐ Scraping Trustpilot reviews...")
        trust_df = fetch_trustpilot(8)
        st.write(f"   ✓ {len(trust_df)} Trustpilot reviews collected")
        dfs.append(trust_df)

        status.update(label="Data collection complete!", state="complete")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["text"])
    combined = combined[combined["text"].str.len() > 50]
    combined = combined.drop_duplicates(subset=["text"])
    combined = combined.reset_index(drop=True)

    return combined
