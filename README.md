## Team ID: 1113 - Serendipity 

# HC01 - Agentic Diagnostic Risk Assistance for ICU Complication Detection

ICU environments are overwhelming. ICU data is hard to keep up with. It is complex, unstructured and time-sensitive.
We designed a system using Agentic Architecture where multiple specialized AI agents handle different parts of ICU data processing in parallel.

---

<img width="571" height="670" alt="image" src="https://github.com/user-attachments/assets/5c939aaa-0f33-4c1c-a61e-41ffa05957bc" />


---

## Features

### Multi-Agent Pipeline with Separated Roles
Four specialized AI agents each handle a distinct part of the clinical reasoning process and hand off structured outputs to the next stage — no single model does everything.

- **Note Parser Agent** — Ingests unstructured clinical notes (nursing, physician, shift handovers) and extracts structured symptoms from keywords and timelines: 
  symptom name, severity, category (vital sign/lab result / mental status / fluid output), value, unit, and trend direction (worsening/improving/stable).
  Outputs a timestamped JSON timeline per patient.

- **Temporal Lab Mapper Agent** — Reads LABEVENTS.csv (MIMIC-III dataset format) and tracks six SOFA-relevant lab markers — Creatinine, Lactate, WBC, Bilirubin,   Platelets, Hemoglobin — chronologically across sessions. Computes a weighted disease severity score per round, classifies trend direction, and defines disease progression between real-time data and historical data points.

- **GUuideline Retrieval RAG Agent** — Embeds patient context and queries a ChromaDB vector store populated with curated medical guidelines. Retrieves the most semantically relevant guideline passages and surfaces them as cited evidence in the final report.

- **Chief Synthesis Agent** — Aggregates outputs from all three agents, runs final LLM reasoning, and generates the Diagnostic Risk Report. Includes built-in outlier detection logic: if a lab result is statistically anomalous relative to the prior trend (e.g., WBC drops from 18.7 to 1.8 K/uL in a single draw), the agent flags it as a probable lab error and withholds diagnosis update until a confirmed redraw for reevaluation is received.

---

### Disease Progression Timeline
A chronological disease score is computed each simulation round using a weighted formula across six SOFA lab markers. The timeline merges:
- Historical baseline from prior MIMIC-III admissions (loaded once at start)
- Real-time scores from the current simulation session
- Previous simulation session scores described as historical data points 

Trend classification: **worsening** / **improving** / **stable**, computed 
from the delta between consecutive scores. Stage classification:
- Score ≥ 70 → Sepsis with Septic Shock and Acute Kidney Injury  
- Score ≥ 50 → Moderate Sepsis — Organ Dysfunction Developing  
- Score ≥ 30 → Early Sepsis — Monitoring Required  
- Score < 30 → Stable — Low Risk

---

### Real-Time Lab Simulation (MIMIC-III Format)
A simulation engine generates realistic lab values for six markers every 30 seconds per round, appending rows directly to LABEVENTS.csv in the MIMIC-III schema. Each marker has a configurable drift rate, directional bias, and min/max clamp. A 5% random spike probability fires on any round to demonstrate the outlier detection module — the spike is logged but does not update the running state baseline.

---

### Outlier Detection Module
The Chief Agent applies statistical anomaly detection before updating any diagnosis. If a lab value deviates beyond expected bounds relative to its prior session baseline, it is:
1. Logged separately as a probable lab error
2. Excluded from the risk score computation
3. Surfaced in the report as an excluded outlier requiring redraw confirmation

This prevents a single erroneous reading from triggering a false diagnosis escalation.

---

### Diagnostic Risk Report with Safety Caveats
The final output is a structured report containing:
- Patient overview and admission metadata
- Current risk stage and confidence
- Key findings with severity classification
- Supporting lab evidence with reference ranges
- Retrieved guideline justification with source citations
- Suggested clinical actions with priority tagging
- Explicit safety disclaimer: all outputs are decision-support only, 
  not a clinical diagnosis

---

### Multi-Session Persistence
Simulation sessions are logged with a session ID (timestamp-based). On restart, the engine resumes from the last real-time timeline checkpoint and loads all prior session scores as historic insights. The frontend receives a unified progression payload including historical MIMIC admissions, prior session summaries, and live real-time readings.

---

## Tech Stack

### AI & Agent Orchestration
| Tool | Role |
|---|---|
| `openai` + `langchain-openai` | LLM backbone for all four agents (GPT-4 via OpenAI API) |
| `langchain-core` | Agent orchestration, prompt chaining, output parsing |
| `sentence-transformers` | Local embedding model for RAG query encoding |
| `chromadb` | Vector store for medical guideline retrieval (RAG pipeline) |
| `pdfplumber` | PDF ingestion for loading clinical guideline documents into the vector store |

### Backend
| Tool | Role |
|---|---|
| `FastAPI` | REST API server — exposes `/analyze` endpoint that triggers the full agent pipeline |
| `uvicorn` | ASGI server running the FastAPI app |
| `pymongo` | MongoDB driver — persists generated Diagnostic Risk Reports |
| `pandas` + `numpy` | Lab data loading, MIMIC-III CSV processing, severity score computation |
| `python-dotenv` | Environment variable management (API keys, DB URIs) |
| `pytest` | Test suite |

### Data
| Source | Role |
|---|---|
| MIMIC-III demo dataset | Real patient lab event data (`LABEVENTS.csv`, `PATIENT_HISTORY.csv`) |
| `simulate_icu.py` | Custom real-time simulation engine — generates realistic drifting lab values in MIMIC-III schema, appends to CSV every 30s |

### Frontend
| Tool | Role |
|---|---|
| `Next.js` (TypeScript) | React-based frontend — patient list, analysis dashboard, report view |
| `CSS` | Component styling |
| Vercel / AWS S3 / CloudFront | Deployment targets for frontend static assets |

### Infrastructure
| Tool | Role |
|---|---|
| Docker | Containerization of backend services |
| Kubernetes | Cluster orchestration and horizontal scaling |
| AWS / GCP | Cloud deployment targets |
| MongoDB | Report storage and retrieval |



