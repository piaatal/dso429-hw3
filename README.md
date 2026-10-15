# DSO 429 — Homework 3: The Hourly Quiz

Answers to the hourly quiz at
[FaisalXL/dso429-hourly-quiz](https://github.com/FaisalXL/dso429-hourly-quiz).

A new round of 25 multiple-choice questions is published every hour. Each round
scores `fraction correct × timing credit`, and timing credit is 100% only within
three hours of release — including overnight. So the pipeline runs on GitHub
Actions rather than on a laptop.

## How it works

A GitHub Actions job runs four times an hour. It fetches `questions.csv`,
finds every round with no answer file yet, solves it, and pushes the result.
Nothing depends on a local machine being awake.

Answers come from three tiers:

1. **Deterministic solver** (`tools/solver.py`) — recognizes the question
   template, computes the exact value, and matches it to the closest option.
   This answers everything; it scores 1200/1200 on the practice set.
2. **`solve_unknown()` hook** (`tools/submit.py`) — currently a no-op. An
   unrecognized template should raise an alarm, not be quietly papered over.
   Swapping in an API call here is a one-function change.
3. **Fallback letter** — if both tiers decline, a valid letter is still written.

The ordering rule is **degrade per question, never per round**: a round always
gets a complete, valid 25-answer file, because a missing or malformed file
scores zero for all 25. `tools/test_fallback.py` enforces this.

When any question reaches tier 2 or 3, the job **pushes the answers first and
then fails**, so the answers are safely on GitHub and the red run emails an
alert. Rounds still inside the three-hour window are revisited on later runs,
so a solver fix pushed afterwards upgrades answers that were guessed.

## The 12 question templates

discount · unit revenue · currency conversion · weighted average · gross margin
· compound interest · break-even units · probability · percentage change ·
ratio split · arithmetic sequence · settlement date

## Layout

- `answers/` — one JSON file per round; **this is what gets graded**
- `meta/` — per-round provenance (kept out of `answers/` deliberately)
- `tools/` — solver and scripts
- `.github/workflows/answer.yml` — the hourly job

## Running locally

```bash
cd tools
python3 submit.py                 # answer any unanswered rounds
python3 validate.py ../data/questions.csv ../data/practice_keys.csv
python3 verify_answers.py ../data/practice_keys.csv
python3 test_fallback.py
```

`tools/cluster.py` groups questions by template, for finding new families.
