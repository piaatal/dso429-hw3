"""Answer every published round that has no answer file yet.

Design rules (see README):
  * Degrade per question, never per round -- a round always gets a complete,
    valid 25-answer file even if some questions could not be solved.
  * Tier 1 solver -> Tier 2 hook (currently a no-op) -> Tier 3 fallback letter.
  * Rounds still inside the 3-hour full-credit window are revisited, so a
    solver fix pushed later upgrades answers that were guessed.
Exit code 1 means "files were still written, but something needs a human".
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from solver import solve

QUESTIONS_URL = (
    "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/questions.csv"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSWERS = os.path.join(ROOT, "answers")
META = os.path.join(ROOT, "meta")

FULL_CREDIT = timedelta(hours=3)
PARTIAL_ROUND_GRACE = timedelta(minutes=30)
FALLBACK_LETTER = "A"
EXPECTED_QUESTIONS = 25


def solve_unknown(question, options):
    """Tier 2 hook. Returns a letter, or None.

    Deliberately a no-op: the Tier 1 solver covers every known template, and an
    unsolved question should raise an alarm rather than be quietly papered over
    by a model. Swap in an API call here to automate the fallback.
    """
    return None


def fetch(source):
    if source.startswith(("http://", "https://")):
        # Bust the raw-CDN cache, which can serve a round up to ~5 min stale.
        sep = "&" if "?" in source else "?"
        url = f"{source}{sep}cb={int(datetime.now(timezone.utc).timestamp())}"
        req = urllib.request.Request(url, headers={"User-Agent": "dso429-hw3"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8")
    with open(source, encoding="utf-8") as f:
        return f.read()


def load_rounds(text):
    rounds = defaultdict(list)
    for row in csv.DictReader(io.StringIO(text)):
        rounds[int(row["round_id"])].append(row)
    for rows in rounds.values():
        rows.sort(key=lambda r: int(r["q_index"]))
    return rounds


def released_at(rows):
    stamp = rows[0].get("released_at", "")
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def answer_round(rows):
    """-> (answers dict, list of {q, reason} for anything not solved cleanly)."""
    answers, problems = {}, []
    for row in rows:
        qi = int(row["q_index"])
        opts = [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
        letter, _family = solve(row["question_text"], opts)
        if letter is None:
            letter = solve_unknown(row["question_text"], opts)
            reason = "tier2" if letter else "guess"
            if letter is None:
                letter = FALLBACK_LETTER
            problems.append({"q": qi, "reason": reason})
        answers[f"q{qi}"] = letter

    for qi in range(1, EXPECTED_QUESTIONS + 1):
        if f"q{qi}" not in answers:       # round published incomplete
            answers[f"q{qi}"] = FALLBACK_LETTER
            problems.append({"q": qi, "reason": "missing"})

    ordered = {f"q{i}": answers[f"q{i}"] for i in range(1, EXPECTED_QUESTIONS + 1)}
    return ordered, problems


def write_round(rid, answers, problems, rows):
    os.makedirs(ANSWERS, exist_ok=True)
    os.makedirs(META, exist_ok=True)
    path = os.path.join(ANSWERS, f"round-{rid:04d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"round_id": rid, "answers": answers}, f, indent=2)
        f.write("\n")
    with open(os.path.join(META, f"round-{rid:04d}.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "round_id": rid,
                "released_at": rows[0].get("released_at"),
                "answered_at": datetime.now(timezone.utc).isoformat(),
                "questions_seen": len(rows),
                "problems": problems,
            },
            f,
            indent=2,
        )
        f.write("\n")
    return path


def existing_answers(rid):
    path = os.path.join(ANSWERS, f"round-{rid:04d}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("answers")
    except (json.JSONDecodeError, OSError):
        return None       # unreadable: treat as unanswered and rewrite


def had_problems(rid):
    path = os.path.join(META, f"round-{rid:04d}.json")
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            return bool(json.load(f).get("problems"))
    except (json.JSONDecodeError, OSError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=QUESTIONS_URL)
    ap.add_argument("--max-round", type=int, help="ignore rounds above this")
    args = ap.parse_args()

    rounds = load_rounds(fetch(args.source))
    now = datetime.now(timezone.utc)
    written, revisited, skipped, alerts = [], [], [], []

    for rid in sorted(rounds):
        if args.max_round and rid > args.max_round:
            continue
        rows = rounds[rid]
        rel = released_at(rows)
        fresh = rel is not None and (now - rel) < FULL_CREDIT
        current = existing_answers(rid)

        if current is not None and not (fresh and had_problems(rid)):
            continue

        if len(rows) < EXPECTED_QUESTIONS:
            young = rel is not None and (now - rel) < PARTIAL_ROUND_GRACE
            if young and current is None:
                skipped.append((rid, len(rows)))
                continue

        answers, problems = answer_round(rows)
        if current == answers:
            continue
        write_round(rid, answers, problems, rows)
        (revisited if current is not None else written).append(rid)
        if problems:
            alerts.append((rid, problems))

    def fmt(ids):
        return ", ".join(str(i) for i in ids) if ids else "none"

    print(f"rounds seen      : {len(rounds)}")
    print(f"newly answered   : {len(written)} ({fmt(written)})")
    print(f"revisited        : {len(revisited)} ({fmt(revisited)})")
    if skipped:
        print(f"waiting (partial): {', '.join(f'r{r}({n}/25)' for r, n in skipped)}")

    if alerts:
        print("\n!! rounds needing attention (answers were still written):")
        for rid, problems in alerts:
            detail = ", ".join(f"q{p['q']}:{p['reason']}" for p in problems)
            print(f"   round {rid}: {detail}")
        return 1
    print("\nall questions solved by the deterministic solver")
    return 0


if __name__ == "__main__":
    sys.exit(main())
