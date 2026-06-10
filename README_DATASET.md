# Dataset Mode — Quickstart

The demo (`alarm_storm_demo.html`) runs two ways:

- **Default (synthetic):** double-click the HTML. You get the curated CWP-2 → turbine-trip cascade with the deferred-work-order "wow" moment. Zero setup, zero risk — use this on stage. The **DATA** badge reads `SYNTHETIC CASCADE`.
- **Real-data mode:** the alarm stream is derived from a public ICS benchmark (**HAI**). The **DATA** badge turns purple and the incident card is generated from the dataset, not the CWP-2 story.

## Flip to real-data mode (one line)

`alarms_dataset.js` is **already generated from the real HAI 21.03 data** (`test1.csv`). To use it, open `alarm_storm_demo.html` and uncomment this line (near the bottom, just above the main `<script>`):

```html
<!-- <script src="alarms_dataset.js"></script> -->
```

Reload. The badge shows `DATA: HAI (open benchmark)`, the storm streams real HAI sensor alarms, and the incident card reports the dataset-derived root cause (in the shipped run: **P1_PIT01**, a process-pressure transmitter that drops ~20-27% at the labeled attack onset, with the control-valve / pressure cascade following). Re-comment the line to return to the stage-safe synthetic story.

## Regenerate from any HAI / TEP file

```bash
python3 dataset_to_alarms.py path/to/file.csv          # auto-detects HAI/TEP
python3 dataset_to_alarms.py file.csv --z 3.0 --max-alarms 42
```

Writes `alarms_dataset.js` (+ `.json`). Keep the `.js` next to the HTML.

### Note on the HAI download (Git LFS)

In `~/Downloads/hai-master`, the newer `.csv` files (hai-22.04, hai-23.05) are **Git LFS pointers** (~133 bytes) unless you run `git lfs pull`. The older **`hai-21.03/*.csv.gz`** and `hai-20.07/*.csv.gz` are real data — that's what was used here (`gunzip test1.csv.gz` then convert). To use the 22.04 / 23.05 CSVs, run `git lfs install && git lfs pull` in the repo first.

## What the converter does (5-step pipeline)

1. Reads the anomaly time-window from the CSV (uses the dataset's own `attack`/`fault` labels).
2. Per sensor tag: baseline (mean/std on the normal head) → z-score.
3. Threshold breach → alarm `[time, severity, tag, message]`.
4. Root cause = earliest tag with a real, alarm-worthy deviation (>=5% change) at onset.
5. Adds three synthetic RAG docs (SOP / work order / past incident).

## For a real customer

Swap three things, nothing else: their **CSV**, the **tag-name mapping**, and their **SOP / maintenance docs**. Pipeline and UI stay the same.

## Files

| File | What it is |
|---|---|
| `alarm_storm_demo.html` | The demo (synthetic by default, dataset-aware) |
| `dataset_to_alarms.py` | CSV -> alarm-stream converter |
| `alarms_dataset.js` / `.json` | Alarm stream generated from real HAI 21.03 `test1.csv` |
| `DEMO_IDEA.md` | Pitch / proposal, incl. the data-strategy section |
