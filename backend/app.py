"""
app.py

SunCast backend (FastAPI). Hosted on Render.

Endpoints:
    GET  /health                 check that the server is awake
    POST /predict                solar forecast and savings for a city
    GET  /retailers?city=Lahore  solar retailers in a city
    POST /chat                   solar chatbot (Member 2 plugs in chatbot.py)

Run locally from the backend folder:
    uvicorn app:app --reload
Then open http://127.0.0.1:8000/docs to try every endpoint in the browser.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from physics import physics_kw
from weather import CITIES, get_forecast

# Member 2's ML predictor. Until predictor.py exists, the backend uses the
# physics formula, so the app always returns a real forecast.
try:
    from predictor import predict_hourly
    MODEL_USED = "ml"
except ImportError:
    predict_hourly = None
    MODEL_USED = "physics"

# Member 2's chatbot. Until chatbot.py exists, /chat returns a placeholder.
try:
    from chatbot import answer
except ImportError:
    answer = None

HERE = Path(__file__).resolve().parent

app = FastAPI(title="SunCast API", version="1.0")

# Let the Streamlit frontend (a different website) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- request shapes (these match the API contract in the plan) ----------

class PredictRequest(BaseModel):
    city: str
    system_kw: float = Field(gt=0, le=1000, description="Size of the solar system in kW")
    tariff_pkr: float = Field(gt=0, le=500, description="Electricity price in Rs per unit (kWh)")
    days: int = Field(default=3, ge=1, le=7, description="How many days to forecast")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    city: Optional[str] = None


# ---------- helpers ----------

def load_retailers():
    """Read retailers.csv from backend/data/ (on Render) or ../data/ (locally)."""
    for path in [HERE / "data" / "retailers.csv", HERE.parent / "data" / "retailers.csv"]:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def check_city(city):
    """Return the city name in its proper form, or stop with a clear error."""
    for name in CITIES:
        if name.lower() == city.strip().lower():
            return name
    raise HTTPException(status_code=400, detail=f"City must be one of {list(CITIES)}")


# ---------- endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_USED, "cities": list(CITIES)}


@app.post("/predict")
def predict(req: PredictRequest):
    city = check_city(req.city)

    try:
        weather = get_forecast(city, req.days)
    except Exception:
        raise HTTPException(status_code=503, detail="Weather forecast is unavailable right now, please try again.")

    # Comparison line from the physics formula
    weather["baseline_kw"] = physics_kw(weather["radiation"], weather["temp_c"], req.system_kw)

    # Main forecast: ML model if available, otherwise the physics formula
    if predict_hourly is not None:
        weather["kw"] = predict_hourly(weather, req.system_kw)
    else:
        weather["kw"] = weather["baseline_kw"]

    # Hourly values are averages over one hour, so kW summed over hours = kWh
    weather["date"] = weather["time"].dt.strftime("%Y-%m-%d")
    per_day = weather.groupby("date")[["kw", "baseline_kw"]].sum()

    daily = [
        {
            "date": date,
            "kwh": round(row.kw, 2),
            "savings_pkr": round(row.kw * req.tariff_pkr),
            "baseline_kwh": round(row.baseline_kw, 2),
        }
        for date, row in per_day.iterrows()
    ]
    hourly = [
        {"time": t.strftime("%Y-%m-%dT%H:%M"), "kw": round(kw, 3), "baseline_kw": round(b, 3)}
        for t, kw, b in zip(weather["time"], weather["kw"], weather["baseline_kw"])
    ]
    total_kwh = float(weather["kw"].sum())

    return {
        "city": city,
        "model": MODEL_USED,
        "daily": daily,
        "hourly": hourly,
        "total_kwh": round(total_kwh, 2),
        "total_savings_pkr": round(total_kwh * req.tariff_pkr),
    }


@app.get("/retailers")
def retailers(city: str = Query(..., description="One of the 5 SunCast cities")):
    city = check_city(city)
    df = load_retailers()
    if df.empty:
        return []

    # Find the city column whatever its exact name is (city, City, ...)
    city_col = next((c for c in df.columns if c.lower() == "city"), None)
    if city_col is not None:
        df = df[df[city_col].str.strip().str.lower() == city.lower()]
    return df.fillna("").to_dict(orient="records")


@app.post("/chat")
def chat(req: ChatRequest):
    if answer is None:
        return {"reply": "The SunCast assistant is being set up. Please try again soon."}
    return {"reply": answer(req.message, req.city)}
