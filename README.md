# Football Gravity Pipeline \u26bd\ufe0f\ud83d\udd12

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Security Posture](https://img.shields.io/badge/Security-Zero%20Trust-green)
![LangGraph Orchestration](https://img.shields.io/badge/Orchestrator-LangGraph-purple)
![License](https://img.shields.io/badge/License-MIT-gray)

> **The most secure, autonomous, production-grade multi-agent system for daily football match data ingestion, enrichment, and storage in 2026.**

## Overview
Unlike typical football ETL pipelines that act deterministically linearly (e.g., `football-etl-pipeline` or `SoccerAgent`), **Football Gravity** is an advanced Multi-Agent System orchestrated by LangGraph. It is inherently self-healing, handles network drops via exponential backoff, enforces strict **Zero-Trust data boundaries** via exhaustive Pydantic schemas, calculates state-of-the-art **Logistic Regression xG**, and outputs **100% encrypted analysis** at rest using DuckDB + Fernet.

## Features
- **\ud83e\udd16 Agentic Orchestration**: Supervisor, Fetcher, Enricher, Loader, and Validator operating cooperatively.
- **\ud83d\udd12 Defense-in-Depth**: Strict TLS enforcement, pure-JSON append-only audit logging, and `extra="forbid"` Pydantic validation guarantees no rogue keys slip into memory.
- **\ud83d\udcca Production xG Engine**: Scikit-Learn Logistic Regression initialized via real pitch geometric probability models, replacing naive rule-engines.
- **\ud83d\udd04 Self-Healing & Anomaly Detection**: If an output anomalies out (e.g., 0 goals vs 8.8 total xG), the Validator isolates it and routes the LangGraph state back to recovery rather than failing the run.

## Zero-Trust Architecture
```mermaid
graph TD
    subgraph "External World"
        SB[StatsBomb API / GitHub]
    end

    subgraph "Zero-Trust Orchestration (LangGraph)"
        O[Supervisor Agent]
        F[Fetcher Agent]
        E[Enricher Agent]
        L[Loader Agent]
        V[Validator Agent]
        
        O -->|Queue World Cup Matches| F
        F -->|Raw JSON via TLS| E
        E -->|scikit-learn xG and Pydantic| L
        L -->|Encrypted DuckDB Upsert| V
        V -->|Anomaly Detection| O
    end

    subgraph "Secure Storage & UX"
        DB[(DuckDB)]
        Parquet[(Encrypted Parquet.enc)]
        ST[Streamlit Dashboard]
        
        L -.-> DB
        DB -.->|Fernet Export| Parquet
        Parquet -->|In-Memory Decrypt| ST
    end

    SB <-->|HTTPS / Tenacity Backoff| F
```

## Quick Start & Demo Run

### 1. Secure Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate your secure key (Never commit this!)
python -c "from cryptography.fernet import Fernet; print('FERNET_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" > .env
```

### 2. Run the LangGraph Pipeline
This will fetch real 2022 World Cup matches, calculate the advanced analytics, validate statistics, and output the encrypted payloads to `data/db/`.
```bash
python main.py --date today
```

### 3. Interactive Visualization Dashboard
We employ a zero-trust presentation layer. The Streamlit dashboard relies on the environment variable to decrypt the parquet files **in-memory**, displaying Plotly shot-maps vividly.
```bash
streamlit run streamlit_app.py
```

## Running the Security & Unit Tests
```bash
pytest tests/ -v
```

## Next Enhancements
- **Tracking Data ML Expansion**: Incorporating broadcast optical tracking natively.
- **FastAPI Real-Time Webhooks**: Triggering pipeline execution from match-finish events dynamically instead of batch execution.
- **Celery / Redis Distributed Scrape**: Parallel processing across Top 5 European leagues simultaneously.

---
*Built for absolute precision, security, and elegance.*
