"""Score the solver against the published practice answer keys."""
import csv
import sys
from collections import Counter, defaultdict

from solver import solve


def main(qpath, kpath):
    keys = {}
    with open(kpath, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            keys[(r["round_id"], r["q_index"])] = r["answer"].strip().upper()

    per_family = defaultdict(Counter)
    wrong, unknown = [], []
    total = 0

    with open(qpath, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            total += 1
            opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
            letter, fam = solve(r["question_text"], opts)
            truth = keys.get((r["round_id"], r["q_index"]))
            if letter is None:
                unknown.append(r)
                per_family["<unrecognized>"]["unknown"] += 1
            elif letter == truth:
                per_family[fam]["ok"] += 1
            else:
                per_family[fam]["wrong"] += 1
                wrong.append((r, letter, truth, fam))

    ok = sum(c["ok"] for c in per_family.values())
    print(f"correct {ok}/{total}   wrong {len(wrong)}   unknown {len(unknown)}\n")
    for fam in sorted(per_family):
        c = per_family[fam]
        print(f"  {fam:<20} ok={c['ok']:<5} wrong={c['wrong']:<4} unknown={c['unknown']}")

    for r, got, truth, fam in wrong[:5]:
        print(f"\nWRONG [{fam}] r{r['round_id']}q{r['q_index']} got {got} want {truth}")
        print(f"  {r['question_text']}")
        print(f"  A) {r['option_a']}  B) {r['option_b']}  C) {r['option_c']}  D) {r['option_d']}")
    for r in unknown[:5]:
        print(f"\nUNKNOWN r{r['round_id']}q{r['q_index']}: {r['question_text']}")

    return 0 if (not wrong and not unknown) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
