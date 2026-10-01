"""The MoodReel agent: understand the mood, maybe ask one question, recommend.

Everything is exposed as an async stream of events so the API can forward it
as Server-Sent Events:

    session · status · mood · care · delta · question · recommendations · done

Two planners share the same tools:

* **LLM planner** - an instruct model drives a tool-calling loop (search, details,
  providers, history) and finishes with ``recommend`` / ``ask_followup``. Its output
  is validated (ids must come from search results, 3-5 picks, reasons trimmed).
* **Rule planner** - deterministic plan over the same tools. Used when no LLM is
  configured and as the fallback whenever the LLM errors or misbehaves.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from collections.abc import AsyncIterator
from typing import Any

from moodreel.agent import memory
from moodreel.agent.llm import LLM, LLMResponse
from moodreel.agent.memory import SessionState, SessionStore
from moodreel.agent.prompts import SYSTEM_PROMPT, followup_for, intro_for, user_turn
from moodreel.agent.ranking import Scored
from moodreel.agent.reasons import build_group_reason, build_reason, why_notes
from moodreel.agent.refine import detect_refinement
from moodreel.agent.tools import TERMINAL_TOOLS, TOOL_SCHEMAS, ToolBox
from moodreel.config import Settings, get_settings
from moodreel.emotion.classifier import EmotionClassifier, EmotionResult
from moodreel.emotion.lexicon import STATES
from moodreel.emotion.mood import CHIPS, analyze_mood, blend_group, request_matches, summarize
from moodreel.emotion.safety import GENTLE_AVOID, GENTLE_TONES, assess_distress, care_message
from moodreel.log import get_logger, log_step
from moodreel.schemas import LANGUAGE_NAMES as LANG_NAMES
from moodreel.schemas import (
    AgentReply,
    CareMessage,
    ChatRequest,
    GroupRequest,
    MoodProfile,
    Recommendation,
    SurpriseRequest,
    Why,
)
from moodreel.search.index import SearchIndex

logger = get_logger("agent")
Event = dict[str, Any]

SURPRISE_MOODS = [
    ["twisty", "thrilling", "quirky"],
    ["whimsical", "heartwarming", "funny"],
    ["epic", "adventurous", "energetic"],
    ["bittersweet", "romantic", "nostalgic"],
    ["mind-bending", "thought-provoking"],
    ["feel-good", "warm", "inspiring"],
]


def build_query(profile: MoodProfile) -> str:
    """Natural-language query for the vector index."""
    tones = ", ".join(profile.target_tones[:5]) or "well-loved"
    who = {
        "family": " to watch with family",
        "friends": " to watch with friends",
        "partner": " for a date night",
        "alone": "",
    }.get(profile.context.company, "")
    feeling = STATES[profile.primary].label if profile.primary in STATES else ""
    goal = {"shift": " and wants to feel better", "stay": " and wants to lean into it"}.get(
        profile.goal, ""
    )
    person = f" for someone feeling {feeling}{goal}" if feeling else ""
    return f"A {tones} film{who}{person}. {profile.key_phrase}".strip()


def _sanitize_reason(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    text = " ".join(sentences[:2])
    return text[:320]


class MoodReelAgent:
    def __init__(
        self,
        index: SearchIndex,
        classifier: EmotionClassifier,
        llm: LLM | None = None,
        sessions: SessionStore | None = None,
        settings: Settings | None = None,
        typing_delay: float = 0.012,
    ) -> None:
        self.index = index
        self.classifier = classifier
        self.llm = llm
        self.settings = settings or get_settings()
        self.sessions = sessions or SessionStore(self.settings.session_ttl_minutes)
        self.typing_delay = typing_delay

    # ------------------------------------------------------------------ helpers

    def _toolbox(
        self,
        user_id: str,
        profile: MoodProfile | None,
        exclude: set[int] | None = None,
        rng: random.Random | None = None,
    ) -> ToolBox:
        return ToolBox(
            self.index,
            self.classifier,
            user_id,
            profile=profile,
            exclude=set(exclude or ()),
            rng=rng,
        )

    async def _type(self, text: str) -> AsyncIterator[Event]:
        """Stream text in small chunks so the UI can render a typing effect."""
        words = re.findall(r"\S+\s*", text)
        for i in range(0, len(words), 3):
            yield {"type": "delta", "text": "".join(words[i : i + 3])}
            if self.typing_delay:
                await asyncio.sleep(self.typing_delay)

    def _recommendation(self, s: Scored, profile: MoodProfile, reason: str) -> Recommendation:
        return Recommendation(
            movie=s.movie,
            reason=reason,
            slot=s.slot,
            why=Why(
                matched_tones=s.matched,
                mood_goal=profile.goal,
                score=round(s.score, 3),
                notes=why_notes(profile, s.slot, s.notes),
            ),
        )

    @staticmethod
    def _apply_distress(profile: MoodProfile, level: str) -> None:
        profile.distress = level  # type: ignore[assignment]
        if level != "none":
            profile.goal = "shift"
            profile.target_tones = list(dict.fromkeys(GENTLE_TONES + profile.target_tones))[:7]
            profile.context.avoid = sorted(set(profile.context.avoid) | set(GENTLE_AVOID))
            profile.summary = summarize(profile)

    # --------------------------------------------------------------- main chat

    async def stream(self, req: ChatRequest) -> AsyncIterator[Event]:
        session = self.sessions.get(req.session_id, req.user_id)
        yield {"type": "session", "session_id": session.id}
        text = req.message.strip() or (CHIPS[req.chip]["text"] if req.chip in CHIPS else "")
        if not text:
            text = "surprise me"
        session.add("user", text)
        yield {"type": "status", "text": "Reading your mood…"}

        distress = assess_distress(text)
        emotion_raw = self._toolbox(req.user_id, None).call("detect_emotion", {"text": text})
        emotion = EmotionResult(emotion_raw["scores"], emotion_raw["states"], emotion_raw["source"])

        refinement = detect_refinement(text, session.last_profile) if not req.chip else None
        exclude: set[int] = set()
        if refinement and sum(emotion.states.values()) < 1.0:
            profile = refinement.profile
            exclude = set(session.shown_ids)
            if refinement.mark_seen:
                for movie_id in session.shown_ids[-5:]:
                    memory.save_feedback(req.user_id, movie_id, "seen")
            log_step(logger, "refine", notes=refinement.notes)
        else:
            profile = analyze_mood(
                text,
                emotion,
                chip=req.chip,
                energy_slider=req.energy,
                shift_slider=req.mood_shift,
                languages=req.languages,
                prior=session.pending_profile,
            )
            refinement = None
        if req.languages:
            profile.context.languages = list(req.languages)
        self._apply_distress(profile, distress)
        log_step(
            logger,
            "mood",
            summary=profile.summary,
            tones=profile.target_tones,
            ctx=profile.context.model_dump(),
        )
        yield {"type": "mood", "mood": profile.model_dump()}

        care = care_message(distress)
        if care:
            yield {"type": "care", "care": care.model_dump()}

        needs_question = (
            not session.asked_followup
            and refinement is None
            and distress == "none"
            and (profile.goal == "unclear" or profile.vague)
            and req.mood_shift is None
        )
        if needs_question and self.llm is None:
            async for ev in self._ask(session, *followup_for(profile), profile=profile):
                yield ev
            return

        yield {"type": "status", "text": "Finding films that fit…"}
        n = 3 if distress != "none" else self.settings.default_recommendations
        result: tuple[str, list[Recommendation], MoodProfile, list[str]] | None = None
        engine = "rules"
        if self.llm is not None:
            try:
                llm_out = await self._llm_plan(text, profile, session, req.user_id, exclude, n)
            except Exception as exc:  # network/model failure -> graceful fallback
                logger.warning("LLM planner failed (%s); falling back to rules", exc)
                llm_out = None
            if llm_out and llm_out[0] == "question":
                _, question, options = llm_out
                async for ev in self._ask(session, question, options, profile=profile):
                    yield ev
                return
            if llm_out:
                result = llm_out[1]
                engine = "llm"
        if result is None:
            result = self._rule_plan(profile, req.user_id, exclude, n)
        message, recs, profile, steps = result
        if engine == "llm":  # the model may have refined the mood reading
            yield {"type": "mood", "mood": profile.model_dump()}
        if refinement and refinement.notes:
            message = f"Okay — {', '.join(refinement.notes)}. " + message
        async for ev in self._finish(
            session,
            req.user_id,
            text,
            profile,
            message,
            recs,
            steps,
            engine,
            log=refinement is None,
        ):
            yield ev

    async def _ask(
        self, session: SessionState, question: str, options: list[str], profile: MoodProfile
    ) -> AsyncIterator[Event]:
        session.asked_followup = True
        session.pending_profile = profile
        session.add("assistant", question)
        log_step(logger, "followup", question=question)
        async for ev in self._type(question):
            yield ev
        yield {"type": "question", "text": question, "options": options}
        yield {
            "type": "done",
            "engine": "rules" if self.llm is None else "llm",
            "steps": ["ask_followup"],
        }

    async def _finish(
        self,
        session: SessionState,
        user_id: str,
        text: str,
        profile: MoodProfile,
        message: str,
        recs: list[Recommendation],
        steps: list[str],
        engine: str,
        log: bool = True,
    ) -> AsyncIterator[Event]:
        session.pending_profile = None
        session.last_profile = profile
        session.shown_ids.extend(r.movie.id for r in recs)
        session.add("assistant", message + " " + "; ".join(r.movie.title for r in recs))
        if log and profile.primary != "neutral":
            memory.log_mood(user_id, profile, text)
        async for ev in self._type(message):
            yield ev
        yield {"type": "recommendations", "items": [r.model_dump() for r in recs]}
        log_step(
            logger, "recommend", engine=engine, picks=[f"{r.slot}:{r.movie.title}" for r in recs]
        )
        yield {"type": "done", "engine": engine, "steps": steps}

    # ------------------------------------------------------------ rule planner

    def _rule_plan(
        self,
        profile: MoodProfile,
        user_id: str,
        exclude: set[int],
        n: int,
        rng: random.Random | None = None,
    ) -> tuple[str, list[Recommendation], MoodProfile, list[str]]:
        box = self._toolbox(user_id, profile, exclude, rng)
        history = box.call("get_user_history", {"user_id": user_id})
        box.exclude |= set(history.get("seen", [])) | set(history.get("disliked", []))
        found = box.call(
            "search_movies", {"mood_query": build_query(profile), "filters": {"limit": n}}
        )
        picks: list[Scored] = found.get("_scored", [])
        recs = []
        for i, s in enumerate(picks):
            box.call(
                "get_watch_providers", {"movie_id": s.movie.id, "region": self.settings.region}
            )
            recs.append(
                self._recommendation(
                    s, profile, build_reason(s.movie, profile, s.slot, s.matched, i)
                )
            )
        message = intro_for(profile)
        unmet = [
            t
            for t in profile.requested_tones
            if recs and not any(request_matches([t], r.movie.tones) for r in recs)
        ]
        if unmet:
            langs = "/".join(LANG_NAMES.get(c, c) for c in profile.context.languages)
            asked = " or ".join(unmet[:2])
            message = (
                f"Honest heads-up: I couldn't find a {langs + ' ' if langs else ''}{asked} film that fits "
                f"all your filters, so these are the closest matches. Want me to loosen something?"
            )
        if found.get("relaxed"):
            message += f" (Heads up: {'; '.join(found['relaxed'])}.)"
        if not recs:
            message = "Hmm, I couldn't find anything that fits all of that. Want to loosen a filter or two?"
        return message, recs, profile, box.steps

    # ------------------------------------------------------------- LLM planner

    async def _llm_plan(
        self,
        text: str,
        profile: MoodProfile,
        session: SessionState,
        user_id: str,
        exclude: set[int],
        n: int,
    ) -> tuple | None:
        assert self.llm is not None
        box = self._toolbox(user_id, profile, exclude)
        history = box.call("get_user_history", {"user_id": user_id})
        box.exclude |= set(history.get("seen", [])) | set(history.get("disliked", []))
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += session.history[-7:-1]
        messages.append(
            {"role": "user", "content": user_turn(text, profile, user_id, session.asked_followup)}
        )

        for step in range(self.settings.agent_max_steps):
            resp: LLMResponse = await self.llm.chat(messages, TOOL_SCHEMAS)
            log_step(
                logger,
                f"llm:step{step}",
                content=resp.content[:120],
                calls=[c.name for c in resp.tool_calls],
            )
            if not resp.tool_calls:
                messages.append({"role": "assistant", "content": resp.content})
                messages.append(
                    {
                        "role": "user",
                        "content": "Please call search_movies, then finish with the recommend tool.",
                    }
                )
                continue
            messages.append(
                {
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.name, "arguments": c.arguments},
                        }
                        for c in resp.tool_calls
                    ],
                }
            )
            for call in resp.tool_calls:
                if call.name == "ask_followup":
                    if session.asked_followup or profile.distress != "none":
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": call.name,
                                "content": "Not allowed: already asked. Recommend now.",
                            }
                        )
                        continue
                    question = str(call.arguments.get("question", "")).strip()[:200]
                    options = [str(o)[:40] for o in call.arguments.get("options", [])][:4]
                    if question:
                        return ("question", question, options)
                if call.name == "recommend":
                    final = self._validate_llm_recommend(call.arguments, profile, box, n)
                    if final:
                        return ("recommend", final)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.name,
                            "content": "Invalid: pick 3-5 movie_ids from search_movies results.",
                        }
                    )
                    continue
                if call.name in TERMINAL_TOOLS:
                    continue
                result = box.call(call.name, call.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": ToolBox.for_llm(result),
                    }
                )
        log_step(logger, "llm:exhausted", steps=self.settings.agent_max_steps)
        return None

    def _validate_llm_recommend(
        self, args: dict[str, Any], profile: MoodProfile, box: ToolBox, n: int
    ) -> tuple[str, list[Recommendation], MoodProfile, list[str]] | None:
        # Let the LLM's nuanced reading refine the profile (only valid values).
        mood = args.get("mood") or {}
        if isinstance(mood, str):
            try:
                mood = json.loads(mood)
            except json.JSONDecodeError:
                mood = {}
        for key, allowed in (
            ("primary", STATES),
            ("secondary", STATES),
            ("energy", ("low", "medium", "high")),
            ("goal", ("stay", "shift")),
        ):
            if mood.get(key) in allowed and profile.distress == "none":
                setattr(profile, key, mood[key])
        profile.summary = summarize(profile)

        chosen: list[tuple[Scored, str]] = []
        for pick in args.get("picks") or []:
            try:
                movie_id = int(pick.get("movie_id"))
            except (TypeError, ValueError, AttributeError):
                continue
            scored = box.seen_candidates.get(movie_id)
            if scored and all(movie_id != c.movie.id for c, _ in chosen):
                chosen.append((scored, _sanitize_reason(pick.get("reason", ""))))
        if not box.seen_candidates:
            return None
        # Respect the model's 3-5 picks; top up from search results only if it chose too few.
        for scored in box.seen_candidates.values():
            if len(chosen) >= 3:
                break
            if all(scored.movie.id != c.movie.id for c, _ in chosen):
                chosen.append((scored, ""))
        chosen = chosen[:5]
        recs = [
            self._recommendation(
                s, profile, reason or build_reason(s.movie, profile, s.slot, s.matched, i)
            )
            for i, (s, reason) in enumerate(chosen)
        ]
        message = _sanitize_reason(args.get("message", "")) or intro_for(profile)
        return message, recs, profile, box.steps

    # ------------------------------------------------------------- group mode

    async def stream_group(self, req: GroupRequest) -> AsyncIterator[Event]:
        session = self.sessions.get(req.session_id, req.user_id)
        yield {"type": "session", "session_id": session.id}
        yield {"type": "status", "text": "Blending everyone's moods…"}
        members: list[tuple[str, MoodProfile]] = []
        worst = "none"
        for m in req.members:
            emo = self.classifier.detect(m.mood)
            prof = analyze_mood(m.mood, emo, languages=req.languages)
            level = assess_distress(m.mood)
            if ["none", "elevated", "crisis"].index(level) > ["none", "elevated", "crisis"].index(
                worst
            ):
                worst = level
            members.append((m.name.strip(), prof))
        group = blend_group(members)
        if req.languages:
            group.context.languages = list(req.languages)
        self._apply_distress(group, worst)
        session.add("user", "Group: " + "; ".join(f"{m.name}: {m.mood}" for m in req.members))
        yield {
            "type": "mood",
            "mood": group.model_dump(),
            "members": [{"name": n, "mood": p.model_dump()} for n, p in members],
        }
        care = care_message(worst)
        if care:
            yield {"type": "care", "care": care.model_dump()}

        box = self._toolbox(req.user_id, group)
        history = box.call("get_user_history", {"user_id": req.user_id})
        box.exclude |= set(history.get("disliked", []))
        found = box.call(
            "search_movies", {"mood_query": build_query(group), "filters": {"limit": 4}}
        )
        recs = [
            self._recommendation(s, group, build_group_reason(s.movie, members, s.matched, i))
            for i, s in enumerate(found.get("_scored", []))
        ]
        names = [n for n, _ in members]
        who = ", ".join(names[:-1]) + f" and {names[-1]}"
        message = f"Movie night for {who}! I blended everyone's moods — here's what should work for the whole room:"
        async for ev in self._finish(
            session, req.user_id, "group", group, message, recs, box.steps, "rules", log=False
        ):
            yield ev

    # ------------------------------------------------------------ surprise me

    async def stream_surprise(
        self, req: SurpriseRequest, seed: int | None = None
    ) -> AsyncIterator[Event]:
        session = self.sessions.get(req.session_id, req.user_id)
        yield {"type": "session", "session_id": session.id}
        rng = random.Random(seed)
        history = memory.get_user_history(req.user_id)
        liked = [
            t for t, w in sorted(history["tone_affinity"].items(), key=lambda kv: -kv[1]) if w > 0
        ][:2]
        tones = list(dict.fromkeys(liked + rng.choice(SURPRISE_MOODS)))
        profile = MoodProfile(
            primary="neutral", goal="stay", target_tones=tones, summary="feeling adventurous 🎲"
        )
        profile.context.languages = list(req.languages)
        box = self._toolbox(req.user_id, profile, set(session.shown_ids), rng)
        box.history = history
        box.exclude |= set(history["seen"]) | set(history["disliked"])
        found = box.call("search_movies", {"mood_query": ", ".join(tones), "filters": {"limit": 4}})
        recs = []
        loved = history.get("loved_titles") or []
        for i, s in enumerate(found.get("_scored", [])):
            tone = ", ".join(s.matched[:2] or s.movie.tones[:2])
            if loved and i == 0:
                reason = (
                    f"Because you loved {loved[-1]}: {s.movie.title} has that same {tone} streak."
                )
            else:
                reason = f"Pure wildcard energy — {s.movie.title} is {tone} and a {s.movie.language_name} favourite worth a spin."
            recs.append(self._recommendation(s, profile, reason))
        yield {"type": "mood", "mood": profile.model_dump()}
        async for ev in self._finish(
            session,
            req.user_id,
            "surprise",
            profile,
            "Surprise! 🎲 A little something from every corner of the map:",
            recs,
            box.steps,
            "rules",
            log=False,
        ):
            yield ev

    # ------------------------------------------------------- non-streaming API

    @staticmethod
    async def collect(events: AsyncIterator[Event]) -> AgentReply:
        reply = AgentReply(session_id="", message="")
        async for ev in events:
            kind = ev["type"]
            if kind == "session":
                reply.session_id = ev["session_id"]
            elif kind == "mood":
                reply.mood = MoodProfile(**ev["mood"])
            elif kind == "care":
                reply.care = CareMessage(**ev["care"])
            elif kind == "delta":
                reply.message += ev["text"]
            elif kind == "question":
                reply.question, reply.options = ev["text"], ev["options"]
            elif kind == "recommendations":
                reply.recommendations = [Recommendation(**r) for r in ev["items"]]
            elif kind == "done":
                reply.engine, reply.steps = ev["engine"], ev["steps"]
        reply.message = reply.message.strip()
        return reply
