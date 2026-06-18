"""
app.py
Spotify Discovery Intelligence Engine
Streamlit interface — what evaluators see and interact with.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq

from scraper import collect_all
from analyzer import run_full_analysis, answer_question

# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Spotify Discovery Intelligence Engine",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Dark Spotify-inspired theme */
    .stApp { background-color: #0d0d0d; color: #ffffff; }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1DB954, #1ed760);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #b3b3b3;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1DB954;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #b3b3b3;
        margin-top: 0.2rem;
    }
    .theme-card {
        background: #1a1a1a;
        border-left: 3px solid #1DB954;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .theme-name {
        font-weight: 600;
        font-size: 1rem;
        color: #ffffff;
        text-transform: capitalize;
    }
    .theme-desc {
        color: #b3b3b3;
        font-size: 0.875rem;
        margin-top: 0.3rem;
    }
    .theme-quote {
        color: #1DB954;
        font-size: 0.8rem;
        font-style: italic;
        margin-top: 0.5rem;
        padding-left: 0.75rem;
        border-left: 2px solid #1DB954;
    }
    .segment-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.75rem;
    }
    .segment-name {
        font-weight: 700;
        font-size: 1.05rem;
        color: #1DB954;
    }
    .need-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .answer-box {
        background: #1a1a1a;
        border: 1px solid #1DB954;
        border-radius: 12px;
        padding: 1.5rem;
        color: #e0e0e0;
        line-height: 1.7;
        font-size: 0.95rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-neg { background: #3d1515; color: #ff6b6b; }
    .badge-pos { background: #0d2e1a; color: #1DB954; }
    .badge-neu { background: #2a2a2a; color: #b3b3b3; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #111111; }
    
    /* Buttons */
    .stButton > button {
        background: #1DB954;
        color: #000000;
        border: none;
        border-radius: 25px;
        font-weight: 700;
        padding: 0.5rem 2rem;
        font-size: 0.95rem;
    }
    .stButton > button:hover { background: #1ed760; }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        color: #ffffff;
        border-radius: 8px;
    }
    .stTextArea > div > div > textarea {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        color: #ffffff;
        border-radius: 8px;
    }
    
    div[data-testid="stMetricValue"] { color: #1DB954; }
    
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #2a2a2a;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar — credentials ────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎵 Configuration")
    st.markdown("---")

    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Get yours free at groq.com"
    )

    st.markdown("**Reddit API**")
    reddit_id = st.text_input(
        "Client ID",
        type="password",
        placeholder="Your Reddit client ID"
    )
    reddit_secret = st.text_input(
        "Client Secret",
        type="password",
        placeholder="Your Reddit client secret"
    )

    st.markdown("---")
    st.markdown("**Data collection settings**")
    review_depth = st.select_slider(
        "Review volume",
        options=["Quick (200)", "Standard (400)", "Deep (600)"],
        value="Standard (400)"
    )

    st.markdown("---")
    st.markdown(
        "<div style='color:#b3b3b3; font-size:0.8rem;'>Analyzes App Store, Play Store & Reddit in real time using Groq + Llama 3</div>",
        unsafe_allow_html=True
    )


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown('<div class="main-title">Spotify Discovery Intelligence Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered analysis of user feedback across App Store, Play Store & Reddit — uncovering why music discovery fails</div>',
    unsafe_allow_html=True
)

# ─── Session state ────────────────────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results = None
if "df" not in st.session_state:
    st.session_state.df = None


# ─── Main CTA ────────────────────────────────────────────────────────────────

col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_analysis = st.button("▶ Run Analysis", use_container_width=True)
with col_info:
    if not st.session_state.results:
        st.markdown(
            "<div style='color:#b3b3b3; padding-top:0.6rem; font-size:0.9rem;'>Add your credentials in the sidebar, then click Run Analysis. Takes ~2 minutes.</div>",
            unsafe_allow_html=True
        )

if run_analysis:
    if not groq_key or not reddit_id or not reddit_secret:
        st.error("Please fill in all credentials in the sidebar first.")
    else:
        with st.spinner(""):
            # Step 1: Collect
            df = collect_all(reddit_id, reddit_secret)
            st.session_state.df = df

            # Step 2: Analyze
            with st.status("Running AI analysis with Groq + Llama 3...", expanded=True) as status:
                st.write("🧠 Extracting recurring themes...")
                st.write("👥 Identifying user segments...")
                st.write("💡 Surfacing unmet needs...")
                results = run_full_analysis(groq_key, df)
                st.session_state.results = results
                status.update(label="Analysis complete!", state="complete")

        st.success(f"✓ Analyzed {results['total_reviews']} data points across 3 sources")
        st.rerun()


# ─── Results ─────────────────────────────────────────────────────────────────

if st.session_state.results:
    results = st.session_state.results
    df = st.session_state.df

    # ── Overview metrics ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Data Overview</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    source_breakdown = results.get("source_breakdown", {})

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{results['total_reviews']}</div>
            <div class="metric-label">Total data points analyzed</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{source_breakdown.get('Play Store', 0)}</div>
            <div class="metric-label">Play Store reviews</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{source_breakdown.get('App Store', 0)}</div>
            <div class="metric-label">App Store reviews</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{source_breakdown.get('Reddit', 0)}</div>
            <div class="metric-label">Reddit discussions</div>
        </div>""", unsafe_allow_html=True)

    # ── Source distribution chart ─────────────────────────────────────────────
    if source_breakdown:
        fig_source = px.pie(
            names=list(source_breakdown.keys()),
            values=list(source_breakdown.values()),
            color_discrete_sequence=["#1DB954", "#158a3e", "#0d5c2a"],
            hole=0.5,
        )
        fig_source.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=20, b=20),
            height=250,
        )
        st.plotly_chart(fig_source, use_container_width=True)

    # ── Themes ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔍 Discovery Pain Point Themes</div>', unsafe_allow_html=True)

    themes = results.get("themes", {})
    if themes:
        # Sort by mention count
        sorted_themes = sorted(themes.values(), key=lambda x: x.get("mention_count", 0), reverse=True)

        # Bar chart
        theme_names = [t["name"].title() for t in sorted_themes[:8]]
        theme_counts = [t.get("mention_count", 1) for t in sorted_themes[:8]]

        fig_themes = go.Figure(go.Bar(
            x=theme_counts,
            y=theme_names,
            orientation="h",
            marker_color="#1DB954",
        ))
        fig_themes.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
            xaxis=dict(gridcolor="#2a2a2a", title="Mention frequency"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=300,
        )
        st.plotly_chart(fig_themes, use_container_width=True)

        # Theme cards
        col_left, col_right = st.columns(2)
        for i, theme in enumerate(sorted_themes[:8]):
            sentiment = theme.get("sentiment", "neutral")
            badge_class = {"negative": "badge-neg", "positive": "badge-pos"}.get(sentiment, "badge-neu")
            card_html = f"""
            <div class="theme-card">
                <div class="theme-name">{theme['name'].title()}
                    <span class="badge {badge_class}" style="margin-left:8px;">{sentiment}</span>
                </div>
                <div class="theme-desc">{theme.get('description', '')}</div>
                <div class="theme-quote">"{theme.get('representative_quote', '')}"</div>
            </div>"""
            if i % 2 == 0:
                col_left.markdown(card_html, unsafe_allow_html=True)
            else:
                col_right.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("No themes extracted yet.")

    # ── User Segments ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">👥 User Segments & Discovery Challenges</div>', unsafe_allow_html=True)

    segments = results.get("segments", [])
    if segments:
        for seg in segments:
            st.markdown(f"""
            <div class="segment-card">
                <div class="segment-name">{seg.get('name', 'Segment')}</div>
                <div style="color:#b3b3b3; font-size:0.875rem; margin-top:0.3rem;">{seg.get('description', '')}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-top:0.75rem;">
                    <div>
                        <div style="color:#888; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em;">Discovery Challenge</div>
                        <div style="color:#e0e0e0; font-size:0.875rem; margin-top:0.2rem;">{seg.get('discovery_challenge', '')}</div>
                    </div>
                    <div>
                        <div style="color:#888; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em;">Unmet Need</div>
                        <div style="color:#1DB954; font-size:0.875rem; margin-top:0.2rem;">{seg.get('unmet_need', '')}</div>
                    </div>
                </div>
                <div style="color:#666; font-size:0.8rem; font-style:italic; margin-top:0.75rem; border-left:2px solid #2a2a2a; padding-left:0.75rem;">"{seg.get('example_quote', '')}"</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No segments identified yet.")

    # ── Unmet Needs ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">💡 Top Unmet Needs</div>', unsafe_allow_html=True)

    unmet_needs = results.get("unmet_needs", [])
    if unmet_needs:
        for need in unmet_needs:
            freq = need.get("frequency", "common")
            freq_color = {"very common": "#ff6b6b", "common": "#ffa500", "occasional": "#1DB954"}.get(freq, "#b3b3b3")
            st.markdown(f"""
            <div class="need-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div style="font-weight:600; font-size:1rem; color:#ffffff;">{need.get('need', '')}</div>
                    <span style="color:{freq_color}; font-size:0.75rem; font-weight:600; text-transform:uppercase;">{freq}</span>
                </div>
                <div style="color:#b3b3b3; font-size:0.875rem; margin-top:0.4rem;">{need.get('explanation', '')}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-top:0.75rem;">
                    <div>
                        <div style="color:#888; font-size:0.75rem; text-transform:uppercase;">Current Gap</div>
                        <div style="color:#e0e0e0; font-size:0.825rem; margin-top:0.2rem;">{need.get('current_gap', '')}</div>
                    </div>
                    <div>
                        <div style="color:#888; font-size:0.75rem; text-transform:uppercase;">Opportunity</div>
                        <div style="color:#1DB954; font-size:0.825rem; margin-top:0.2rem;">{need.get('opportunity', '')}</div>
                    </div>
                </div>
                <div style="color:#555; font-size:0.8rem; font-style:italic; margin-top:0.75rem;">"{need.get('supporting_quote', '')}"</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No unmet needs extracted yet.")

    # ── Q&A Interface ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🤖 Ask the Research Engine</div>', unsafe_allow_html=True)

    st.markdown(
        "<div style='color:#b3b3b3; font-size:0.875rem; margin-bottom:1rem;'>Ask any research question about music discovery. The AI answers using the collected reviews and identified patterns.</div>",
        unsafe_allow_html=True
    )

    preset_questions = [
        "Why do users struggle to discover new music?",
        "What causes users to repeatedly listen to the same content?",
        "Which user segments experience the most discovery challenges?",
        "What listening behaviors are users trying to achieve?",
        "What are the most common frustrations with Spotify recommendations?",
    ]

    selected_preset = st.selectbox(
        "Quick questions:",
        ["— choose a preset or type your own below —"] + preset_questions
    )

    custom_q = st.text_area(
        "Or type your own question:",
        value=selected_preset if selected_preset != "— choose a preset or type your own below —" else "",
        placeholder="e.g. Why do users feel like Spotify keeps them in an echo chamber?",
        height=80,
    )

    if st.button("Get Answer", key="qa_btn"):
        if custom_q.strip():
            with st.spinner("Analyzing reviews to answer your question..."):
                client = Groq(api_key=groq_key)
                answer = answer_question(
                    client,
                    custom_q,
                    results["reviews"],
                    results["themes"],
                )
            st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
        else:
            st.warning("Please enter a question first.")

    # ── Raw data preview ──────────────────────────────────────────────────────
    with st.expander("📄 View raw collected data"):
        st.dataframe(
            df[["source", "text", "rating", "date", "upvotes"]].head(100),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing first 100 of {len(df)} total entries")

else:
    # Empty state
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; padding: 3rem 0; color:#b3b3b3;">
        <div style="font-size:3rem; margin-bottom:1rem;">🎵</div>
        <div style="font-size:1.1rem; font-weight:600; color:#ffffff; margin-bottom:0.5rem;">Ready to analyze</div>
        <div style="font-size:0.9rem;">Add your credentials in the sidebar and click <strong style="color:#1DB954;">Run Analysis</strong> to begin.</div>
        <div style="font-size:0.85rem; margin-top:1rem;">Pulls real data from App Store · Play Store · Reddit → analyzes with Groq Llama 3</div>
    </div>
    """, unsafe_allow_html=True)
