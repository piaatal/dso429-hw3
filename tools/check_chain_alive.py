"""Fail if the Answer chain has not started a run recently.

The chain is what answers rounds on time. Every deliberate failure path
emails, because the run goes red -- but a chain that stops quietly fails
nothing and so sends nothing. This runs from the scheduled workflow, which
GitHub delivers only every few hours: useless for answering rounds, but
enough to notice a corpse and turn it into an email.
"""
import datetime
import json
import os
import sys
import urllib.request

# Hand-offs are ~330 min apart; allow a late one before crying wolf.
MAX_AGE_MINUTES = 420


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "piaatal/dso429-hw3")
    url = f"https://api.github.com/repos/{repo}/actions/workflows/chain.yml/runs?per_page=1"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "dso429-hw3"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            runs = json.load(r)["workflow_runs"]
    except Exception as e:
        # An API hiccup is not evidence the chain is dead -- do not cry wolf.
        print(f"could not check the chain ({type(e).__name__}: {e}); not treating as failure")
        return 0

    if not runs:
        print("::error::No Answer chain run exists at all. "
              "Go to Actions -> Answer chain -> Run workflow.")
        return 1

    started = runs[0]["run_started_at"]
    t = datetime.datetime.fromisoformat(started.replace("Z", "+00:00"))
    age = int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60)
    print(f"newest chain run: #{runs[0]['run_number']} started {age} min ago ({started})")

    if age > MAX_AGE_MINUTES:
        print(f"::error::The Answer chain has not started a run in {age} minutes, so it "
              f"has stopped and rounds are no longer being answered. "
              f"Go to Actions -> Answer chain -> Run workflow to restart it.")
        return 1

    print("chain is alive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
