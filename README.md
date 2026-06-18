# 🎵 Spotify Discovery Intelligence Engine

An AI-powered research system that analyzes thousands of real user reviews across App Store, Play Store, and Reddit to uncover why music discovery fails — and what users actually want.

Built with **Groq + Llama 3**, **PRAW**, and **Streamlit**.

---

## What It Does

Most music discovery research relies on surveys or assumptions. This system pulls real user feedback at scale and lets AI find the patterns.

It answers questions like:
- Why do users struggle to discover new music?
- What causes repetitive listening behavior?
- Which user segments face different discovery challenges?
- What unmet needs appear consistently across all sources?

---

## How It Works

```
App Store + Play Store + Reddit
            ↓
     Python scrapers collect
     and clean raw reviews
            ↓
    Groq + Llama 3 analyzes
    in batches — extracts themes,
    segments users, finds unmet needs
            ↓
     Streamlit interface lets
     you query the findings
     in plain English
```

---

## Live Demo

👉 **[Open the live app](https://spotify-discovery-engine.streamlit.app)**

Add your credentials in the sidebar and click **Run Analysis**. Takes about 2 minutes to collect and analyze data.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| AI Analysis | Groq + Llama 3 (70B) | Free, fast, no expiry |
| Reddit Data | PRAW (Reddit API) | Free, official API |
| Play Store Data | google-play-scraper | Free, no key needed |
| App Store Data | app-store-scraper | Free, no key needed |
| Interface | Streamlit | Free hosting, shareable link |

---

## Setup (if running locally)

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/spotify-discovery-engine
cd spotify-discovery-engine
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your credentials**

Create a `.env` file:
```
GROQ_API_KEY=your_groq_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

**4. Run**
```bash
streamlit run app.py
```

---

## Getting API Keys

**Groq API Key** (free, no expiry)
- Go to [groq.com](https://groq.com) → sign up → API Keys → Create

**Reddit API Credentials** (free, no expiry)
- Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
- Click "create another app"
- Select "script"
- Redirect URI: `http://localhost:8080`
- Copy your Client ID and Client Secret

---

## Project Structure

```
spotify-discovery-engine/
├── app.py            # Streamlit interface
├── scraper.py        # Data collection (Reddit + stores)
├── analyzer.py       # Groq AI analysis engine
├── requirements.txt  # Dependencies
└── README.md
```

---

## What the Analysis Produces

- **Themes** — recurring pain points ranked by mention frequency
- **User Segments** — distinct listener types with different discovery challenges
- **Unmet Needs** — gaps between what users want and what Spotify delivers
- **Q&A Engine** — ask any research question, get an answer grounded in real reviews
