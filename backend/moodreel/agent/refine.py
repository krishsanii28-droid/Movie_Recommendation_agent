"""Follow-up refinements on the last set of picks ("something else", "seen them", "shorter")."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from moodreel.schemas import MoodProfile

_MORE = re.compile(r"\b(something else|more options|show me more|more please|others?|different ones?|another( one)?|not these|none of these|next|anything else|more like (?:this|these))\b", re.I)
_SEEN = re.compile(r"\b(seen (?:it|them|those|these|all|that)|already (?:seen|watched)|watched (?:them|those|these|all))\b", re.I)
_SHORTER = re.compile(r"\b(shorter|less long|too long|quicker)\b", re.I)
_LIGHTER = re.compile(r"\b(lighter|less heavy|too heavy|too sad|too dark|funnier|happier)\b", re.I)
_FASTER = re.compile(r"\b(too slow|faster|more exciting|more action|more energy|pacier)\b", re.I)
_CALMER = re.compile(r"\b(calmer|too intense|too loud|softer|gentler)\b", re.I)


@dataclass
class Refinement:
    profile: MoodProfile
    mark_seen: bool = False
    notes: list[str] = field(default_factory=list)


def detect_refinement(text: str, last: MoodProfile | None) -> Refinement | None:
    if last is None:
        return None
    hits = [p for p in (_MORE, _SEEN, _SHORTER, _LIGHTER, _FASTER, _CALMER) if p.search(text)]
    if not hits or len(text.split()) > 14:
        return None
    prof = last.model_copy(deep=True)
    ref = Refinement(prof)
    if _SEEN.search(text):
        ref.mark_seen = True
        ref.notes.append("marked those as seen")
    if _SHORTER.search(text):
        prof.context.time_available = min(prof.context.time_available or 130, 115)
        ref.notes.append("shorter runtimes")
    if _LIGHTER.search(text):
        prof.requested_tones = list(dict.fromkeys(["funny", "light"] + prof.requested_tones))
        prof.target_tones = list(dict.fromkeys(["funny", "light", "feel-good"] + prof.target_tones))[:7]
        prof.context.avoid = sorted(set(prof.context.avoid) | {"heavy"})
        prof.goal = "shift"
        ref.notes.append("lighter")
    if _FASTER.search(text):
        prof.requested_tones = list(dict.fromkeys(["fast-paced", "thrilling"] + prof.requested_tones))
        prof.target_tones = list(dict.fromkeys(["fast-paced", "thrilling", "energetic"] + prof.target_tones))[:7]
        prof.context.avoid = sorted(set(prof.context.avoid) | {"tone:slow-burn"})
        ref.notes.append("faster-paced")
    if _CALMER.search(text):
        prof.target_tones = list(dict.fromkeys(["gentle", "calming", "comforting"] + prof.target_tones))[:7]
        prof.context.avoid = sorted(set(prof.context.avoid) | {"tone:intense", "violence"})
        ref.notes.append("calmer")
    return ref
