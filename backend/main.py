import json
import os
from datetime import datetime, timezone
from typing import List

import duckdb
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Payment Resilience Metrics Server")

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
MOCK_DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    os.getenv("MOCK_DATA_PATH", "mock_data.json")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    time: str
    label: str
    description: str
    completed: bool


class Incident(BaseModel):
    id: str
    processorId: str
    processorName: str
    status: str
    errorTitle: str
    errorDetail: str
    startTime: str
    impactEstimate: str
    timeline: List[TimelineEvent]


class ProcessorGeo(BaseModel):
    type: str
    coordinates: List[float]


class Processor(BaseModel):
    id: str
    name: str
    status: str
    uptime: float
    incidentsCount: int
    successRate: float
    marketShare: int
    region: str
    primaryRail: str
    details: str
    logo: str
    uptime_vs_avg: float
    success_rate_vs_avg: float
    risk_tier: str
    incident_severity_score: float
    geo: ProcessorGeo


class GeoFeatureProperties(BaseModel):
    id: str
    name: str
    status: str
    risk_tier: str
    marketShare: int


class GeoFeature(BaseModel):
    type: str
    geometry: ProcessorGeo
    properties: GeoFeatureProperties


class GeoFeatureCollection(BaseModel):
    type: str
    features: List[GeoFeature]


class ResilienceMetrics(BaseModel):
    processors: List[Processor]
    incidents: List[Incident]
    last_updated: str
    fleet_avg_uptime: float
    fleet_avg_success_rate: float


class RiskSummaryItem(BaseModel):
    id: str
    name: str
    severity_score: float
    risk_tier: str


class RiskSummaryResponse(BaseModel):
    at_risk: List[RiskSummaryItem]
    queried_at: str


# ── Constants ────────────────────────────────────────────────────────────────

REGION_COORDINATES = {
    "stripe":    [-122.4194, 37.7749],
    "adyen":     [4.9041,   52.3676],
    "paypal":    [-121.9886, 37.3382],
    "chase":     [-74.0060,  40.7128],
    "fiserv":    [-88.0040,  43.0389],
    "braintree": [-87.6298,  41.8781],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def compute_risk_tier(success_rate: float) -> str:
    if success_rate >= 99.5:
        return "low"
    elif success_rate >= 97.0:
        return "medium"
    return "high"


def compute_severity_score(
    incident_count: int,
    success_rate: float,
    status: str
) -> float:
    status_weight = {"incident": 1.0, "degraded": 0.5, "operational": 0.0}
    base = (
        (100 - success_rate) * 0.6
        + incident_count * 0.3
        + status_weight.get(status, 0) * 10
    )
    return round(base, 2)


def load_and_enrich() -> dict:
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["processors"])

    fleet_avg_uptime        = round(float(df["uptime"].mean()), 4)
    fleet_avg_success_rate  = round(float(df["successRate"].mean()), 4)

    df["uptime_vs_avg"]         = (df["uptime"] - fleet_avg_uptime).round(4)
    df["success_rate_vs_avg"]   = (df["successRate"] - fleet_avg_success_rate).round(4)
    df["risk_tier"]             = df["successRate"].apply(compute_risk_tier)
    df["incident_severity_score"] = df.apply(
        lambda row: compute_severity_score(
            row["incidentsCount"], row["successRate"], row["status"]
        ),
        axis=1,
    )

    df = df.sort_values("incident_severity_score", ascending=False).reset_index(drop=True)

    processors = []
    for _, row in df.iterrows():
        coords = REGION_COORDINATES.get(row["id"], [0.0, 0.0])
        processors.append({
            **row.to_dict(),
            "geo": {"type": "Point", "coordinates": coords},
        })

    return {
        "processors":             processors,
        "incidents":              raw["incidents"],
        "last_updated":           datetime.now(timezone.utc).isoformat(),
        "fleet_avg_uptime":       fleet_avg_uptime,
        "fleet_avg_success_rate": fleet_avg_success_rate,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/resilience-metrics", response_model=ResilienceMetrics)
def get_metrics():
    """Enriched processor status, incidents, and fleet averages."""
    return load_and_enrich()


@app.get("/api/processor-geo", response_model=GeoFeatureCollection)
def get_processor_geo():
    """GeoJSON FeatureCollection for Mapbox / Deck.gl map layers."""
    data = load_and_enrich()
    features = [
        {
            "type": "Feature",
            "geometry": p["geo"],
            "properties": {
                "id":          p["id"],
                "name":        p["name"],
                "status":      p["status"],
                "risk_tier":   p["risk_tier"],
                "marketShare": p["marketShare"],
            },
        }
        for p in data["processors"]
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/risk-summary", response_model=RiskSummaryResponse)
def get_risk_summary():
    """
    DuckDB-powered risk query.
    Returns all non-low-risk processors ranked by computed severity score.
    """
    data = load_and_enrich()

    rows = [
        (p["id"], p["name"], p["incident_severity_score"], p["risk_tier"])
        for p in data["processors"]
    ]

    values_sql = ", ".join(
        f"('{r[0]}', '{r[1]}', {r[2]}, '{r[3]}')" for r in rows
    )

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE proc AS
        SELECT * FROM (VALUES {values_sql})
        t(id, name, severity, risk_tier)
    """)
    result = con.execute("""
        SELECT id, name, severity, risk_tier
        FROM proc
        WHERE risk_tier != 'low'
        ORDER BY severity DESC
    """).fetchall()
    con.close()

    return {
        "at_risk": [
            {
                "id":             r[0],
                "name":           r[1],
                "severity_score": r[2],
                "risk_tier":      r[3],
            }
            for r in result
        ],
        "queried_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)