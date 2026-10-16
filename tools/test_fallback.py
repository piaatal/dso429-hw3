"""The degradation guarantee: one unsolvable question must not spoil a round."""
import json
import sys

from submit import answer_round, EXPECTED_QUESTIONS

VALID = {"A", "B", "C", "D"}


def row(qi, text, opts):
    return {
        "round_id": "99",
        "q_index": str(qi),
        "released_at": "2026-10-20T12:00:00Z",
        "question_text": text,
        "option_a": opts[0], "option_b": opts[1],
        "option_c": opts[2], "option_d": opts[3],
    }


def main():
    failures = []

    # 24 solvable + 1 from a template that does not exist.
    rows = [
        row(i, f"A retailer sells {i + 10} units at $3.00 each. What is total revenue?",
            [f"${(i + 10) * 3}.00", "$1.00", "$2.00", "$4.00"])
        for i in range(1, 25)
    ]
    rows.append(row(25, "What is the airspeed velocity of an unladen swallow?",
                    ["11 m/s", "12 m/s", "13 m/s", "14 m/s"]))

    answers, problems = answer_round(rows)

    if len(answers) != EXPECTED_QUESTIONS:
        failures.append(f"expected 25 answers, got {len(answers)}")
    if set(answers) != {f"q{i}" for i in range(1, 26)}:
        failures.append("answer keys are not exactly q1..q25")
    bad = {k: v for k, v in answers.items() if v not in VALID}
    if bad:
        failures.append(f"non-ABCD values: {bad}")
    if not problems:
        failures.append("unsolvable question was not reported as a problem")
    if [p["q"] for p in problems] != [25]:
        failures.append(f"wrong question flagged: {problems}")
    try:
        json.dumps({"round_id": 99, "answers": answers})
    except (TypeError, ValueError) as e:
        failures.append(f"not JSON-serialisable: {e}")

    # A completely truncated round must still produce a full file.
    short_answers, short_problems = answer_round([rows[0]])
    if len(short_answers) != EXPECTED_QUESTIONS:
        failures.append("truncated round did not get a full 25-answer file")
    if len(short_problems) != 24:
        failures.append(f"truncated round flagged {len(short_problems)} problems, want 24")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: 25 valid answers written despite an unsolvable question")
    print(f"      flagged: {problems}")
    print(f"      q25 fell back to {answers['q25']!r}")
    print("PASS: a truncated round still yields a complete file")
    return 0


def test_exploding_solver():
    """A solver that raises must not cost the round its file."""
    import solver

    original = solver.FAMILIES

    def boom(q):
        raise OverflowError("simulated solver blow-up")

    solver.FAMILIES = [("boom", boom)]
    try:
        answers, problems = answer_round(
            [row(i, "anything at all", ["1", "2", "3", "4"]) for i in range(1, 26)]
        )
    finally:
        solver.FAMILIES = original

    failures = []
    if len(answers) != EXPECTED_QUESTIONS:
        failures.append(f"lost answers when the solver raised: {len(answers)}")
    if any(v not in VALID for v in answers.values()):
        failures.append("invalid letters after solver raised")
    if len(problems) != EXPECTED_QUESTIONS:
        failures.append(f"problems not recorded: {len(problems)}")
    for f in failures:
        print(f"FAIL: {f}")
    if not failures:
        print("PASS: a solver that raises still yields 25 valid answers")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main() or test_exploding_solver())
