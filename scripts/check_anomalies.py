"""
Runs statistical analysis to check for anomalies in the trend data

Usage:
    Used in the scrape-jobs.yml cron job, ran after the commit of the new "daily.jsonl"
    Checks to see if there is a major difference in the data as compared to previous days
    Useful to see if for e.g. Workday ATS goes from 200k jobs, to 0 jobs.
"""

import json
import os
import statistics
from pathlib import Path

TRENDS_FILE = Path("data/trends/daily.jsonl")
LOOKBACK_DAYS = 7
THRESHOLD_STDDEVS = 3
MIN_DAYS = 5


def load_history():
    rows = []
    with open(TRENDS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    by_date = {}
    for r in rows:
        by_date[r["date"]] = r
    return [by_date[d] for d in sorted(by_date)]


def main():
    history = load_history()
    if len(history) < MIN_DAYS + 1:
        print(f"Not enough history ({len(history)} days). Skipping.")
        return

    today = history[-1]
    baseline_days = history[-(LOOKBACK_DAYS + 1) : -1]
    anomalies = []

    for platform, today_count in today["by_platform"].items():
        prior = [
            d["by_platform"][platform]
            for d in baseline_days
            if platform in d["by_platform"]
        ]
        if len(prior) < MIN_DAYS:
            continue  # new platform, not enough history yet

        mean = statistics.mean(prior)
        stdev = statistics.pstdev(prior)

        if stdev == 0:
            # perfectly flat history, fall back to a small percentage band
            if abs(today_count - mean) / mean > 0.10:
                anomalies.append(f"{platform}: {today_count} vs flat {round(mean)}")
            continue

        standard_score = (today_count - mean) / stdev
        if abs(standard_score) > THRESHOLD_STDDEVS:
            direction = "SPIKE" if standard_score > 0 else "DROP"
            anomalies.append(
                f"{platform}: {direction}, {today_count} vs {round(mean)} mean "
                f"(The Z (standard score) is ={round(standard_score, 1)}, {round((today_count/mean)*100)}% of normal)"
            )

    if anomalies:
        report = "Job scraper anomaly detected:\n\n" + "\n".join(anomalies)
        print(report)
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("anomaly=true\n")
            f.write("report<<EOF\n")
            f.write(report + "\n")
            f.write("EOF\n")
    else:
        print("All platforms within normal range.")


if __name__ == "__main__":
    main()
