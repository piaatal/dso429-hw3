"""Independently check the answer files on disk against the practice keys."""
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID = {"A", "B", "C", "D"}


def main(kpath):
    keys = defaultdict(dict)
    with open(kpath, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            keys[int(r["round_id"])][f"q{int(r['q_index'])}"] = r["answer"].strip().upper()

    paths = sorted(glob.glob(os.path.join(ROOT, "answers", "round-*.json")))
    print(f"{len(paths)} answer files found")

    structural, correct, graded = [], 0, 0
    for p in paths:
        name = os.path.basename(p)
        if not re.fullmatch(r"round-\d{4}\.json", name):
            structural.append(f"{name}: bad filename")
            continue
        rid = int(name[6:10])
        try:
            with open(p, encoding="utf-8") as f:
                doc = json.load(f)
        except json.JSONDecodeError as e:
            structural.append(f"{name}: invalid JSON ({e})")
            continue
        ans = doc.get("answers")
        if not isinstance(ans, dict):
            structural.append(f"{name}: no answers object")
            continue
        expected_keys = {f"q{i}" for i in range(1, 26)}
        if set(ans) != expected_keys:
            structural.append(f"{name}: keys are not exactly q1..q25")
            continue
        bad = {k: v for k, v in ans.items() if v not in VALID}
        if bad:
            structural.append(f"{name}: non-ABCD values {bad}")
            continue
        if doc.get("round_id") != rid:
            structural.append(f"{name}: round_id {doc.get('round_id')} != filename")

        for q, letter in ans.items():
            truth = keys.get(rid, {}).get(q)
            if truth:
                graded += 1
                correct += letter == truth

    print(f"structural problems: {len(structural)}")
    for s in structural[:10]:
        print(f"  {s}")
    if graded:
        print(f"against practice keys: {correct}/{graded} correct")

    # Round 1 is printed in the assignment PDF -- eyeball it.
    with open(os.path.join(ROOT, "answers", "round-0001.json"), encoding="utf-8") as f:
        a = json.load(f)["answers"]
    print("round 1:", " ".join(a[f"q{i}"] for i in range(1, 26)))
    return 0 if not structural and correct == graded else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
