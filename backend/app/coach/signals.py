"""The 52-signal scoring rubric (see docs/SCORING_RUBRIC.md).

Each signal is an observable behaviour in a user's turn, tied to one pillar and a fixed
polarity (+1 positive, -1 anti-signal). The tagger returns which signals fired; the
dashboard scores a pillar as positives / (positives + negatives). Every score is therefore
traceable to specific fired signals.

Source: Dosi, Rosati & Vignoli (2018), "Measuring Design Thinking Mindset" (22 constructs).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    id: str
    pillar: str
    polarity: int  # +1 or -1
    text: str


SIGNALS: list[Signal] = [
    # VALUES
    Signal("VAL-1", "values", +1, "Proceeds without demanding a fully-defined/certain outcome; comfortable leaving options open"),
    Signal("VAL-2", "values", -1, "Insists on certainty or one right answer before engaging; uncomfortable with open problems"),
    Signal("VAL-3", "values", +1, "Willing to pursue an unconventional or risky direction; accepts possible failure"),
    Signal("VAL-4", "values", +1, "Frames the work around real user needs rather than internal preference"),
    Signal("VAL-5", "values", -1, "Justifies decisions by internal opinion/aesthetics or assumed user reaction (\"we know they'll love it\")"),
    Signal("VAL-6", "values", +1, "References actually involving or observing real users"),
    Signal("VAL-7", "values", +1, "Tries to see the problem from the user's perspective; considers their feelings/context"),
    Signal("VAL-8", "values", +1, "Treats the problem as a chance to learn; seeks new knowledge or feedback"),
    Signal("VAL-9", "values", +1, "References past failure/mistakes as learning; open to being wrong"),
    Signal("VAL-10", "values", -1, "Defensive about being wrong; treats failure as purely negative"),
    # BEHAVIOR
    Signal("BEH-1", "behavior", +1, "Considers the broader system, downstream impacts, or multiple factors"),
    Signal("BEH-2", "behavior", -1, "Fixates on one narrow aspect, ignoring the wider context"),
    Signal("BEH-3", "behavior", +1, "Questions or reframes the initial problem rather than taking it at face value"),
    Signal("BEH-4", "behavior", -1, "Jumps to solving the problem as given without interrogating it"),
    Signal("BEH-5", "behavior", +1, "Asks \"why\" or challenges an assumption (their own or one given to them)"),
    Signal("BEH-6", "behavior", +1, "Pressure-tests their own claim or invites a counter-view"),
    Signal("BEH-7", "behavior", +1, "Generates multiple alternative hypotheses or possibilities"),
    Signal("BEH-8", "behavior", -1, "Commits to the first idea without considering alternatives"),
    Signal("BEH-9", "behavior", +1, "Reasons toward future possibility (\"what if…\") not only from the current state"),
    # CLIMATE
    Signal("CLI-1", "climate", +1, "References team decisions or appropriately incorporates group input"),
    Signal("CLI-2", "climate", +1, "Talks about sharing or co-developing knowledge with teammates"),
    Signal("CLI-3", "climate", +1, "Involves or values people from other functions or disciplines"),
    Signal("CLI-4", "climate", -1, "Works in a silo where collaboration would clearly matter"),
    Signal("CLI-5", "climate", +1, "Open to changing their opinion; welcomes differing views"),
    Signal("CLI-6", "climate", -1, "Dismisses differing perspectives; seeks only confirming views"),
    Signal("CLI-7", "climate", +1, "Treats diverse perspectives as improving the outcome"),
    Signal("CLI-8", "climate", +1, "Raises a risky or dissenting idea (signals psychological safety)"),
    # PROCESS
    Signal("PRO-1", "process", +1, "Knows which design-thinking phase they're in; distinguishes diverge vs converge"),
    Signal("PRO-2", "process", +1, "Recognises the need to iterate a phase"),
    Signal("PRO-3", "process", -1, "Skips a phase — especially jumps to a solution before empathy/define"),
    Signal("PRO-4", "process", +1, "Proposes testing or trying things in small iterations"),
    Signal("PRO-5", "process", +1, "Favours making something concrete over endless discussion"),
    Signal("PRO-6", "process", -1, "Stuck in analysis/discussion with no path to action"),
    Signal("PRO-7", "process", +1, "Turns an idea or hypothesis into something testable (prototype, mock, experiment)"),
    Signal("PRO-8", "process", +1, "Keeps multiple options open simultaneously"),
    Signal("PRO-9", "process", -1, "Converges prematurely to a single option"),
    Signal("PRO-10", "process", +1, "Can foresee different outcomes of a direction"),
    # SUCCESS
    Signal("SUC-1", "success", +1, "Shows confidence tackling an open or creative problem"),
    Signal("SUC-2", "success", +1, "Articulates the value or impact the solution should create"),
    Signal("SUC-3", "success", +1, "Connects the work to a measurable outcome or how success will be judged"),
    Signal("SUC-4", "success", -1, "Has no notion of how success will be measured"),
    Signal("SUC-5", "success", +1, "Stays constructively optimistic about overcoming difficulty or midcourse correction"),
    Signal("SUC-6", "success", +1, "Validates outcomes with evidence rather than declaring victory at launch"),
    Signal("SUC-7", "success", -1, "Treats launch as the finish line — no validation or measurement"),
    # RESOURCES (operational; fire only when the user explicitly mentions them)
    Signal("RES-1", "resources", +1, "References having or needing the right skills for the work"),
    Signal("RES-2", "resources", +1, "References research access or data availability"),
    Signal("RES-3", "resources", +1, "References tools or systems supporting the design work"),
    Signal("RES-4", "resources", -1, "Flags resourcing constraints (time/budget that punishes iteration)"),
    Signal("RES-6", "resources", +1, "References clear project structure or ownership"),
]

BY_ID: dict[str, Signal] = {s.id: s for s in SIGNALS}
ALL_IDS: list[str] = [s.id for s in SIGNALS]
PILLARS = ["values", "behavior", "climate", "process", "resources", "success"]


def prompt_catalog() -> str:
    """Human-readable list of signals for the tagging prompt, grouped by pillar."""
    lines: list[str] = []
    for pillar in PILLARS:
        lines.append(f"\n[{pillar.upper()}]")
        for s in SIGNALS:
            if s.pillar == pillar:
                sign = "+" if s.polarity > 0 else "-"
                lines.append(f"  {s.id} ({sign}): {s.text}")
    return "\n".join(lines)
