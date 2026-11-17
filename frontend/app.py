"""
SunCast frontend (Streamlit). Member 3.
Talks to the FastAPI backend. If BACKEND_URL is not set in
Streamlit secrets, it runs in MOCK mode with fake data.
"""

import math
import random
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

CITIES = ["Lahore", "Karachi", "Islamabad", "Peshawar", "Multan"]

st.set_page_config(page_title="SunCast", page_icon="☀️", layout="wide")


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


# ---------------- backend calls ----------------

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


# ---------------- sidebar ----------------

st.title("☀️ SunCast")
st.caption("Rooftop solar forecast and savings for Pakistani cities")

if MOCK:
    st.warning("Mock mode: showing fake data. Set BACKEND_URL in Streamlit secrets to use the live backend.")

with st.sidebar:
    st.header("Your solar system")
    city = st.selectbox("City", CITIES)
    system_kw = st.number_input("System size (kW)", min_value=0.5, max_value=1000.0, value=5.0, step=0.5)
    tariff = st.number_input("Tariff (Rs per unit)", min_value=1.0, max_value=500.0, value=60.0, step=1.0)
    days = st.slider("Days to forecast", min_value=1, max_value=7, value=3)
    go = st.button("Get forecast", type="primary", use_container_width=True)

if go:
    with st.spinner("Getting your forecast... (if the backend was asleep this can take about a minute)"):
        data, err = get_forecast(city, system_kw, tariff, days)
    if err:
        st.session_state.pop("result", None)
        st.session_state["error"] = err
    else:
        st.session_state["error"] = None
        st.session_state["result"] = data
        st.session_state["inputs"] = {"city": city, "kw": system_kw, "tariff": tariff, "days": days}


# ---------------- tabs ----------------

tab_forecast, tab_retailers, tab_chat = st.tabs(["Forecast", "Retailers", "Chat"])

with tab_forecast:
    if st.session_state.get("error"):
        st.error(st.session_state["error"])

    result = st.session_state.get("result")
    if result is None:
        if not st.session_state.get("error"):
            st.info("Pick your city and system size in the sidebar, then press **Get forecast**.")
    else:
        inp = st.session_state["inputs"]
        st.subheader(f"{result['city']}: {inp['kw']:g} kW system, {inp['days']} day(s)")

        c1, c2 = st.columns(2)
        c1.metric("Total energy", f"{result['total_kwh']:,.1f} kWh")
        c2.metric("Total savings", f"Rs {result['total_savings_pkr']:,}")

        daily = pd.DataFrame(result["daily"]).set_index("date")
        st.markdown("**Daily energy (kWh)**")
        st.bar_chart(
            daily[["kwh", "baseline_kwh"]].rename(
                columns={"kwh": "SunCast forecast", "baseline_kwh": "Physics baseline"}),
            color=["#F97316", "#94A3B8"],
            stack=False,
        )

        hourly = pd.DataFrame(result["hourly"])
        hourly["time"] = pd.to_datetime(hourly["time"])
        hourly = hourly.set_index("time")
        st.markdown("**Hourly power (kW)**")
        cols = ["kw"] + (["baseline_kw"] if "baseline_kw" in hourly.columns else [])
        st.line_chart(
            hourly[cols].rename(
                columns={"kw": "SunCast forecast", "baseline_kw": "Physics baseline"}),
            color=["#F97316", "#94A3B8"][:len(cols)],
        )

        with st.expander("Daily table"):
            table = daily.rename(columns={
                "kwh": "kWh", "savings_pkr": "Savings (Rs)", "baseline_kwh": "Baseline kWh"})
            st.dataframe(table, use_container_width=True)

        st.caption("Forecast uses weather predictions, an estimated panel temperature and an assumed 0.86 loss factor.")

with tab_retailers:
    st.subheader(f"Solar retailers in {city}")
    rows, err = get_retailers(city, MOCK, BACKEND_URL)
    if err:
        st.error(err)
    elif not rows:
        st.info("No retailers listed for this city yet.")
    else:
        df = pd.DataFrame(rows)
        df = df.drop(columns=[c for c in df.columns if c.lower() == "city"])
        # the backend returns all retailers, so keep only this city's rows
        if not MOCK and "area" in df.columns:
            df = df[df["area"].astype(str).str.contains(city, case=False, na=False)]
        if df.empty:
            st.info("No retailers listed for this city yet.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)