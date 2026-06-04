# Pulse — Objective Scoring Rubric

**Goal:** make every pillar score traceable to specific, observed behaviours instead of a
single subjective 1–5 judgement. A score like "Values 5/10" must be answerable with
*"because these signals fired, and these did not."*

**Source instrument:** Dosi, C., Rosati, F. & Vignoli, M. (2018), *Measuring Design
Thinking Mindset*, International Design Conference – DESIGN 2018. A factor-analysis-
validated questionnaire: **22 constructs, 71 items**, built from 17 peer-reviewed papers.

**Adaptation (stated honestly):** the original 71 items are a *self-report* Likert survey.
Pulse infers the same constructs from what the user actually says/does in coaching
conversations. This is a behavioural proxy, not the validated self-report — detection
accuracy must be calibrated during a pilot. The construct definitions and their grouping
carry the academic validity; our *detection* of them does not (yet).

---

## 1. Construct → KPMG Pillar mapping

The 22 validated constructs map onto the 6 KPMG maturity pillars as follows.

| Pillar (weight) | DT-mindset constructs assigned |
|---|---|
| **Values** (0.25) | A Ambiguity tolerance · B Embracing risk · C Human-centeredness · D Empathy · K Learning-oriented · Lb Learn-from-failure |
| **Behavior** (0.20) | F Holistic view · G Problem reframing · N Critical questioning · O Abductive thinking |
| **Climate** (0.20) | Ha Team knowledge · Hb Team interactions · I Cross-disciplinary collaboration · J Openness to diversity |
| **Process** (0.10) | E Process awareness · La Experimentation · Ma Bias for action · Mb Making tangible · P Envisioning options |
| **Success** (0.15) | Q Creative confidence · R Desire to make a difference · S Optimism to have impact |
| **Resources** (0.10) | *(not covered by the mindset instrument — see §4)* |

---

## 2. The signals (the "questions")

Each signal is something the tagger looks for in a user turn. For each, the tagger records
one of: **+1** (clearly observed), **−1** (anti-signal clearly observed), or **null** (not
applicable to this turn). Each signal cites its source construct.

### VALUES — `VAL-*`
- **VAL-1** (+) Proceeds without demanding a fully-defined/certain outcome — comfortable leaving options open. *(A)*
- **VAL-2** (−) Insists on certainty / one right answer before engaging; uncomfortable with open problems. *(A)*
- **VAL-3** (+) Willing to pursue an unconventional or risky direction; accepts possible failure. *(B)*
- **VAL-4** (+) Frames the work around real user needs rather than internal preference. *(C)*
- **VAL-5** (−) Justifies decisions by internal opinion / aesthetics / assumed user reaction ("we know they'll love it"). *(C)*
- **VAL-6** (+) References actually involving or observing real users. *(C)*
- **VAL-7** (+) Tries to see the problem from the user's perspective; considers their feelings/context. *(D)*
- **VAL-8** (+) Treats the problem as a chance to learn; seeks new knowledge or feedback. *(K)*
- **VAL-9** (+) References past failure/mistakes as learning; open to being wrong. *(Lb)*
- **VAL-10** (−) Defensive about being wrong; treats failure as purely negative. *(Lb)*

### BEHAVIOR — `BEH-*`
- **BEH-1** (+) Considers the broader system / downstream impacts / multiple factors. *(F)*
- **BEH-2** (−) Fixates on one narrow aspect, ignoring wider context. *(F)*
- **BEH-3** (+) Questions or reframes the initial problem rather than taking it at face value. *(G)*
- **BEH-4** (−) Jumps to solving the problem-as-given without interrogating it. *(G)*
- **BEH-5** (+) Asks "why" / challenges an assumption (their own or given). *(N)*
- **BEH-6** (+) Pressure-tests their own claim or invites a counter-view. *(N)*
- **BEH-7** (+) Generates multiple alternative hypotheses/possibilities. *(O)*
- **BEH-8** (−) Commits to the first idea without considering alternatives. *(O)*
- **BEH-9** (+) Reasons toward future possibility ("what if…") not only from the current state. *(O)*

### CLIMATE — `CLI-*`
- **CLI-1** (+) References team decisions / appropriately incorporates group input. *(Ha)*
- **CLI-2** (+) Talks about sharing or co-developing knowledge with teammates. *(Hb)*
- **CLI-3** (+) Involves or values people from other functions/disciplines. *(I)*
- **CLI-4** (−) Works in a silo where collaboration would clearly matter. *(I)*
- **CLI-5** (+) Open to changing their opinion; welcomes differing views. *(J)*
- **CLI-6** (−) Dismisses differing perspectives; seeks only confirming views. *(J)*
- **CLI-7** (+) Treats diverse perspectives as improving the outcome. *(J)*
- **CLI-8** (+) Raises a risky/dissenting idea (signals psychological safety). *(J)*

### PROCESS — `PRO-*`
- **PRO-1** (+) Knows which DT phase they're in; distinguishes diverge vs converge. *(E)*
- **PRO-2** (+) Recognises the need to iterate a phase. *(E)*
- **PRO-3** (−) Skips a phase — esp. jumps to a solution before empathy/define. *(E)*
- **PRO-4** (+) Proposes testing / trying things in small iterations. *(La)*
- **PRO-5** (+) Favours making something concrete over endless discussion. *(Ma)*
- **PRO-6** (−) Stuck in analysis/discussion with no path to action. *(Ma)*
- **PRO-7** (+) Turns an idea/hypothesis into something testable (prototype, mock, experiment). *(Mb)*
- **PRO-8** (+) Keeps multiple options open simultaneously. *(P)*
- **PRO-9** (−) Converges prematurely to a single option. *(P)*
- **PRO-10** (+) Can foresee different outcomes of a direction. *(P)*

### SUCCESS — `SUC-*`
- **SUC-1** (+) Shows confidence tackling an open/creative problem. *(Q)*
- **SUC-2** (+) Articulates the value/impact the solution should create. *(R)*
- **SUC-3** (+) Connects the work to a measurable outcome / how success will be judged. *(R)*
- **SUC-4** (−) Has no notion of how success will be measured. *(R)*
- **SUC-5** (+) Stays constructively optimistic about overcoming difficulty / midcourse correction. *(S)*
- **SUC-6** (+) Validates outcomes with evidence rather than declaring victory at launch. *(S)*
- **SUC-7** (−) Treats launch as the finish line — no validation/measurement. *(S)*

### RESOURCES — `RES-*`  (operational, not from the mindset instrument — see §4)
- **RES-1** References having / needing the right skills for the work.
- **RES-2** References research access / data availability.
- **RES-3** References tools or systems supporting the design work.
- **RES-4** Flags resourcing constraints (time/budget that punishes iteration).
- **RES-5** Engagement consistency (cadence of coach use) — from telemetry, not a turn.
- **RES-6** References project structure / clear ownership.

**Total: 52 signals** (46 conversational + 6 resource/operational).

---

## 3. Scoring formula

For each pillar `p`, over a chosen window (all turns, or rolling 90 days):

```
pos(p) = number of "+1" signal fires across the user's turns for that pillar
neg(p) = number of "−1" anti-signal fires
n(p)   = pos(p) + neg(p)

if n(p) < MIN_EVIDENCE (e.g. 5):  pillar_score = null  (not enough evidence yet)
else:                             pillar_score(0–10) = round( pos(p) / n(p) × 10 )
```

The Design Quality (DQ) score is unchanged in spirit — the weighted blend of pillar scores:

```
DQ = Σ  pillar_score(p) × weight(p)      (rescaled to 0–100)
```

Every fired signal is stored with the `message_id` that produced it, so any score is fully
auditable.

---

## 4. The Resources gap (honest)

The mindset instrument measures *attitudes*, so it says nothing about Resources (people,
tools, systems, project structure). Resources is better measured from **operational
telemetry** — tool/artifact activity, research-data access, engagement cadence (`RES-1..6`)
— than from a single conversation. Until those integrations exist, Resources should either
be (a) seeded from the baseline assessment and held, or (b) excluded from the live DQ and
its 0.10 weight redistributed. Recommendation: hold it from the assessment baseline and
mark it "assessment-only" on the dashboard so we never fake a live number.

---

## 5. Worked example — "Values 5/10"

Across Raj's last 90 days of coaching, the Values signals fired:

| Signal | Fires |
|---|---|
| VAL-4 (frames around real user needs) + | 3 |
| VAL-7 (sees user's perspective) + | 2 |
| VAL-8 (treats problem as learning) + | 1 |
| VAL-5 (justifies by internal assumption) − | 4 |
| VAL-10 (defensive about being wrong) − | 2 |

```
pos = 6, neg = 6, n = 12 (≥ MIN_EVIDENCE)
score = round(6 / 12 × 10) = 5  →  "Values 5/10"
```

Explanation surfaced to the user: *"Values is 5/10. You consistently frame work around real
user needs (VAL-4 ×3) and treat problems as learning, but you repeatedly justify decisions
by internal assumptions about users rather than evidence (VAL-5 ×4) and were defensive about
being wrong (VAL-10 ×2). Closing that gap is the fastest way to raise this score."*

That sentence is the whole point: the number is defensible, specific, and coachable.

---

## 6. How this changes the build (proposed, not yet implemented)

- `coach/tagging.py`: replace the single `quality_score (1–5)` with a structured call that
  returns the list of signal IDs that fired (+1/−1) for the turn.
- New table `interaction_signals(interaction_id, signal_id, polarity)` for the audit trail.
- `dashboard/metrics.py`: compute pillar scores by the §3 formula instead of averaging
  quality_score; expose the fired-signal breakdown so the UI can show the "because…" text.
- Keep `quality_score` as a coarse secondary signal during transition / for sparse data.
