"""
scraper.py
Collects reviews from Reddit, Google Play Store, and Apple App Store.
All sources feed into one unified, clean format.
"""

import praw
import pandas as pd
from google_play_scraper import reviews as gplay_reviews, Sort
from app_store_scraper import AppStore
import streamlit as st
from datetime import datetime
import time


# ─── Unified review schema ───────────────────────────────────────────────────
# Every source produces rows with these exact keys:
# source | text | rating | date | upvotes

def _clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(str(text).split())  # collapse whitespace


# ─── Reddit ──────────────────────────────────────────────────────────────────

def fetch_reddit(client_id: str, client_secret: str, limit: int = 150) -> pd.DataFrame:
    """
    Pull posts + top comments from Spotify-related subreddits.
    Focuses on discovery and recommendation frustrations.
    """
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="SpotifyDiscoveryResearch/1.0"
    )

    subreddits = ["spotify", "SpotifyMusic", "music"]
    queries = [
        "music discovery frustrating",
        "spotify recommend same songs",
        "stuck listening same music",
        "spotify algorithm bubble",
        "new music discovery",
        "repeat playlist spotify",
        "spotify recommendation bad",
    ]

    rows = []
    seen = set()

    for subreddit_name in subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        for query in queries[:3]:  # limit queries per subreddit to stay fast
            try:
                for submission in subreddit.search(query, limit=10, sort="relevance", time_filter="year"):
                    if submission.id in seen:
                        continue
                    seen.add(submission.id)

                    # Add the post itself
                    if len(submission.selftext) > 50:
                        rows.append({
                            "source": "Reddit",
                            "text": _clean(submission.title + " " + submission.selftext),
                            "rating": None,
                            "date": datetime.utcfromtimestamp(submission.created_utc).strftime("%Y-%m-%d"),
                            "upvotes": submission.score,
                        })

                    # Add top comments
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:5]:
                        if len(comment.body) > 80:
                            rows.append({
                                "source": "Reddit",
                                "text": _clean(comment.body),
                                "rating": None,
                                "date": datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%d"),
                                "upvotes": comment.score,
                            })

                    if len(rows) >= limit:
                        break
                if len(rows) >= limit:
                    break
            except Exception:
                continue
        if len(rows) >= limit:
            break

    return pd.DataFrame(rows[:limit])


# ─── Google Play Store ───────────────────────────────────────────────────────

def fetch_play_store(count: int = 200) -> pd.DataFrame:
    """
    Scrape Spotify reviews from Google Play Store.
    Pulls both recent and most-relevant reviews.
    """
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

def fetch_app_store(count: int = 100) -> pd.DataFrame:
    """
    Scrape Spotify reviews from Apple App Store.
    """
    rows = []

    try:
        app = AppStore(country="us", app_name="spotify-music", app_id="324684580")
        app.review(how_many=count)

        for r in app.reviews:
            if r.get("review") and len(r["review"]) > 40:
                rows.append({
                    "source": "App Store",
                    "text": _clean(r["review"]),
                    "rating": r.get("rating"),
                    "date": r["date"].strftime("%Y-%m-%d") if r.get("date") else None,
                    "upvotes": 0,
                })
    except Exception as e:
        st.warning(f"App Store scraping partial: {e}")

    return pd.DataFrame(rows)


# ─── Master collector ─────────────────────────────────────────────────────────

def collect_all(reddit_client_id: str, reddit_client_secret: str) -> pd.DataFrame:
    """
    Runs all three scrapers and returns one unified DataFrame.
    Deduplicates and filters very short entries.
    """
    dfs = []

    with st.status("Collecting data from all sources...", expanded=True) as status:
        st.write("📱 Scraping Google Play Store reviews...")
        play_df = fetch_play_store(200)
        st.write(f"   ✓ {len(play_df)} Play Store reviews collected")
        dfs.append(play_df)
        time.sleep(1)

        st.write("🍎 Scraping Apple App Store reviews...")
        apple_df = fetch_app_store(100)
        st.write(f"   ✓ {len(apple_df)} App Store reviews collected")
        dfs.append(apple_df)
        time.sleep(1)

        st.write("💬 Fetching Reddit discussions...")
        reddit_df = fetch_reddit(reddit_client_id, reddit_client_secret, 150)
        st.write(f"   ✓ {len(reddit_df)} Reddit posts/comments collected")
        dfs.append(reddit_df)

        status.update(label="Data collection complete!", state="complete")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["text"])
    combined = combined[combined["text"].str.len() > 50]
    combined = combined.drop_duplicates(subset=["text"])
    combined = combined.reset_index(drop=True)

    return combined
