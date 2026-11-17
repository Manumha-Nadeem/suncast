"""
SunCast frontend (Streamlit). Member 3.
Talks to the FastAPI backend. If BACKEND_URL is not set in
Streamlit secrets, it runs in MOCK mode with fake data.

Layout: top bar, hero, input card, then three folder tabs
(Forecast, Solar shops, Ask SunCast). All styling lives in the CSS
block below; the backend calls are in the "backend calls" section.
"""

import html
import math
import random
from datetime import date, timedelta

import altair as alt
import pandas as pd
import requests
import streamlit as st

CITIES = ["Lahore", "Karachi", "Islamabad", "Peshawar", "Multan"]

# ---------------- palette (same values as the CSS variables) ----------------
PAPER = "#F4EBDD"
CARD = "#FBF6EE"
INK = "#2B2118"
INK_SOFT = "#6B5B4B"
TERRACOTTA = "#C2552D"
OCHRE = "#D9A23A"
OLIVE = "#6F7A3E"
SAGE = "#C9CFAE"
CLAY = "#E8C9A9"
MONO = "JetBrains Mono, monospace"

st.set_page_config(page_title="SunCast", page_icon="☀️", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------- CSS (palette variables first) ----------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
  --paper: #F4EBDD; --card: #FBF6EE; --ink: #2B2118; --ink-soft: #6B5B4B;
  --terracotta: #C2552D; --ochre: #D9A23A; --olive: #6F7A3E;
  --sage: #C9CFAE; --clay: #E8C9A9;
}

/* base */
.stApp { background: var(--paper); color: var(--ink); }
.stApp, .stApp p, .stApp label, .stApp button, .stApp li {
  font-family: 'Bricolage Grotesque', sans-serif;
}
.block-container { max-width: 1100px; padding-top: 1.5rem; padding-bottom: 3rem; }
.mono { font-family: 'JetBrains Mono', monospace !important; }

/* hide default Streamlit chrome */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], #MainMenu, footer {
  display: none !important;
}

/* top bar */
.sc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem; }
.sc-logo { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 1.5rem;
  letter-spacing: -0.02em; }
.sc-nav a { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--ink-soft);
  margin-left: 1.4rem; text-decoration: none; }
.sc-nav a:hover { color: var(--terracotta); }

/* hero */
.sc-hero { display: grid; grid-template-columns: 1.2fr 1fr; gap: 1.5rem; align-items: center;
  margin-bottom: 1.8rem; }
.sc-hero h1 { font-weight: 800; font-size: clamp(2.4rem, 5vw, 3.6rem); line-height: 1.02;
  letter-spacing: -0.03em; margin: 0.9rem 0; padding: 0; color: var(--ink); }
.sc-mark { display: inline-block; background: var(--ochre); border: 2px solid var(--ink);
  box-shadow: 3px 3px 0 var(--ink); padding: 0 10px; transform: rotate(-1.2deg); }
.sc-hero p { color: var(--ink-soft); font-size: 1.05rem; max-width: 30rem; }
.sc-hero svg { width: 100%; height: auto; }
@media (max-width: 760px) { .sc-hero { grid-template-columns: 1fr; } }

/* tags */
.sc-tag { display: inline-block; background: var(--sage); border: 1.5px solid var(--ink);
  border-radius: 4px; padding: 1px 7px; font-family: 'JetBrains Mono', monospace;
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink); }

/* cards (every st.container with a key starting with card_) */
[class*="st-key-card_"] { background: var(--card); border: 2px solid var(--ink);
  border-radius: 8px; box-shadow: 4px 4px 0 var(--ink); padding: 1rem 1.25rem; }
.sc-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 0.4rem; }
.sc-step { font-weight: 800; font-size: 1.3rem; margin-right: 8px; }
.sc-hint { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--ink-soft);
  margin-top: -0.7rem; }
.sc-ticks { display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem; color: var(--ink-soft); margin-top: -0.6rem; }

/* inputs */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
  background: #FFF8EF !important; border: 2px solid var(--ink) !important;
  border-radius: 6px !important; box-shadow: none !important; }
div[data-baseweb="base-input"] { background: transparent !important; border: none !important; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
  outline: 2px solid var(--terracotta) !important; }
.stApp input, div[data-baseweb="select"] * { font-family: 'JetBrains Mono', monospace !important; }
div[data-baseweb="slider"] div[role="slider"] { border-radius: 4px !important;
  border: 2px solid var(--ink) !important; background: var(--terracotta) !important; }

/* buttons: rectangular, hard shadow, lift on hover, press on click */
.stApp .stButton > button, .stApp [data-testid="stFormSubmitButton"] > button {
  border: 2px solid var(--ink); border-radius: 6px; background: var(--card); color: var(--ink);
  font-weight: 700; box-shadow: 3px 3px 0 var(--ink); transition: transform .08s, box-shadow .08s; }
.stApp .stButton > button:hover, .stApp [data-testid="stFormSubmitButton"] > button:hover {
  transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--ink); color: var(--ink);
  border-color: var(--ink); }
.stApp .stButton > button:active, .stApp [data-testid="stFormSubmitButton"] > button:active {
  transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--ink); }
.stApp button[data-testid="stBaseButton-primary"], .stApp button[data-testid="stBaseButton-primaryFormSubmit"],
.stApp button[kind="primary"], .stApp button[kind="primaryFormSubmit"] {
  background: var(--terracotta) !important; color: #FFFFFF !important; }
.stApp button[data-testid="stBaseButton-primary"] p, .stApp button[data-testid="stBaseButton-primaryFormSubmit"] p,
.stApp button[kind="primary"] p, .stApp button[kind="primaryFormSubmit"] p { color: #FFFFFF !important; }

/* folder tabs */
div[role="tablist"] { gap: 6px; border-bottom: 2px solid var(--ink) !important; }
button[role="tab"] { background: var(--clay) !important; border: 2px solid var(--ink) !important;
  border-bottom: none !important; border-radius: 6px 6px 0 0 !important; padding: 6px 16px !important;
  margin-bottom: -2px; }
button[role="tab"][aria-selected="true"] { background: var(--card) !important; }
button[role="tab"] p { font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem;
  color: var(--ink) !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* headings and stat cards */
.sc-h2 { font-weight: 800; font-size: 1.7rem; letter-spacing: -0.02em; margin: 1.2rem 0 1rem; }
.sc-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem; }
.sc-stat { background: var(--card); border: 2px solid var(--ink); border-radius: 8px;
  box-shadow: 4px 4px 0 var(--ink); padding: 0.8rem 1.1rem; transition: transform .1s; }
.sc-stat:hover, .sc-shop:hover { transform: translateY(-2px); }
.sc-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.08em;
  color: var(--ink-soft); text-transform: uppercase; }
.sc-value { font-family: 'JetBrains Mono', monospace; font-size: 2.5rem; font-weight: 700; }
.sc-unit { font-size: 0.9rem; font-weight: 400; color: var(--ink-soft); }
@media (max-width: 760px) { .sc-stats { grid-template-columns: 1fr; } }

/* appliance banner */
.sc-banner { display: flex; gap: 14px; align-items: center; background: var(--ochre);
  border: 2px solid var(--ink); border-radius: 8px; box-shadow: 4px 4px 0 var(--ink);
  padding: 0.8rem 1.1rem; margin-bottom: 1.2rem; }
.sc-banner b { display: block; font-size: 1.05rem; }
.sc-banner span { font-size: 0.9rem; }

/* notes, empty state, error card */
.sc-note { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--ink-soft);
  margin-top: 0.8rem; }
.sc-empty { text-align: center; padding: 1.5rem 0; color: var(--ink-soft); }
.sc-empty svg { width: 130px; height: auto; }
.sc-empty p { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; margin-top: 0.4rem; }
.sc-error { background: var(--card); border: 2px solid var(--ink); border-left: 8px solid var(--terracotta);
  border-radius: 8px; box-shadow: 4px 4px 0 var(--ink); padding: 0.8rem 1.1rem; margin: 0.8rem 0; }
.sc-error b { display: block; }
.sc-error span { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--ink-soft); }
.sc-mock { background: var(--clay); border: 2px solid var(--ink); border-radius: 8px;
  padding: 0.5rem 1rem; margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }

/* daily table */
[data-testid="stExpander"] { background: var(--card); border: 2px solid var(--ink) !important;
  border-radius: 8px; box-shadow: 4px 4px 0 var(--ink); margin-top: 1.2rem; }
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { background: transparent; }
.sc-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem; }
.sc-table th { text-align: right; color: var(--ink-soft); font-weight: 400;
  border-bottom: 2px solid var(--ink); padding: 6px 8px; }
.sc-table td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--sage); }
.sc-table th:first-child, .sc-table td:first-child { text-align: left; }

/* shop cards */
.sc-shops { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.sc-shop { background: var(--card); border: 2px solid var(--ink); border-radius: 8px;
  box-shadow: 4px 4px 0 var(--ink); padding: 0.9rem 1.1rem; transition: transform .1s; }
.sc-shop-name { font-weight: 800; font-size: 1.05rem; }
.sc-shop-area { color: var(--ink-soft); font-size: 0.85rem; margin-bottom: 0.7rem; }
.sc-shop-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.sc-call { border: 2px solid var(--ink); border-radius: 6px; background: var(--card);
  box-shadow: 2px 2px 0 var(--ink); padding: 3px 9px; font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; color: var(--ink) !important; text-decoration: none; }
.sc-call:hover { background: var(--clay); }
@media (max-width: 900px) { .sc-shops { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .sc-shops { grid-template-columns: 1fr; } }

/* chat bubbles (st.container keys user_msg_* and bot_msg_*) */
[class*="st-key-user_msg_"] { background: var(--clay); border: 2px solid var(--ink);
  border-radius: 8px; padding: 0.5rem 0.9rem; }
[class*="st-key-bot_msg_"] { background: var(--card); border: 2px solid var(--ink);
  border-radius: 8px; padding: 0.5rem 0.9rem; }

.sc-foot { text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
  color: var(--ink-soft); margin-top: 2.5rem; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ---------------- illustrations (inline SVG, drawn with the palette) ----------------

def ray_lines(cx, cy, r1, r2a, r2b):
    """Eight uneven sun rays around (cx, cy), alternating long and short."""
    out = ""
    for i in range(8):
        a = math.radians(i * 45 + 8)
        r2 = r2a if i % 2 == 0 else r2b
        out += (f'<line x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" '
                f'x2="{cx + r2 * math.cos(a):.1f}" y2="{cy + r2 * math.sin(a):.1f}"/>')
    return out


def sun_svg(size):
    """Small hand-drawn sun used as the logo and the chat avatar."""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">'
            f'<g stroke="{INK}" stroke-width="2.2" stroke-linecap="round">{ray_lines(20, 20, 12, 18, 16)}</g>'
            f'<circle cx="20" cy="20" r="8.5" fill="{OCHRE}" stroke="{INK}" stroke-width="2.2"/></svg>')


HERO_SVG = (
    f'<svg viewBox="0 0 400 250" xmlns="http://www.w3.org/2000/svg" stroke="{INK}" stroke-width="2.5" '
    f'stroke-linejoin="round" stroke-linecap="round">'
    f'<g>{ray_lines(330, 62, 40, 56, 50)}</g>'
    f'<circle cx="330" cy="62" r="30" fill="{OCHRE}"/>'
    f'<path d="M40 92 Q26 92 26 78 Q26 64 42 64 Q46 48 64 48 Q82 48 86 62 Q104 60 106 76 Q106 92 92 92 Z" fill="{CARD}"/>'
    f'<rect x="262" y="168" width="72" height="52" fill="{CLAY}"/>'
    f'<polygon points="256,170 298,140 340,170" fill="{OLIVE}"/>'
    f'<rect x="110" y="132" width="140" height="88" fill="{CARD}"/>'
    f'<polygon points="95,134 180,66 265,134" fill="{TERRACOTTA}"/>'
    f'<polygon points="132,122 160,98 178,110 150,130" fill="{OLIVE}"/>'
    f'<polygon points="186,110 206,98 230,116 210,128" fill="{OLIVE}"/>'
    f'<line x1="146" y1="110" x2="164" y2="120" stroke-width="1.5"/>'
    f'<line x1="196" y1="104" x2="220" y2="122" stroke-width="1.5"/>'
    f'<rect x="124" y="150" width="36" height="30" fill="{CLAY}"/>'
    f'<line x1="142" y1="150" x2="142" y2="180" stroke-width="1.5"/>'
    f'<line x1="124" y1="165" x2="160" y2="165" stroke-width="1.5"/>'
    f'<rect x="178" y="165" width="26" height="55" fill="{TERRACOTTA}"/>'
    f'<circle cx="198" cy="194" r="2" fill="{INK}"/>'
    f'<line x1="356" y1="220" x2="356" y2="186"/>'
    f'<circle cx="356" cy="172" r="18" fill="{SAGE}"/>'
    f'<rect x="30" y="220" width="340" height="12" fill="{SAGE}"/></svg>'
)

EMPTY_SVG = (
    f'<svg viewBox="0 0 130 90" xmlns="http://www.w3.org/2000/svg" stroke="{INK}" stroke-width="2.5" '
    f'stroke-linejoin="round" stroke-linecap="round">'
    f'<g>{ray_lines(70, 34, 24, 34, 30)}</g>'
    f'<circle cx="70" cy="34" r="18" fill="{OCHRE}"/>'
    f'<path d="M22 78 Q8 78 8 64 Q8 50 24 50 Q28 34 48 34 Q68 34 72 50 Q92 48 94 64 Q94 78 80 78 Z" fill="{CARD}"/></svg>'
)

WASHER_SVG = (
    f'<svg width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg" fill="none" '
    f'stroke="{INK}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    f'<rect x="6" y="4" width="26" height="30" rx="3" fill="{CARD}"/>'
    f'<circle cx="19" cy="22" r="7.5"/><line x1="10" y1="9" x2="14" y2="9"/>'
    f'<line x1="18" y1="9" x2="22" y2="9"/></svg>'
)

TOP_BAR = (
    f'<div class="sc-top"><div class="sc-logo">{sun_svg(34)}<span>SunCast</span></div>'
    f'<div class="sc-nav"><a href="#sc-tabs">Forecast</a><a href="#sc-tabs">Solar shops</a>'
    f'<a href="#sc-tabs">Ask SunCast</a></div></div>'
)

HERO = (
    f'<div class="sc-hero"><div>'
    f'<span class="sc-tag">Lahore · Karachi · Islamabad · Peshawar · Multan</span>'
    f'<h1>How much sun will your roof turn into <span class="sc-mark">rupees?</span></h1>'
    f'<p>Live weather forecasts, turned into kWh and savings for your exact system. '
    f'No sign up, no sales pitch.</p></div>'
    f'<div>{HERO_SVG}</div></div>'
)

st.markdown(TOP_BAR, unsafe_allow_html=True)
st.markdown(HERO, unsafe_allow_html=True)


# ---------------- config ----------------

def get_backend_url():
    try:
        return str(st.secrets.get("BACKEND_URL", "")).strip().rstrip("/")
    except Exception:
        return ""


BACKEND_URL = get_backend_url()
MOCK = BACKEND_URL == ""


# ---------------- mock data (same shape as the API) ----------------

def mock_predict(city, system_kw, tariff, days):
    daily, hourly = [], []
    total = 0.0
    start = date.today() + timedelta(days=1)
    for d in range(days):
        day = start + timedelta(days=d)
        day_kwh, day_base = 0.0, 0.0
        cloud = random.uniform(0.7, 1.0)
        for h in range(24):
            x = math.sin(math.pi * (h - 6) / 12) if 6 <= h <= 18 else 0.0
            base = max(x, 0) * system_kw * 0.86
            kw = base * cloud
            day_kwh += kw
            day_base += base
            hourly.append({
                "time": f"{day}T{h:02d}:00",
                "kw": round(kw, 3),
                "baseline_kw": round(base, 3),
            })
        total += day_kwh
        daily.append({
            "date": str(day),
            "kwh": round(day_kwh, 2),
            "savings_pkr": round(day_kwh * tariff),
            "baseline_kwh": round(day_base, 2),
        })
    return {
        "city": city, "model": "mock", "daily": daily, "hourly": hourly,
        "total_kwh": round(total, 2),
        "total_savings_pkr": round(total * tariff),
    }


MOCK_RETAILERS = [
    {"name": "Sample Solar Co", "area": "Gulberg", "contact": "0300-0000000", "rating": 4.5},
    {"name": "Demo Energy", "area": "DHA", "contact": "0321-0000000", "rating": 4.2},
]


# ---------------- backend calls (unchanged logic) ----------------

def api_error_text(resp):
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        return f"Server error ({resp.status_code})."
    if isinstance(detail, list):  # validation errors from FastAPI
        return "Please check your inputs."
    return str(detail)


def call_backend(method, path, **kwargs):
    """Returns (data, error_message)."""
    try:
        resp = requests.request(method, BACKEND_URL + path, timeout=90, **kwargs)
    except requests.exceptions.Timeout:
        return None, "The backend is taking too long. It may be waking up, please try again in a minute."
    except requests.exceptions.RequestException:
        return None, "Could not reach the backend. It may be waking up from sleep, please try again in a minute."
    if resp.status_code != 200:
        return None, api_error_text(resp)
    return resp.json(), None


def get_forecast(city, system_kw, tariff, days):
    if MOCK:
        return mock_predict(city, system_kw, tariff, days), None
    body = {"city": city, "system_kw": system_kw, "tariff_pkr": tariff, "days": days}
    return call_backend("POST", "/predict", json=body)


@st.cache_data(ttl=600, show_spinner=False)
def get_retailers(city, mock, url):
    if mock:
        return MOCK_RETAILERS, None
    return call_backend("GET", "/retailers", params={"city": city})


def get_chat_reply(message, city):
    if MOCK:
        return "(Mock mode) A battery is worth it mainly if you have long load shedding. Ask me again once the live backend is connected.", None
    data, err = call_backend("POST", "/chat", json={"message": message, "city": city})
    if err:
        return None, err
    return data.get("reply", ""), None


# ---------------- small html helpers ----------------

def error_card(detail):
    """Calm styled error instead of a red Streamlit box."""
    st.markdown(
        f'<div class="sc-error"><b>We couldn\'t reach the forecast right now. Try again in a minute.</b>'
        f'<span>{html.escape(str(detail))}</span></div>', unsafe_allow_html=True)


def stat_card(label, value_html):
    return (f'<div class="sc-stat"><div class="sc-label">{label}</div>'
            f'<div class="sc-value">{value_html}</div></div>')


def fmt_hour(h):
    return f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}"


def style_chart(chart):
    """Apply the SunCast look to an Altair chart (card colour, mono axes, sage grid)."""
    return (chart.configure(background=CARD, font=MONO)
            .configure_view(strokeWidth=0)
            .configure_axis(labelFont=MONO, titleFont=MONO, labelColor=INK_SOFT, titleColor=INK_SOFT,
                            gridColor=SAGE, domainColor=INK, tickColor=INK)
            .configure_legend(labelFont=MONO, labelColor=INK, symbolType="square"))


# ---------------- chat helpers (run as button callbacks) ----------------

QUICK_QUESTIONS = ["Is a battery worth it?", "How does net metering work?", "Which inverter should I get?"]


def ask(question):
    msgs = st.session_state.setdefault("messages", [])
    msgs.append({"role": "user", "content": question})
    reply, err = get_chat_reply(question, st.session_state.get("city", "Lahore"))
    msgs.append({"role": "assistant", "content": reply if not err else err})


def submit_chat():
    q = st.session_state.get("chat_text", "").strip()
    if q:
        ask(q)
    st.session_state["chat_text"] = ""


def render_chat():
    """User bubbles on the right (clay), assistant bubbles on the left with the sun avatar."""
    for i, m in enumerate(st.session_state["messages"]):
        if m["role"] == "user":
            _, right = st.columns([0.25, 0.75])
            with right:
                with st.container(key=f"user_msg_{i}"):
                    st.write(m["content"])
        else:
            avatar, body = st.columns([0.07, 0.93])
            avatar.markdown(sun_svg(32), unsafe_allow_html=True)
            with body:
                with st.container(key=f"bot_msg_{i}"):
                    st.markdown(m["content"])


# ---------------- input card ----------------

if MOCK:
    st.markdown('<div class="sc-mock">Mock mode: showing fake data. Set BACKEND_URL in Streamlit secrets '
                'to use the live backend.</div>', unsafe_allow_html=True)

with st.container(key="card_roof"):
    st.markdown('<span class="sc-step">Your roof</span><span class="sc-tag">Step 1</span>',
                unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
    with c1:
        city = st.selectbox("City", CITIES, key="city")
        st.markdown('<div class="sc-hint">5 cities for now</div>', unsafe_allow_html=True)
    with c2:
        system_kw = st.number_input("System size (kW)", min_value=0.5, max_value=1000.0, value=5.0, step=0.5)
        st.markdown('<div class="sc-hint">most homes: 3 to 10 kW</div>', unsafe_allow_html=True)
    with c3:
        tariff = st.number_input("Tariff (Rs per unit)", min_value=1.0, max_value=500.0, value=60.0, step=1.0)
        st.markdown('<div class="sc-hint">check your latest bill</div>', unsafe_allow_html=True)
    with c4:
        days = st.slider("Days to forecast", min_value=1, max_value=7, value=3)
        st.markdown('<div class="sc-ticks"><span>1</span><span>4</span><span>7</span></div>',
                    unsafe_allow_html=True)
    b1, b2 = st.columns([1, 3])
    go = b1.button("Get my forecast →", type="primary")
    b2.markdown('<div class="sc-hint" style="margin-top:0.7rem">takes about 2 seconds</div>',
                unsafe_allow_html=True)

if go:
    with st.spinner(f"Checking the sky over {city}..."):
        data, err = get_forecast(city, system_kw, tariff, days)
    if err:
        st.session_state.pop("result", None)
        st.session_state["error"] = err
    else:
        st.session_state["error"] = None
        st.session_state["result"] = data
        st.session_state["inputs"] = {"city": city, "kw": system_kw, "tariff": tariff, "days": days}


# ---------------- tabs ----------------

st.markdown('<div id="sc-tabs" style="height:1.2rem"></div>', unsafe_allow_html=True)
tab_forecast, tab_shops, tab_chat = st.tabs(["Forecast", "Solar shops", "Ask SunCast"])

with tab_forecast:
    if st.session_state.get("error"):
        error_card(st.session_state["error"])

    result = st.session_state.get("result")
    if result is None:
        if not st.session_state.get("error"):
            st.markdown(f'<div class="sc-empty">{EMPTY_SVG}<p>Pick your city and press Get my forecast</p></div>',
                        unsafe_allow_html=True)
    else:
        inp = st.session_state["inputs"]
        st.markdown(
            f'<div class="sc-h2">{html.escape(result["city"])} · {inp["kw"]:g} kW · next {inp["days"]} days</div>',
            unsafe_allow_html=True)

        daily = pd.DataFrame(result["daily"])
        daily["dt"] = pd.to_datetime(daily["date"])
        best = daily.loc[daily["kwh"].idxmax()]

        cards = (
            stat_card("Total energy", f'{result["total_kwh"]:,.1f} <span class="sc-unit">kWh</span>')
            + stat_card("Estimated savings", f'<span class="sc-unit">Rs</span> {result["total_savings_pkr"]:,}')
            + stat_card("Best day", f'{best["dt"]:%a} {best["dt"].day} <span class="sc-unit">{best["kwh"]:.1f} kWh</span>')
        )
        st.markdown(f'<div class="sc-stats">{cards}</div>', unsafe_allow_html=True)

        hourly = pd.DataFrame(result["hourly"])
        hourly["time"] = pd.to_datetime(hourly["time"])

        # appliance callout: the 3 consecutive hours with the highest total kW on the first day
        first_day = hourly["time"].dt.date.min()
        d0 = hourly[hourly["time"].dt.date == first_day].reset_index(drop=True)
        roll = d0["kw"].rolling(3).sum()
        if roll.notna().any() and d0["kw"].max() > 0:
            end_idx = int(roll.idxmax())
            start_h = int(d0.loc[end_idx - 2, "time"].hour)
            day_word = "today" if first_day == date.today() else f"{first_day:%A}"
            st.markdown(
                f'<div class="sc-banner">{WASHER_SVG}<div>'
                f'<b>Best time for heavy appliances: {day_word} {fmt_hour(start_h)} to {fmt_hour(start_h + 3)}</b>'
                f'<span>That\'s when your panels peak. Run the washing machine or water pump then.</span>'
                f'</div></div>', unsafe_allow_html=True)

        names = ["SunCast forecast", "Physics baseline"]
        left, right = st.columns(2)

        with left:
            with st.container(key="card_chart_energy"):
                st.markdown('<div class="sc-card-title">Energy per day</div>', unsafe_allow_html=True)
                labels = [f"{d:%a} {d.day}" for d in daily["dt"]]
                bar_df = pd.DataFrame({
                    "Day": labels + labels,
                    "Series": [names[0]] * len(labels) + [names[1]] * len(labels),
                    "kWh": list(daily["kwh"]) + list(daily["baseline_kwh"]),
                })
                bars = (
                    alt.Chart(bar_df)
                    .mark_bar(stroke=INK, strokeWidth=2)
                    .encode(
                        x=alt.X("Day:N", sort=labels, title=None, axis=alt.Axis(labelAngle=0)),
                        xOffset=alt.XOffset("Series:N", sort=names),   # side by side, not stacked
                        y=alt.Y("kWh:Q", title="kWh"),
                        color=alt.Color("Series:N",
                                        scale=alt.Scale(domain=names, range=[TERRACOTTA, OLIVE]),
                                        legend=alt.Legend(orient="top", title=None, symbolType="square")),
                        tooltip=["Day:N", "Series:N", alt.Tooltip("kWh:Q", format=".1f")],
                    )
                    .properties(height=260)
                )
                st.altair_chart(style_chart(bars), theme=None, width="stretch")

        with right:
            with st.container(key="card_chart_hour"):
                st.markdown('<div class="sc-card-title">Hour by hour</div>', unsafe_allow_html=True)
                col_names = {"kw": names[0], "baseline_kw": names[1]}
                cols = [c for c in col_names if c in hourly.columns]
                long = hourly.melt(id_vars="time", value_vars=cols, var_name="series", value_name="kW")
                long["series"] = long["series"].map(col_names)
                domain = [col_names[c] for c in cols]
                line = (
                    alt.Chart(long)
                    .mark_line(strokeWidth=3)
                    .encode(
                        x=alt.X("time:T", title=None, axis=alt.Axis(format="%a %d", tickCount="day")),
                        y=alt.Y("kW:Q", title="kW"),
                        color=alt.Color("series:N",
                                        scale=alt.Scale(domain=domain, range=[TERRACOTTA, OLIVE][:len(cols)]),
                                        legend=alt.Legend(orient="top", title=None)),
                        strokeDash=alt.StrokeDash("series:N",
                                                  scale=alt.Scale(domain=domain, range=[[1, 0], [6, 4]][:len(cols)]),
                                                  legend=None),
                        tooltip=[alt.Tooltip("time:T", format="%a %d %b, %H:%M"), "series:N",
                                 alt.Tooltip("kW:Q", format=".2f")],
                    )
                    .properties(height=260)
                )
                st.altair_chart(style_chart(line), theme=None, width="stretch")

        with st.expander("Daily numbers"):
            rows_html = "".join(
                f'<tr><td>{r["date"]}</td><td>{r["kwh"]:,.2f}</td>'
                f'<td>{r["savings_pkr"]:,}</td><td>{r["baseline_kwh"]:,.2f}</td></tr>'
                for r in result["daily"])
            st.markdown(
                '<table class="sc-table"><tr><th>Date</th><th>Energy (kWh)</th><th>Savings (Rs)</th>'
                f'<th>Baseline (kWh)</th></tr>{rows_html}</table>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="sc-note">Uses forecast weather, an estimated panel temperature and an assumed '
            f'0.86 loss factor. Model in use: {html.escape(str(result.get("model", "unknown")))}.</div>',
            unsafe_allow_html=True)

with tab_shops:
    st.markdown(f'<div class="sc-h2">Solar shops in {html.escape(city)}</div>', unsafe_allow_html=True)
    rows, err = get_retailers(city, MOCK, BACKEND_URL)
    if err:
        error_card(err)
    elif not rows:
        st.markdown('<div class="sc-note">No retailers listed for this city yet.</div>', unsafe_allow_html=True)
    else:
        df = pd.DataFrame(rows)
        # the backend returns all retailers, so keep only this city's rows
        if not MOCK and "area" in df.columns:
            df = df[df["area"].astype(str).str.contains(city, case=False, na=False)]
        if df.empty:
            st.markdown('<div class="sc-note">No retailers listed for this city yet.</div>', unsafe_allow_html=True)
        else:
            shop_cards = []
            for r in df.to_dict("records"):
                name = html.escape(str(r.get("name", "")))
                area = html.escape(str(r.get("area", "")))
                contact = html.escape(str(r.get("contact", "")))
                rating = html.escape(str(r.get("rating", "")))
                tel = "".join(ch for ch in str(r.get("contact", "")) if ch.isdigit() or ch == "+")
                shop_cards.append(
                    f'<div class="sc-shop"><div class="sc-shop-name">{name}</div>'
                    f'<div class="sc-shop-area">{area}</div>'
                    f'<div class="sc-shop-row"><span class="sc-tag">{rating} / 5</span>'
                    f'<a class="sc-call" href="tel:{tel}">Call {contact}</a></div></div>')
            st.markdown('<div class="sc-shops">' + "".join(shop_cards) + "</div>", unsafe_allow_html=True)

with tab_chat:
    st.markdown('<div class="sc-h2">Ask SunCast</div>', unsafe_allow_html=True)
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    with st.container(key="card_chat"):
        qcols = st.columns(3)
        for i, q in enumerate(QUICK_QUESTIONS):
            qcols[i].button(q, key=f"quick_{i}", on_click=ask, args=(q,), width="stretch")

        render_chat()

        with st.form("chat_form", border=False):
            st.text_input("Your question", placeholder="Ask anything about going solar",
                          max_chars=1000, key="chat_text", label_visibility="collapsed")
            st.form_submit_button("Send", type="primary", on_click=submit_chat)

st.markdown('<div class="sc-foot">SunCast · AI course project · forecasts are estimates, not financial advice</div>',
            unsafe_allow_html=True)