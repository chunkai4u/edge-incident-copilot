# Edge Incident Copilot

**Offline incident copilot for energy and water control rooms.**

> **YC-style positioning:** We turn SCADA alarm floods into one operator-ready incident card, locally, in seconds, without sending plant data to the cloud.

This is a pitch demo for critical-infrastructure operators: power plants, water utilities, industrial sites, and other facilities where downtime, safety, and data isolation matter.

## The Problem

When something goes wrong in a plant, the control room can receive dozens of alarms in seconds.

Operators often have to jump between:

- SCADA alarm lists
- historian screens
- SOP binders
- maintenance work orders
- senior-operator memory

That creates three painful problems:

- **Alarm flood:** too many alarms, not enough signal.
- **Slow root-cause discovery:** the first alarm is not always the real problem.
- **Weak handover:** the next shift may not get a clear, evidence-backed summary.

## What This Demo Shows

During an alarm storm, the operator clicks once.

The demo compresses many raw alarms into one incident card:

- likely root cause
- critical event timeline
- recommended operator actions
- cited SOP / work-order evidence
- concise handover summary

Everything runs locally. No cloud connection is required.

## Demo Scenario

### Stage Demo: Cooling Water Pump Failure -> Turbine Trip

The default story is a realistic combined-cycle power plant upset:

1. Cooling water pump `CWP-2` trips on motor overcurrent.
2. Cooling water flow and pressure drop.
3. Lube oil and bearing temperatures rise.
4. Shaft vibration becomes critical.
5. The turbine trips and creates a cascade of downstream alarms.

The important demo moment: a deferred maintenance work order had already flagged `CWP-2` as risky. The copilot surfaces that evidence immediately.

### Dataset Mode: Public ICS Benchmark Data

The project also includes a real-data mode generated from the public **HAI industrial control systems benchmark**.

In the shipped dataset run, the converter finds an early pressure-transmitter anomaly around `P1_PIT01` and turns the benchmark time-series data into 42 SCADA-style alarms.

Important: the HAI data is real benchmark sensor data. The SOP / work-order documents used for the demo are synthetic placeholders so the product flow can be shown without customer documents.

## Who It Is For

- Power plant control rooms
- Water and wastewater facilities
- Industrial sites with strict data-sovereignty rules
- Operators who already use SCADA/DCS systems but still need faster incident understanding

## What It Is Not

This is not trying to replace Honeywell, Emerson, ABB, Yokogawa, or existing SCADA/DCS systems.

It is a **last-mile cognition layer** on top of them:

- reads alarms
- reads historian tags
- retrieves SOPs and work orders
- summarizes the situation
- keeps the human operator in control

The copilot is advisory. The operator makes the final decision.

## Why Now

Three changes make this possible now:

- Small local LLMs can run at the edge.
- Retrieval can connect alarms to plant documents.
- OT environments increasingly need data isolation because of regulation and cybersecurity risk.

This aligns with the direction of NIS2, EU AI Act expectations, and industrial data-sovereignty requirements.

## How To Run

Open the demo directly:

```bash
open alarm_storm_demo.html
```

Or double-click `alarm_storm_demo.html`.

Then:

1. Click **Start Storm**.
2. Wait for the alarm flood to stream in.
3. Click **Correlate Incident**.
4. Review the incident card.

No install is required for demo mode.

## Optional: Use A Local LLM

If Ollama is running locally, the demo can call it:

```bash
ollama serve
ollama pull llama3.1
```

The UI still works without Ollama. If no local model is available, it uses the built-in deterministic demo result.

## Optional: Run Dataset Mode

`alarms_dataset.js` is already generated from HAI 21.03 data.

To enable it, open `alarm_storm_demo.html` and uncomment this line near the bottom:

```html
<!-- <script src="alarms_dataset.js"></script> -->
```

Then reload the page.

For details, see [`README_DATASET.md`](README_DATASET.md).

## Files

| File | Purpose |
|---|---|
| `alarm_storm_demo.html` | Single-file offline demo UI |
| `dataset_to_alarms.py` | Converts public ICS CSV data into SCADA-style alarms |
| `alarms_dataset.js` | Generated HAI dataset alarm stream |
| `alarms_dataset.json` | JSON version of the generated alarm stream |
| `README_DATASET.md` | Dataset-mode details and limitations |
| `DEMO_IDEA.md` | Longer pitch notes and positioning |

## Current Status

This is a pre-pilot demo, built to show the workflow and value proposition.

The right next step is a controlled pilot with a real facility using their alarm export, historian tags, SOPs, and maintenance records.
