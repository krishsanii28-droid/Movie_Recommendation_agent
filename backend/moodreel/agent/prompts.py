"""System prompt and message templates for the MoodReel agent."""

from __future__ import annotations

import json

from moodreel.schemas import MoodProfile

SYSTEM_PROMPT = """You are MoodReel, a warm, film-loving friend who recommends movies based on how people feel.
You cover Malayalam, Hindi, Tamil, Telugu and English films and know where they stream in India.

How you work:
1. Read the user's words closely. A first-pass mood reading from our classifier is provided - refine it:
   primary + secondary emotion, energy (low/medium/high), and whether they want to STAY in the mood
   (e.g. a sad film when sad) or SHIFT it (something uplifting). Note company, time, language and anything to avoid.
2. If - and only if - the stay/shift goal is genuinely unclear AND you have not asked before in this chat,
   call ask_followup with ONE short, friendly question (offer 2-4 quick options). Never interrogate.
3. Otherwise call search_movies with a vivid mood_query (tones + themes, e.g. "warm, gentle, funny film about
   friendship and second chances") and filters for language / avoid / max_runtime / energy / goal.
4. Pick 3-5 films ONLY from search results. Keep the set varied (the tool marks a safe pick, a hidden gem and
   a wildcard - keep those). Call get_watch_providers if the user asks where to watch.
5. Finish with the recommend tool: a 1-2 sentence warm intro, and for each pick a 1-2 sentence reason that
   quotes or echoes the user's own words ("You said you want something light after a long day - ...").

Tone: warm, empathetic, concise, lightly playful. Never clinical, never preachy.
Wellbeing: if the user seems to be in serious distress, be kind, keep picks gentle (nothing dark or violent)
and gently encourage reaching out to someone they trust or a helpline. Never diagnose.
Never invent movie ids, ratings or streaming services - only use tool results."""


def user_turn(text: str, profile: MoodProfile, user_id: str, asked_followup: bool) -> str:
    reading = {
        "primary": profile.primary, "secondary": profile.secondary, "intensity": profile.intensity,
        "energy": profile.energy, "goal": profile.goal, "context": profile.context.model_dump(),
        "suggested_tones": profile.target_tones, "distress": profile.distress,
    }
    return (
        f"User message: {text!r}\n\n"
        f"First-pass mood reading: {json.dumps(reading)}\n"
        f"user_id: {user_id}\n"
        f"Already asked a follow-up in this chat: {'yes - do not ask again, recommend now' if asked_followup else 'no'}"
    )


# Deterministic intros for the rule-based planner (and as LLM fallback copy).
INTROS: dict[tuple[str, str], str] = {
    ("tired", "shift"): "Long days deserve soft landings. Here's a cosy little lineup that won't ask much of you:",
    ("tired", "stay"): "Let's keep it slow and gentle tonight. A few quiet picks:",
    ("sad", "shift"): "Sending you a small cinematic hug. These should nudge the day somewhere brighter:",
    ("sad", "stay"): "Sometimes you just need a film that gets it. These sit with the feeling, gently:",
    ("heartbroken", "stay"): "Heartbreak is rough. Here are films that understand — tissues optional, but recommended:",
    ("heartbroken", "shift"): "No sappy love stories tonight — just momentum, laughs and a little hope:",
    ("lonely", "shift"): "You're in good company with these — warm films full of people who find each other:",
    ("lonely", "stay"): "Quiet, tender films for a quiet night in:",
    ("stressed", "shift"): "Deep breath. Here's some low-stakes comfort to help your brain unclench:",
    ("stressed", "stay"): "Let's channel that energy — gripping enough to take over your head for a couple of hours:",
    ("anxious", "shift"): "Let's keep things soft and safe. Gentle picks, zero jump scares:",
    ("anxious", "stay"): "Films that understand restless minds, handled gently:",
    ("angry", "stay"): "Let it out through someone else's fight — high-octane picks ahead:",
    ("angry", "shift"): "Let's cool things down with something light and easy:",
    ("scared", "shift"): "Let's swap the nerves for something cosy:",
    ("scared", "stay"): "Oh, you want to lean into it? Brave. Lights off, here you go:",
    ("bored", "shift"): "Boredom? Not on my watch. Here's a mix to wake things up:",
    ("curious", "stay"): "Brain snacks, coming right up. These will stay with you after the credits:",
    ("happy", "stay"): "Love that for you! Let's keep the good mood rolling:",
    ("happy", "shift"): "Feeling good enough to go somewhere deeper? Try these:",
    ("excited", "stay"): "Party mode activated 🎉 Crowd-pleasers, big laughs and bigger energy:",
    ("romantic", "stay"): "Date-night picks with just the right amount of swoon:",
    ("nostalgic", "stay"): "A little trip down memory lane:",
    ("calm", "stay"): "Easy, unhurried picks for a calm evening:",
}
DEFAULT_INTRO = "Here's a varied lineup — one of these should click:"
GENTLE_INTRO = "Whenever you're ready, here are a few gentle, comforting films — nothing heavy, nothing dark:"
UNCLEAR_INTRO = "I kept these somewhere in the middle — gentle, but not gloomy:"


def intro_for(profile: MoodProfile) -> str:
    if profile.distress != "none":
        return GENTLE_INTRO
    if profile.goal == "unclear":
        return UNCLEAR_INTRO
    return INTROS.get((profile.primary, profile.goal)) or INTROS.get((profile.primary, "stay")) or DEFAULT_INTRO


def followup_for(profile: MoodProfile) -> tuple[str, list[str]]:
    if profile.vague:
        return ("Happy to help! What kind of night is it?",
                ["Cosy & easy", "Make me laugh", "Something gripping", "Make me think"])
    feeling = {
        "sad": "a bit down", "heartbroken": "heartbroken", "lonely": "lonely", "stressed": "stressed",
        "anxious": "anxious", "angry": "frustrated", "scared": "uneasy",
    }.get(profile.primary, "that way")
    return (f"Got it — feeling {feeling}. Do you want something that sits with that feeling, "
            f"or something to lift you out of it?", ["Sit with it", "Lift me up"])
