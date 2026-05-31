# POC--14-PaymentOutage-Ganga

# Payment Processor Outage Monitor

A full-stack fintech intelligence dashboard built with Next.js, FastAPI, Pandas, and DuckDB for monitoring payment processor outages, failover routing, market concentration risk, and downstream merchant impact.

The platform transforms raw processor health metrics into actionable operational intelligence through real-time visualizations, incident diagnostics, and financial impact estimation.

---

## Features

### Core Status Board
- Live processor status monitoring
- Uptime and success-rate tracking
- Risk-tier classification
- Fleet-average comparison
- Incident severity scoring

### Global Processor Geo-Distribution
- Interactive world map visualization
- Real processor coordinates
- Market-share-based node sizing
- Status-based color coding
- Regional payment rail visibility

### Incident Diagnosis Timeline
- Step-by-step outage replay
- Timestamped audit trail
- Incident severity tracking
- Postmortem CSV export

### Merchant Impact Estimator
- Interactive financial risk modeling
- Revenue-at-risk calculations
- Transaction-loss estimation
- Recovery scenario simulation

### Failover Traffic Router
- Traffic rerouting visualization
- Standby gateway monitoring
- Failover state tracking
- Routing distribution analysis

### Market Concentration Analysis
- Processor market share comparison
- Gateway profile inspection
- Payment rail dependency insights

### Resilient Architecture
- Mock-data fallback support
- API outage protection
- Cached data recovery
- No blank-state rendering

---

## Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Recharts
- react-simple-maps
- lucide-react

### Backend

- FastAPI
- Pandas
- DuckDB
- Pydantic
- Uvicorn
- python-dotenv

---

## Architecture

```text
Next.js Frontend
       │
       ▼
FastAPI Backend
       │
       ▼
Pandas Intelligence Layer
       │
       ▼
DuckDB Analytics Engine
       │
       ▼
Enriched Processor Intelligence
