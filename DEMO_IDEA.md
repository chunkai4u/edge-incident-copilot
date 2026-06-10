# Demo Idea: Alarm Storm → One-Click Incident Summary
## Offline Incident Copilot for Critical-Infrastructure Operators — Live Demo for TUM Venture Labs Demo Day (Friday)

> Owner: Chun-Kai · Complements Yamini's usecase1 work · Based on `EnergySector-Usecase1.md` (Prototype Architecture for Offline & Privacy-Critical Energy Environments)

---

## 1. The Story (30-second pitch)

A power plant control room receives **hundreds of alarms per hour**. During a single equipment failure, one root cause can cascade into 40+ alarms within seconds — operators suffer **alarm fatigue** and lose minutes finding the real problem.

**Our demo:** a live alarm storm floods a SCADA-style dashboard. The operator clicks **one button**. An **edge-hosted LLM running fully offline** compresses the alarm flood into a single incident card: a root-cause *hypothesis*, evidence timeline, cited SOPs/maintenance history, and a suggested action list — in seconds, with **zero data leaving the plant**. It is **advisory and human-in-the-loop**: it summarizes, cites, and ranks hypotheses; the operator decides and acts.

We don't pitch this as "alarm management" (a crowded category owned by DCS vendors). We pitch the **last-mile cognition layer** that sits on top of existing SCADA/DCS/historian data and turns a live cascade into a cited, operator-ready incident narrative — fully inside the plant perimeter.

---

## 1.5 Positioning & Market (demo-day framing)

**Reframe:** From *"edge LLM alarm correlation for control rooms"* → To **"offline incident copilot for EU critical-infrastructure operators, starting with alarm floods."**

**Category & wedge.** Alarm overload is a recognized, standardized problem (ISA-18.2 covers the full alarm lifecycle around reducing floods and operator overload). Incumbents own that lifecycle; we own a narrower, emotionally clear job: **turn the first 90 seconds of a plant upset into a trustworthy, cited incident card without sending OT data to the cloud.**

**Buyer:** EU energy and water operators with OT networks that *cannot* stream plant data to cloud AI — not "industrial companies" in general.

**Competitive landscape (public positioning):**

| Category | Players | What they own | Our angle |
|---|---|---|---|
| DCS-native alarm mgmt | Emerson DeltaV, ABB 800xA, Yokogawa | Filtering, suppression, historian/reporting, lifecycle | Don't replace — sit on top as a thin copilot layer |
| Vendor-agnostic alarm suites | Honeywell Forge/DynAMo, Hexagon/PAS, AVEVA ProcessVue | Cross-site alarm health, rationalization, KPI/compliance | Heavier lifecycle tools; we claim speed, usability, offline edge, explainable RAG |
| Industrial AI platforms | Cognite Atlas AI | NL access to industrial data, cause maps | Closest AI competitor — we go narrower: live alarm storms, operators, offline OT |
| Research | Alarm-flood RCA / LLM-agent papers | Validates the direction | Timing is right; keep demo grounded in UX, not novelty |

**Regulatory tailwind.** NIS2 pulls energy, water, and other critical sectors into incident-notification + risk-management duties; the EU AI Act (Annex III) treats AI safety components for critical infrastructure as high-risk — which is exactly why **advisory-first, human-in-the-loop, evidence-cited, on-prem/offline** is the safe and differentiated posture. We never imply the model controls the plant.

**Integration, not replacement.** "We don't replace Honeywell, Emerson, ABB, or Yokogawa. We read their alarms, historian tags, SOPs, and work orders."

**Claim discipline.** With public datasets we claim **compression, traceability, and workflow speed** — *not* root-cause accuracy. Accuracy claims wait for pilots. Use the demo metric as a demo metric: *"in this demo: 42 alarms → 1 incident in ~8 seconds."*

**YC-style pitch line:**

> We're building an **offline incident copilot** for **operators of critical energy and water facilities**. Today they rely on SCADA alarm lists, historian screens, SOP binders, and senior-operator judgment — which causes alarm floods, slow root-cause discovery, and weak handover documentation during upsets. Small local LLMs + retrieval over plant documents + stricter OT data-sovereignty rules now let them **turn raw alarms into evidence-cited incident decisions without sending plant data to the cloud**. One click during an alarm storm → one root-cause hypothesis, one causal timeline, cited SOP/work-order evidence, and an operator-ready action summary in seconds.

**One-liner:** *"We turn 40 industrial alarms into one cited incident card, fully offline, before the operator loses the first minute."*

---

## 2. Demo Scenario: Cooling Water Pump Failure → Turbine Trip

Synthetic but realistic cascade (Unit 3, combined-cycle plant):

| Time | Event | Tag |
|------|-------|-----|
| 14:02:13 | Cooling water pump CWP-2 motor overcurrent trip | ROOT CAUSE |
| 14:02:15 | Cooling water flow LOW | cascade |
| 14:02:40 | Lube oil temperature HIGH | cascade |
| 14:03:05 | Turbine bearing #2/#3 temp HIGH-HIGH | cascade |
| 14:03:30 | Shaft vibration HIGH | cascade |
| 14:03:48 | **Turbine protective trip ST-3** | consequence |
| 14:03:49+ | ~35 downstream alarms (gen breaker, steam pressure, condenser…) | noise |

Hidden clue in maintenance logs (RAG retrieves it): **WO-2026-0871** — CWP-2 abnormal vibration noted 3 weeks ago, maintenance deferred. This is the "wow" moment: the LLM connects live alarms with historical maintenance records.

---

## 2.5 Demo Data Strategy — grounded in open ICS benchmarks

We are pre-revenue with no customer data yet, so instead of inventing numbers the demo is built to run on **public industrial-control benchmark datasets**. The alarm schema and the conversion pipeline are real; for a paying customer we only swap the CSV + tag mapping + their SOP/maintenance docs. This is the honest answer to "where does the data come from?" on stage.

**Recommended open datasets**

| Priority | Dataset | Why it fits this demo | How we use it |
|---|---|---|---|
| 1 (primary) | **HAI** (HIL-based Augmented ICS, `github.com/icsdataset/hai`) | Realistic ICS testbed with boiler / turbine / water-treatment / HIL simulation; turbine loop uses a GE Mark VIe DCS — closest to our turbine-trip story. CSV, first column time, attack labels at the end. | Replace the synthetic alarm stream; turn turbine/boiler/CW SCADA-point deviations into alarms. |
| 2 (backup) | **Tennessee Eastman Process (TEP)** | Classic fault-diagnosis benchmark; normal/faulty multivariate time-series — perfect "many sensors abnormal → LLM names one root cause." Downside: chemical, not power. | Easiest to wire up fast: use fault number as root cause, threshold breaches as alarms. |
| 3 | UAH/MSU/ORNL Power System Datasets | Electric-transmission domain: normal/disturbance/control/cyber-attack, synchrophasor + relay logs. | If we pivot the story to grid rather than a single plant. |
| 4 | SWaT | 6-stage water-treatment testbed, 51 sensors/actuators, 41 attack scenarios. | Generic SCADA-anomaly demo (needs iTrust/Kaggle access). |
| 5 | BATADAL | Water-distribution cyber-attack challenge (sensors, pumps, network). | Pump/system anomaly correlation. |

**Pipeline (implemented in `dataset_to_alarms.py`)**

1. Read an anomaly time-window from the HAI/TEP CSV.
2. Per sensor tag, compute baseline + z-score / % change.
3. Threshold breach → emit alarm `[time, severity, tag, message]`.
4. Use the dataset's own attack/fault label as the **root cause**.
5. Add three synthetic RAG docs (SOP, work order, past incident).

Output is `alarms_dataset.js`; include it before the demo's main script and the dashboard auto-switches from the synthetic cascade to the dataset-derived stream (the **DATA** badge turns purple).

**Investor one-liner:** *"The live alarm stream comes from public ICS benchmark data; a customer just swaps their tag mapping and SOP/maintenance logs."*

---

## 3. Demo Flow (≈3 min on stage)

1. **Set the scene (20s):** dashboard idle, status bar shows `OFFLINE MODE — no cloud connection`.
2. **Start Alarm Storm (30s):** ~40 alarms stream in fast. Audience sees the chaos an operator faces.
3. **One click — "Correlate Incident" (40s):** edge LLM processes; incident card appears:
   - Root cause: CWP-2 motor failure (confidence: high)
   - Causal chain: pump trip → loss of cooling → bearing overheat → vibration → turbine trip
   - Citations: SOP-114 (turbine trip recovery), WO-2026-0871 (deferred maintenance)
   - Recommended actions + auto-generated shift-handover summary
4. **Privacy proof (30s):** point at the offline badge — "this just ran on local hardware; nothing left the room." (Optional: toggle WiFi off live before clicking.)
5. **Close (30s):** "In this demo: 42 alarms → 1 cited incident in ~8 seconds, fully offline — NIS2 / EU AI Act-aligned. Compression and traceability, advisory only — the operator still decides."

---

## 4. Mapping to the usecase1 Architecture

| Architecture layer | What the demo shows | Real / simulated |
|---|---|---|
| Data Sources | SCADA event stream, maintenance logs, SOPs | Synthetic cascade by default; swappable to **open ICS benchmark data (HAI / TEP)** via `dataset_to_alarms.py` |
| Event Processing | Alarm normalization, time-sync, flood detection | Real (in-app logic) |
| Context Retrieval (RAG) | SOP + work-order citations in the answer | Simulated retrieval (pre-indexed snippets); swappable for real vector DB |
| Edge LLM | Local inference via **Ollama** (e.g. llama3.1 8B / qwen2.5 7B); mock-response fallback if no LLM available | Real if Ollama installed |
| Operator Experience | Live dashboard, incident card, action panel | Real (the demo UI itself) |

---

## 5. Division of Work (proposal — to discuss with Yamini)

- **Yamini:** platform/infrastructure side — edge deployment environment, model hosting, compliance story (her usecase1 repo).
- **Chun-Kai (this demo):** application/operator side — the alarm-correlation experience that *runs on top of* that platform.
- Joint narrative on Friday: "Yamini shows **how** AI deploys at the edge; Chun-Kai shows **what it does** for the operator."

---

## 6. Tech & Hardware Plan

- **Now (laptop):** single HTML file, runs in any browser. LLM via local Ollama (`OLLAMA_ORIGINS=* ollama serve`); if no Ollama, built-in mock response keeps the demo bulletproof.
- **Stretch (if a Jetson Orin is available before Friday):** same HTML + Ollama on Jetson; demo line becomes "running on a €250 edge device."
- **Demo-day insurance:** mock mode means zero live-failure risk; Ollama mode is the "it's real" upgrade.

---

## 7. Open Questions for Yamini

1. Does this overlap with what you're building, or should I shift to the chat/copilot angle?
2. Do we present sequentially (platform → application) or as one combined flow?
3. Any chance of borrowing a Jetson before Friday?
4. Which local model do you prefer for consistency (llama3.1 / qwen / phi)?
