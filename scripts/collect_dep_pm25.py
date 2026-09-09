"""Download and audit public DEP daily PM2.5 tables; Python standard library only.

Run from any directory: python scripts/collect_dep_pm25.py
Cached HTML is reused. No school dataset or model code is modified.
"""
from __future__ import annotations

import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "broward_dep"
BASE = "https://prodapps.dep.state.fl.us/flaqs/AirQualityMonitoring/Reports/Monthly"
STATIONS = {
    "120115005": ("Coconut Creek", 2019, 1),
    "120112003": ("Pompano Highlands Fire House", 2019, 4),
    "120110035": ("Fort Lauderdale Near Road", 2019, 1),
    "120110034": ("Daniela Banu (NCore)", 2019, 1),
    "120110033": ("Vista View Park", 2021, 8),
    "120110037": ("Pompano", 2025, 9),
}


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_report(document, station, year, month):
    """Fail closed on wrong pages, unexpected values, duplicates or missing rows."""
    title = f"Readings for {calendar.month_name[month]} {year}"
    headings = re.findall(r"<h3\b[^>]*>(.*?)</h3>", document, re.I | re.S)
    if title not in [plain(h) for h in headings]:
        raise ValueError(f"Expected report heading: {title}")
    site_headings = re.findall(r"<h5\b[^>]*>(.*?)</h5>", document, re.I | re.S)
    if not any(f"L{station[2:5]}-{station[5:]}" in plain(h) for h in site_headings):
        raise ValueError("Station identifier mismatch")
    match = re.search(r"<h4\b[^>]*>\s*PM\s+2\.5\s+Data\s*</h4>(.*?)</table>", document, re.I | re.S)
    if not match:
        # Absence is not a download failure or a zero concentration.
        if "This site did not monitor" not in plain(document):
            raise ValueError("PM2.5 table absent on unrecognized report")
        return None
    block = match.group(1)
    if "Micrograms Per Cubic Meter" not in plain(block):
        raise ValueError("Unrecognized PM2.5 units")
    values = {}
    prefix = calendar.month_abbr[month].upper()
    # Some DEP reports omit closing tr tags. Read date/value td pairs instead;
    # remove scripts so chart strings cannot be mistaken for table cells.
    block = re.sub(r"<script\b[^>]*>.*?</script>", "", block, flags=re.I | re.S)
    cells = [plain(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", block, re.I | re.S)]
    for i, label in enumerate(cells):
        if re.fullmatch(r"[A-Z]{3}-\d+", label):
            if i + 1 >= len(cells):
                raise ValueError("Date lacks a value cell")
            raw = cells[i+1]
            if not re.fullmatch(prefix + r"-\d+", label):
                raise ValueError("Month mismatch in daily row")
            day = int(label.split("-")[1])
            if day in values:
                raise ValueError("Duplicate date")
            if raw != "*" and not re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
                raise ValueError(f"Unexpected concentration: {raw!r}")
            values[day] = raw
    if set(values) != set(range(1, calendar.monthrange(year, month)[1] + 1)):
        raise ValueError("Incomplete daily row structure")
    return values


def collect(job):
    station, year, month = job
    url = f"{BASE}/{station}/{month:02d}/{year}/*"
    cache = DEST / "source_html" / station / f"{year}-{month:02d}.html"
    meta_file = cache.with_suffix(".json")
    record = dict(station_id=station, station_name=STATIONS[station][0], year=year,
                  month=month, source_url=url, calendar_days=calendar.monthrange(year, month)[1])
    for attempt in range(3):
        try:
            if cache.exists() and meta_file.exists():
                payload = cache.read_bytes()
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            else:
                request = urllib.request.Request(url, headers={"User-Agent": "BrowardCapstoneDataAudit/1.0"})
                with urllib.request.urlopen(request, timeout=35) as response:
                    payload = response.read()
                meta = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "source_url": url, "sha256": hashlib.sha256(payload).hexdigest()}
            if hashlib.sha256(payload).hexdigest() != meta["sha256"]:
                raise ValueError("Cached HTML checksum mismatch")
            values = parse_report(payload.decode("utf-8-sig"), station, year, month)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(payload)
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            record.update(meta)
            record.pop("error", None)
            record["status"] = "table_present" if values is not None else "no_pm25_table"
            daily = []
            for day in range(1, record["calendar_days"] + 1):
                raw = values[day] if values is not None else None
                daily.append({"station_id": station, "station_name": STATIONS[station][0],
                              "date": date(year, month, day).isoformat(),
                              "pm25_ug_m3": float(raw) if raw not in (None, "*") else None,
                              "source_value": raw,
                              "status": "no_pm25_table" if raw is None else ("unavailable" if raw == "*" else "reported"),
                              "source_url": url, "retrieved_at_utc": meta["retrieved_at_utc"]})
            record["reported_days"] = sum(d["status"] == "reported" for d in daily)
            record["unavailable_dates"] = [d["date"] for d in daily if d["status"] != "reported"]
            return record, daily
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                time.sleep(attempt + 1)
        finally:
            time.sleep(0.15)
    record["status"] = "error"
    return record, []


def write_results(months, daily):
    months.sort(key=lambda r: (r["station_id"], r["year"], r["month"]))
    daily.sort(key=lambda r: (r["station_id"], r["date"]))
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "monthly_audit.json").write_text(json.dumps(months, indent=2), encoding="utf-8")
    with (DEST / "daily_pm25.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in daily:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    errors = [m for m in months if m["status"] == "error"]
    summaries = []
    gaps = []
    for station, (name, _, _) in STATIONS.items():
        rows = [d for d in daily if d["station_id"] == station]
        for year in sorted({d["date"][:4] for d in rows}):
            subset = [d for d in rows if d["date"].startswith(year)]
            count = sum(d["status"] == "reported" for d in subset)
            summaries.append({"station_id": station, "station_name": name, "year": int(year),
                              "inspected_days": len(subset), "reported_days": count,
                              "missing_days": len(subset)-count, "coverage_percent": count/len(subset)*100})
        run = []
        for row in rows + [None]:
            if row is not None and row["status"] != "reported":
                if run and date.fromisoformat(row["date"]) != date.fromisoformat(run[-1])+timedelta(days=1):
                    gaps.append(dict(station_id=station, start=run[0], end=run[-1], days=len(run)))
                    run = []
                run.append(row["date"])
            elif run:
                gaps.append(dict(station_id=station, start=run[0], end=run[-1], days=len(run)))
                run = []
    (DEST / "annual_coverage.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    (DEST / "missing_runs.json").write_text(json.dumps(gaps, indent=2), encoding="utf-8")
    lines = ["# Broward PM2.5 historical coverage audit", "",
             f"Retrieved {len(months)} monthly reports; {len(errors)} errors. Sources are Florida DEP FLAQS monthly report tables.", "",
             "Ranges follow the user-provided starting months and end in December 2025. Partial first years use only inspected months as the denominator. Start months are collection boundaries, not verified instrument commissioning dates.", "",
             "| Station | Year | Readings / inspected days | Missing | Coverage |",
             "| --- | --- | --- | --- | --- |"]
    for r in summaries:
        lines.append(f'| {r["station_name"]} | {r["year"]} | {r["reported_days"]} / {r["inspected_days"]} | {r["missing_days"]} | {r["coverage_percent"]:.1f}% |')
    lines += ["", "## Longest gaps by station", ""]
    for station, (name, _, _) in STATIONS.items():
        station_gaps = [g for g in gaps if g["station_id"] == station]
        if station_gaps:
            g = max(station_gaps, key=lambda r:r["days"])
            month, year = g["start"][5:7], g["start"][:4]
            lines.append(f'- {name}: {g["days"]} days, {g["start"]} through {g["end"]}. [Source month]({BASE}/{station}/{month}/{year}/*)')
        else:
            lines.append(f"- {name}: no missing dates in the inspected reports.")
    lines += ["", "## Files and interpretation", "",
              "- `data/broward_dep/daily_pm25.jsonl`: one record per calendar day; null indicates missing, never zero-filled.",
              "- `data/broward_dep/monthly_audit.json`: source links, retrieval timestamps, HTML SHA256 hashes and monthly coverage.",
              "- `data/broward_dep/annual_coverage.json` and `missing_runs.json`: calculated summaries.",
              "- `data/broward_dep/source_html/`: cached source HTML and retrieval metadata.", "",
              "Reported numeric values are daily PM2.5 averages in micrograms per cubic meter. Presence of a value does not establish regulatory validity, hourly completeness, instrument comparability, or real-time availability. Causes of gaps have not been established. No values were imputed, no weather data were joined, and no model was trained.", "",
              "Before modeling, verify monitor methods and quality metadata against EPA AQS, preserve calendar gaps when creating lags and next-day targets, and use chronological evaluation. Missing targets must not be invented. Long gaps warrant a second station for comparison.", "",
              "Re-run `python scripts/collect_dep_pm25.py` to regenerate from cached HTML or retrieve missing months. Collection uses at most three concurrent requests, bounded retries, and fails visibly on malformed tables."]
    if errors:
        lines += ["", "## Unresolved reports", ""] + [f'- {r["source_url"]}: {r["error"]}' for r in errors]
    (ROOT / "BROWARD_COVERAGE_AUDIT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return summaries, errors


def main():
    jobs = [(site, year, month) for site, (_, first_year, first_month) in STATIONS.items()
            for year in range(first_year, 2026) for month in range(1, 13)
            if (year, month) >= (first_year, first_month)]
    months, daily = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(collect, job): job for job in jobs}
        for index, future in enumerate(as_completed(futures), 1):
            record, rows = future.result()
            months.append(record)
            daily.extend(rows)
            if index % 20 == 0 or record["status"] == "error" or index == len(jobs):
                print(f'{index}/{len(jobs)} reports; latest {record["station_id"]} {record["year"]}-{record["month"]:02d}: {record["status"]}', flush=True)
    summaries, errors = write_results(months, daily)
    print(json.dumps({"reports":len(months), "days":len(daily), "reported_days":sum(r["status"]=="reported" for r in daily), "errors":len(errors)}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
