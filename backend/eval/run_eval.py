"""Offline evaluation of MoodReel on 30 diverse mood prompts.

Scores (0-1, higher is better):

* understanding  - primary emotion / goal / company read correctly
* relevance      - share of picks whose tones match the expected tones for the mood,
                   with hard constraints (language, avoid, runtime) as a gate
* constraints    - share of picks that respect language / avoid / runtime constraints
* diversity      - 1 - mean pairwise similarity (genres, tones, language) of the set
* reason quality - heuristics: echoes the user's words or mood, 1-2 sentences of sane length,
                   names a concrete tone/genre, not clinical, not repetitive within the set
* behaviour      - follow-up asked when (and only when) expected, care shown on distress

Usage (from backend/):  python -m eval.run_eval [--out eval/results.md]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from pathlib import Path

os.environ.setdefault("LOG_LEVEL", "WARNING")

from moodreel.agent.agent import MoodReelAgent  # noqa: E402
from moodreel.agent.ranking import HEAVY_TONES, diversity_score  # noqa: E402
from moodreel.schemas import AgentReply, ChatRequest, GroupMember, GroupRequest  # noqa: E402

HERE = Path(__file__).parent
CLINICAL = re.compile(r"\b(diagnos\w*|disorder|symptom\w*|patient|clinical|therapy session|medicat\w*)\b", re.I)
STOP = set("a an the and or but i im i'm to of in on for with my me it is something want some just".split())


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']{3,}", text.lower()) if w not in STOP}


def reason_quality(reply: AgentReply, prompt_text: str) -> float:
    recs = reply.recommendations
    if not recs:
        return 0.0
    prompt_words = _words(prompt_text)
    openings = [r.reason.split(" ")[:4] for r in recs]
    scores = []
    for r in recs:
        text = r.reason
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
        vocab = _words(text)
        echoes = bool(prompt_words & vocab) or "you said" in text.lower() or "feeling" in text.lower() \
            or any(n.lower() in text.lower() for n in re.findall(r"[A-Z][a-z]+(?=:)", prompt_text))
        concrete = bool(set(r.movie.tones) & vocab) or any(g.lower() in text.lower() for g in r.movie.genres) \
            or any(t.split("-")[0] in text.lower() for t in r.movie.tones)
        checks = [
            echoes,
            1 <= len(sentences) <= 2 and 50 <= len(text) <= 340,
            concrete,
            not CLINICAL.search(text),
            openings.count(text.split(" ")[:4]) == 1,
            r.movie.title in text,
        ]
        scores.append(sum(checks) / len(checks))
    return round(statistics.mean(scores), 3)


def constraint_ok(movie, expect: dict, reply: AgentReply) -> bool:
    langs = expect.get("languages")
    if langs and movie.language not in langs and not expect.get("relaxed_ok"):
        return False
    flags = set(expect.get("avoid_flags", []))
    if flags & set(movie.content_flags):
        return False
    if "horror" in flags and "Horror" in movie.genres:
        return False
    if "heavy" in flags and len(HEAVY_TONES & set(movie.tones)) >= 2:
        return False
    if set(expect.get("avoid_tones", [])) & set(movie.tones):
        return False
    if expect.get("max_runtime") and movie.runtime and movie.runtime > expect["max_runtime"] + 10:
        return False
    return True


async def run_case(agent: MoodReelAgent, case: dict) -> dict:
    expect = case["expect"]
    user = f"eval-{case['id']}"
    asked = 0
    if "members" in case:
        members = [GroupMember(**m) for m in case["members"]]
        reply = await agent.collect(agent.stream_group(GroupRequest(user_id=user, members=members)))
        prompt_text = " ".join(f"{m.name}: {m.mood}" for m in members)
    else:
        prompt_text = case["prompt"]
        reply = await agent.collect(agent.stream(ChatRequest(user_id=user, message=prompt_text)))
        if reply.question:
            asked += 1
            answer = expect.get("answer") or (reply.options[-1] if reply.options else "anything")
            reply = await agent.collect(agent.stream(ChatRequest(user_id=user, session_id=reply.session_id, message=answer)))
            asked += int(bool(reply.question))

    movies = [r.movie for r in reply.recommendations]
    mood = reply.mood
    # understanding
    u_checks = []
    if "primary_any" in expect and mood:
        u_checks.append(mood.primary in expect["primary_any"] or (mood.secondary in expect["primary_any"]))
    if "goal" in expect and mood:
        u_checks.append(mood.goal == expect["goal"])
    if "company" in expect and mood:
        u_checks.append(mood.context.company == expect["company"])
    if "languages" in expect and mood and "members" not in case:
        u_checks.append(set(expect["languages"]) <= set(mood.context.languages))
    understanding = sum(u_checks) / len(u_checks) if u_checks else None

    ok = [constraint_ok(m, expect, reply) for m in movies]
    constraints = sum(ok) / len(ok) if ok else 0.0
    tones = set(expect.get("tones_any", []))
    rel = [bool(tones & set(m.tones)) and c for m, c in zip(movies, ok)]
    relevance = sum(rel) / len(rel) if rel else 0.0

    b_checks = [asked <= 1, 3 <= len(movies) <= 5]
    if "followup" in expect:
        b_checks.append((asked >= 1) == expect["followup"])
    if expect.get("care"):
        b_checks.append(reply.care is not None)
    behaviour = sum(b_checks) / len(b_checks)

    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": prompt_text,
        "mood": mood.summary if mood else "",
        "asked_followup": asked,
        "picks": [f"{m.title} ({m.language})" for m in movies],
        "slots": [r.slot for r in reply.recommendations],
        "understanding": understanding,
        "relevance": round(relevance, 3),
        "constraints": round(constraints, 3),
        "diversity": diversity_score(movies),
        "reason_quality": reason_quality(reply, prompt_text),
        "behaviour": round(behaviour, 3),
        "sample_reason": reply.recommendations[0].reason if reply.recommendations else "",
    }


def summarize(rows: list[dict]) -> dict:
    def mean(key: str, subset=None) -> float:
        vals = [r[key] for r in (subset or rows) if r[key] is not None]
        return round(statistics.mean(vals), 3) if vals else float("nan")

    metrics = ["understanding", "relevance", "constraints", "diversity", "reason_quality", "behaviour"]
    overall = {m: mean(m) for m in metrics}
    by_cat = {}
    for cat in sorted({r["category"] for r in rows}):
        subset = [r for r in rows if r["category"] == cat]
        by_cat[cat] = {"n": len(subset), **{m: mean(m, subset) for m in metrics}}
    return {"overall": overall, "by_category": by_cat, "n": len(rows)}


def to_markdown(summary: dict, rows: list[dict], engines: dict) -> str:
    metrics = ["understanding", "relevance", "constraints", "diversity", "reason_quality", "behaviour"]
    lines = ["# MoodReel evaluation results", "",
             f"{summary['n']} prompts · engines: " + ", ".join(f"{k}=`{v}`" for k, v in engines.items()), "",
             "| Metric | Score |", "|---|---|"]
    lines += [f"| {m.replace('_', ' ').title()} | {summary['overall'][m]:.2f} |" for m in metrics]
    lines += ["", "## By category", "", "| Category | n | " + " | ".join(m.replace("_", " ") for m in metrics) + " |",
              "|---|---|" + "---|" * len(metrics)]
    for cat, vals in summary["by_category"].items():
        lines.append(f"| {cat} | {vals['n']} | " + " | ".join(f"{vals[m]:.2f}" for m in metrics) + " |")
    lines += ["", "## Per prompt", "", "| id | prompt | understood as | picks | rel | div | reason |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        prompt = r["prompt"].replace("|", "/")[:70]
        lines.append(f"| {r['id']} | {prompt} | {r['mood']} | {'; '.join(r['picks'])} | {r['relevance']:.2f} | {r['diversity']:.2f} | {r['reason_quality']:.2f} |")
    lines += ["", "## Sample reasons", ""]
    for r in rows[:8]:
        lines.append(f"- **{r['id']}** “{r['prompt'][:60]}” → {r['sample_reason']}")
    return "\n".join(lines) + "\n"


async def main_async(out: Path) -> dict:
    from moodreel.services import get_agent

    agent = get_agent()
    agent.typing_delay = 0
    cases = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    rows = [await run_case(agent, c) for c in cases]
    summary = summarize(rows)
    engines = {
        "embedder": agent.index.embedder.name, "vectors": agent.index.store.name,
        "emotion": agent.classifier.name, "llm": agent.llm.name if agent.llm else "rules",
        "catalogue": f"{len(agent.index.movies)} films",
    }
    out.write_text(to_markdown(summary, rows, engines), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"summary": summary, "engines": engines, "rows": rows}, indent=1, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE / "results.md")
    parser.add_argument("--min-relevance", type=float, default=0.0, help="exit non-zero below this (CI gate)")
    args = parser.parse_args()
    summary = asyncio.run(main_async(args.out))
    print(json.dumps(summary["overall"], indent=2))
    for cat, vals in summary["by_category"].items():
        print(f"  {cat:9s} " + "  ".join(f"{k[:5]}={v:.2f}" for k, v in vals.items() if k != "n"))
    if summary["overall"]["relevance"] < args.min_relevance:
        sys.exit(1)


if __name__ == "__main__":
    main()
