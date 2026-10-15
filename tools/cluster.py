"""Group practice questions into template families by numeric-stripped skeleton."""
import csv
import re
import sys
from collections import defaultdict

NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")


def skeleton(text):
    s = NUM.sub("<N>", text)
    return re.sub(r"\s+", " ", s).strip()


def main(qpath, kpath):
    keys = {}
    with open(kpath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys[(row["round_id"], row["q_index"])] = row["answer"]

    fams = defaultdict(list)
    with open(qpath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fams[skeleton(row["question_text"])].append(row)

    total = sum(len(v) for v in fams.values())
    print(f"{len(fams)} families / {total} questions\n")
    for i, (sk, rows) in enumerate(
        sorted(fams.items(), key=lambda kv: -len(kv[1])), 1
    ):
        r = rows[0]
        ans = keys.get((r["round_id"], r["q_index"]), "?")
        print(f"[{i}] n={len(rows)}  answer={ans}")
        print(f"  Q: {r['question_text']}")
        print(
            f"  A) {r['option_a']}   B) {r['option_b']}"
            f"   C) {r['option_c']}   D) {r['option_d']}"
        )
        print()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
