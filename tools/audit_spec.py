"""Audit the repo against every mechanical requirement in the assignment."""
import csv
import glob
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://raw.githubusercontent.com/FaisalXL/dso429-hourly-quiz/main/questions.csv"
VALID = {"A", "B", "C", "D"}
ok, bad = [], []


def check(cond, msg):
    (ok if cond else bad).append(msg)


with urllib.request.urlopen(URL, timeout=60) as r:
    rows = list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
published = {}
for row in rows:
    published.setdefault(int(row["round_id"]), set()).add(int(row["q_index"]))

files = sorted(glob.glob(os.path.join(ROOT, "answers", "*")))
names = [os.path.basename(p) for p in files]

# 1. "answers/round-0001.json", round number padded to four digits
check(all(re.fullmatch(r"round-\d{4}\.json", n) for n in names),
      f"every file in answers/ is named round-NNNN.json ({len(names)} files)")

answered = set()
for p in files:
    n = os.path.basename(p)
    if not re.fullmatch(r"round-\d{4}\.json", n):
        continue
    rid = int(n[6:10])
    answered.add(rid)
    with open(p, encoding="utf-8") as f:
        raw = f.read()
    try:
        doc = json.loads(raw)                      # "not valid JSON = not submitted"
    except json.JSONDecodeError as e:
        bad.append(f"{n}: invalid JSON ({e})")
        continue
    a = doc.get("answers")
    if not isinstance(a, dict):
        bad.append(f"{n}: missing answers object")
        continue
    if set(a) != {f"q{i}" for i in range(1, 26)}:
        bad.append(f"{n}: keys are not exactly q1..q25")
    off = {k: v for k, v in a.items() if v not in VALID}
    if off:
        bad.append(f"{n}: values outside A-D: {off}")
    # 4-digit padding must match the round it claims
    if doc.get("round_id") != rid:
        bad.append(f"{n}: round_id {doc.get('round_id')} != filename {rid}")

check(not any(b.startswith("round-") for b in bad), "all files valid JSON, q1..q25, values A-D")

# 2. every published round is answered; no answers for unpublished rounds
missing = sorted(set(published) - answered)
extra = sorted(answered - set(published))
check(not missing, f"every published round has an answer file (published={len(published)})")
if missing:
    bad.append(f"rounds published but unanswered: {missing}")
check(not extra, "no answer files for rounds that were never published")
if extra:
    bad.append(f"answer files for unpublished rounds: {extra}")

# 3. rounds with incomplete question sets
partial = {r: len(q) for r, q in published.items() if len(q) != 25}
check(not partial, "every published round has all 25 questions")
if partial:
    bad.append(f"rounds published with != 25 questions: {partial}")

# 4. graded range sanity
graded = sorted(r for r in published if r >= 49)
check(True, f"practice rounds answered: {len([r for r in answered if r <= 48])}/48")
check(True, f"graded rounds published so far: {len(graded)} (49-168 expected eventually)")

print("PASS")
for m in ok:
    print(f"  + {m}")
if bad:
    print("ISSUES")
    for m in bad:
        print(f"  - {m}")
sys.exit(1 if bad else 0)
