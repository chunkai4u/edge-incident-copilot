#!/usr/bin/env python3
"""
dataset_to_alarms.py
====================
Turn an OPEN industrial-control time-series dataset into the alarm stream that
alarm_storm_demo.html consumes.

Implements the 5-step pipeline recommended for the
"Alarm Storm -> One-Click Incident Summary" demo:

  1. Read an anomaly time-window from a HAI / TEP (or generic) CSV.
  2. For each sensor tag, compute a baseline (mean/std on the normal head) and a
     rolling z-score over the window.
  3. When |z| crosses a threshold, emit an alarm: [time, severity, tag, message].
  4. Use the dataset's own attack / fault label as the ROOT-CAUSE marker.
  5. Emit a small synthetic RAG knowledge base (SOP / work order / past incident).

Why this matters for the pitch
------------------------------
Pre-revenue, you have no customer data yet. Instead of inventing numbers, the
alarm stream is *derived from a public ICS benchmark* (HAI / TEP). For a customer
you only swap the CSV + the tag-name mapping and the SOP/maintenance docs.

Supported sources (auto-detected, no third-party libs required)
---------------------------------------------------------------
  * HAI  (icsdataset/hai)  - first column timestamp, sensor columns numeric,
                             one or more `attack*` columns as the label.
  * TEP  (Tennessee Eastman) - `xmeas_*` / `xmv_*` columns, a `faultNumber`
                             (or `fault`) column; time synthesised from row index.
  * GENERIC - any CSV: first column treated as time/index, last column treated
                             as the binary anomaly label if it looks like one.

Usage
-----
  python3 dataset_to_alarms.py INPUT.csv                 # auto-detect
  python3 dataset_to_alarms.py INPUT.csv --source hai
  python3 dataset_to_alarms.py INPUT.csv --max-alarms 42 --z 3.0
  python3 dataset_to_alarms.py INPUT.csv --out-js alarms_dataset.js

Outputs
-------
  alarms_dataset.js   -> defines window.DATASET_ALARMS / window.DATASET_RAG /
                         window.DATASET_META. Drop this next to the HTML and add
                             <script src="alarms_dataset.js"></script>
                         BEFORE the main <script> block; the demo auto-uses it.
  alarms_dataset.json -> same data as plain JSON (for any other consumer).

Author: integration of Perplexity dataset recommendation into the EdgeOps demo.
"""

import argparse
import csv
import json
import math
import os
import sys
from statistics import mean, pstdev


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def is_number(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def severity_for(z):
    """Map a z-score magnitude to the demo's 4 severity levels."""
    a = abs(z)
    if a >= 6:
        return "CRITICAL"
    if a >= 4:
        return "HIGH"
    if a >= 3:
        return "MEDIUM"
    return "LOW"


def humanise(tag, z, value, baseline):
    direction = "HIGH" if z > 0 else "LOW"
    pct = ""
    if baseline not in (0, None):
        pct = f" ({(value - baseline) / abs(baseline) * 100:+.0f}% vs baseline)"
    return f"{tag} reading {direction} (z={z:+.1f}){pct}"


def synth_time(row_index, start="14:02:00", step_seconds=2):
    """Make HH:MM:SS timestamps when the dataset has no clock column."""
    h, m, s = (int(p) for p in start.split(":"))
    total = h * 3600 + m * 60 + s + row_index * step_seconds
    total %= 24 * 3600
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


# --------------------------------------------------------------------------- #
# Source detection
# --------------------------------------------------------------------------- #
def detect_source(header):
    low = [h.lower() for h in header]
    if any(h.startswith("attack") for h in low):
        return "hai"
    if any(h.startswith("xmeas") or h.startswith("xmv") for h in low) or \
       any(h in ("faultnumber", "fault") for h in low):
        return "tep"
    return "generic"


def find_label_columns(header, source):
    low = [h.lower() for h in header]
    if source == "hai":
        return [h for h, l in zip(header, low) if l.startswith("attack")]
    if source == "tep":
        return [h for h, l in zip(header, low) if l in ("faultnumber", "fault")]
    # generic: a last column that is 0/1-ish is treated as the label
    return [header[-1]]


def find_time_column(header, source):
    low = [h.lower() for h in header]
    for cand in ("time", "timestamp", "datetime", "date"):
        if cand in low:
            return header[low.index(cand)]
    if source == "hai":
        return header[0]  # HAI: first column is the timestamp
    return None  # TEP / generic: synthesise


# --------------------------------------------------------------------------- #
# Core conversion
# --------------------------------------------------------------------------- #
def convert(path, source=None, z_thresh=3.0, max_alarms=42,
            baseline_frac=0.3):
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader if r]

    if not rows:
        sys.exit("No data rows found in CSV.")

    source = source or detect_source(header)
    label_cols = find_label_columns(header, source)
    time_col = find_time_column(header, source)
    label_idx = [header.index(c) for c in label_cols if c in header]
    time_idx = header.index(time_col) if time_col in header else None

    # numeric sensor columns = everything that is not time / label and is numeric
    skip = set(label_idx) | ({time_idx} if time_idx is not None else set())
    sensor_idx = [
        i for i in range(len(header))
        if i not in skip and is_number(rows[0][i])
    ]
    if not sensor_idx:
        sys.exit("Could not find numeric sensor columns.")

    # ---- baseline on the first baseline_frac of rows (assumed normal) ----
    n_base = max(5, int(len(rows) * baseline_frac))
    baselines = {}
    for i in sensor_idx:
        vals = [float(rows[r][i]) for r in range(n_base) if is_number(rows[r][i])]
        mu = mean(vals) if vals else 0.0
        sd = pstdev(vals) if len(vals) > 1 else 0.0
        baselines[i] = (mu, sd)

    # ---- find the anomaly window (first labelled-anomaly row onward) ----
    def is_anomalous(row):
        for li in label_idx:
            v = row[li]
            if is_number(v) and float(v) != 0:
                return True
        return False

    first_anom = next((r for r in range(len(rows)) if is_anomalous(rows[r])), None)

    alarms = []
    root_cause_tag = None
    root_cause_time = None

    start = first_anom if first_anom is not None else n_base
    for r in range(start, len(rows)):
        row = rows[r]
        t = row[time_idx] if time_idx is not None else synth_time(r - start)
        # short HH:MM:SS form if HAI gives a full timestamp
        if isinstance(t, str) and len(t) > 8 and " " in t:
            t = t.split(" ")[-1][:8]

        # mark the root-cause alarm at the first anomaly transition.
        # Pick the tag with the largest *sustained* deviation over the first
        # part of the window (not just one noisy instant) so the root cause is
        # the asset that actually drifts, not a momentary spike.
        if r == first_anom and root_cause_tag is None:
            K = min(180, len(rows) - first_anom)   # attacks can ramp slowly
            MIN_PCT = 0.05                          # ignore low-variance noisy tags
            cand = []                 # (breach_offset, -peak_mag, i, peak_z)
            fb, fb_score, fb_dirz = None, 0.0, 0.0   # fallback if nothing qualifies
            for i in sensor_idx:
                mu, sd = baselines[i]
                if sd == 0:
                    continue
                zs, breach, peak, peak_val = [], None, 0.0, mu
                for off in range(K):
                    rr = first_anom + off
                    if not is_number(rows[rr][i]):
                        continue
                    v = float(rows[rr][i])
                    z = (v - mu) / sd
                    zs.append(z)
                    if abs(z) > abs(peak):
                        peak, peak_val = z, v
                    if breach is None and abs(z) >= z_thresh:
                        breach = off
                if not zs:
                    continue
                score = sum(abs(z) for z in zs) / len(zs)
                if score > fb_score:
                    fb, fb_score, fb_dirz = i, score, sum(zs) / len(zs)
                pct = abs(peak_val - mu) / abs(mu) if mu else 1.0
                if breach is not None and pct >= MIN_PCT:
                    cand.append((breach, -abs(peak), i, peak))
            # root cause = earliest tag with a real, alarm-worthy deviation
            if cand:
                cand.sort()
                best, best_dirz = cand[0][2], cand[0][3]
            else:
                best, best_dirz = fb, fb_dirz
            if best is not None:
                root_cause_tag = header[best]
                root_cause_time = t
                _dir = "HIGH" if best_dirz > 0 else "LOW"
                alarms.append([t, "CRITICAL", header[best],
                               f"ROOT CAUSE - {header[best]} earliest sustained {_dir} deviation (peak z={best_dirz:+.1f})"])

        for i in sensor_idx:
            mu, sd = baselines[i]
            if sd == 0 or not is_number(row[i]):
                continue
            z = (float(row[i]) - mu) / sd
            if abs(z) >= z_thresh:
                alarms.append([t, severity_for(z), header[i],
                               humanise(header[i], z, float(row[i]), mu)])
            if len(alarms) >= max_alarms:
                break
        if len(alarms) >= max_alarms:
            break

    if not alarms:
        sys.exit("No alarms crossed the threshold - lower --z or check the window.")

    meta = {
        "source_file": os.path.basename(path),
        "source_type": source.upper(),
        "rows_scanned": len(rows),
        "sensor_tags": len(sensor_idx),
        "z_threshold": z_thresh,
        "alarm_count": len(alarms),
        "root_cause_tag": root_cause_tag,
        "root_cause_time": root_cause_time,
        "provenance": f"Derived from open ICS benchmark ({source.upper()}). "
                      f"Swap CSV + tag map + SOP/maintenance docs for a real customer.",
    }

    rag = [
        {"id": "WO-2026-0871", "title": "Work Order (3 weeks ago)",
         "text": f"{root_cause_tag or 'Primary asset'}: abnormal vibration / elevated "
                 f"temperature noted during routine inspection. Maintenance DEFERRED "
                 f"to next planned outage due to parts lead time."},
        {"id": "SOP-114", "title": "SOP - Trip on High Vibration / Temp",
         "text": "After a protective trip: confirm coast-down, keep jacking & lube oil "
                 "pumps in service, do not restart until inspection complete and system "
                 "redundancy restored."},
        {"id": "INC-2024-031", "title": "Past Incident Report",
         "text": "Similar event in 2024: a single primary-loop trip at high load led to a "
                 "temperature excursion within ~90 seconds. Treat such trips as imminent "
                 "shutdown risk."},
    ]
    return alarms, rag, meta


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_outputs(alarms, rag, meta, out_js, out_json):
    payload = {"alarms": alarms, "rag": rag, "meta": meta}
    with open(out_json, "w") as f:
        json.dump(payload, f, indent=2)

    js = (
        "/* AUTO-GENERATED by dataset_to_alarms.py - do not edit by hand.\n"
        "   Load this BEFORE the main <script> in alarm_storm_demo.html:\n"
        '   <script src="alarms_dataset.js"></script> */\n'
        f"window.DATASET_ALARMS = {json.dumps(alarms)};\n"
        f"window.DATASET_RAG = {json.dumps(rag)};\n"
        f"window.DATASET_META = {json.dumps(meta)};\n"
    )
    with open(out_js, "w") as f:
        f.write(js)


def main():
    ap = argparse.ArgumentParser(description="ICS dataset -> demo alarm stream")
    ap.add_argument("csv", help="HAI / TEP / generic CSV file")
    ap.add_argument("--source", choices=["hai", "tep", "generic"], default=None)
    ap.add_argument("--z", type=float, default=3.0, help="z-score alarm threshold")
    ap.add_argument("--max-alarms", type=int, default=42)
    ap.add_argument("--baseline-frac", type=float, default=0.3,
                    help="fraction of head rows used as the normal baseline")
    ap.add_argument("--out-js", default="alarms_dataset.js")
    ap.add_argument("--out-json", default="alarms_dataset.json")
    args = ap.parse_args()

    alarms, rag, meta = convert(
        args.csv, source=args.source, z_thresh=args.z,
        max_alarms=args.max_alarms, baseline_frac=args.baseline_frac,
    )
    write_outputs(alarms, rag, meta, args.out_js, args.out_json)

    print("OK - dataset converted to demo alarm stream")
    print(f"  source      : {meta['source_type']}  ({meta['source_file']})")
    print(f"  sensor tags : {meta['sensor_tags']}")
    print(f"  alarms      : {meta['alarm_count']}  (root cause: {meta['root_cause_tag']})")
    print(f"  wrote       : {args.out_js}  +  {args.out_json}")
    print("\nNext: put alarms_dataset.js next to alarm_storm_demo.html and add")
    print('      <script src="alarms_dataset.js"></script> before the main script.')


if __name__ == "__main__":
    main()
