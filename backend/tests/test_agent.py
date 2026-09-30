"""Integration tests for the agent loop (rule planner and LLM planner with a scripted fake LLM)."""

import pytest

from moodreel.agent.agent import MoodReelAgent, build_query
from moodreel.agent.llm import LLMResponse, ToolCall, parse_tool_calls
from moodreel.emotion.classifier import EmotionClassifier
from moodreel.schemas import ChatRequest, GroupMember, GroupRequest, SurpriseRequest


@pytest.fixture()
def agent(search_index):
    return MoodReelAgent(search_index, EmotionClassifier(), llm=None, typing_delay=0)


async def chat(agent, text, user="u-agent", session=None, **kw):
    return await agent.collect(agent.stream(ChatRequest(user_id=user, session_id=session, message=text, **kw)))


async def test_rule_agent_recommends_with_reasons(agent):
    reply = await chat(agent, "Long day, want something cosy but not cheesy")
    assert reply.session_id and reply.engine == "rules"
    assert 3 <= len(reply.recommendations) <= 5
    assert reply.mood.primary == "tired" and reply.mood.goal == "shift"
    first = reply.recommendations[0]
    assert "long day" in first.reason.lower()
    assert all(r.reason and r.movie.providers.link for r in reply.recommendations)
    assert len({r.slot for r in reply.recommendations}) >= 3
    assert "search_movies" in " ".join(reply.steps)


async def test_asks_at_most_one_followup(agent):
    first = await chat(agent, "I got dumped today", user="u-follow")
    assert first.question and first.options and not first.recommendations
    second = await chat(agent, "Lift me up", user="u-follow", session=first.session_id)
    assert second.recommendations and not second.question
    assert second.mood.goal == "shift" and second.mood.primary == "heartbroken"
    assert "dumped" in second.recommendations[0].reason  # still echoes the original words
    for r in second.recommendations:
        assert "romantic" not in r.why.matched_tones
    # a new unclear mood in the same session does not trigger a second question
    third = await chat(agent, "now I'm sad", user="u-follow", session=first.session_id)
    assert third.recommendations and not third.question


async def test_slider_skips_question(agent):
    reply = await chat(agent, "I'm sad", user="u-slider", mood_shift=-1.0)
    assert reply.recommendations and reply.mood.goal == "stay"


async def test_chip_only_start(agent):
    reply = await agent.collect(agent.stream(ChatRequest(user_id="u-chip", chip="party")))
    assert reply.mood.primary == "excited" and reply.recommendations


async def test_language_filter_and_refinement(agent):
    first = await chat(agent, "want a laugh", user="u-lang", languages=["ml"])
    assert all(r.movie.language == "ml" for r in first.recommendations)
    shown = {r.movie.id for r in first.recommendations}
    more = await chat(agent, "seen them, something else", user="u-lang", session=first.session_id, languages=["ml"])
    assert more.recommendations and not shown & {r.movie.id for r in more.recommendations}
    assert more.message.startswith("Okay")


async def test_distress_gets_care_and_gentle_picks(agent, search_index):
    reply = await chat(agent, "honestly I feel hopeless and I can't go on", user="u-care")
    assert reply.care and reply.care.helplines
    assert not reply.question
    assert len(reply.recommendations) == 3
    for r in reply.recommendations:
        assert not {"horror", "violence", "heavy"} & set(r.movie.content_flags)


async def test_feedback_memory_excludes_seen_across_sessions(agent):
    first = await chat(agent, "in a great mood, want something fun", user="u-mem")
    seen_id = first.recommendations[0].movie.id
    from moodreel.agent import memory

    memory.save_feedback("u-mem", seen_id, "seen")
    again = await chat(agent, "in a great mood, want something fun", user="u-mem")  # new session
    assert seen_id not in {r.movie.id for r in again.recommendations}


async def test_group_mode(agent):
    req = GroupRequest(user_id="u-group", members=[
        GroupMember(name="Asha", mood="exhausted after work"),
        GroupMember(name="Ravi", mood="want to laugh, no horror"),
        GroupMember(name="Meera", mood="happy, Malayalam or Hindi"),
    ])
    reply = await agent.collect(agent.stream_group(req))
    assert reply.recommendations and "Asha" in reply.message
    assert "horror" in reply.mood.context.avoid
    assert all("Asha" in r.reason for r in reply.recommendations)


async def test_surprise(agent):
    reply = await agent.collect(agent.stream_surprise(SurpriseRequest(user_id="u-surprise"), seed=7))
    assert len(reply.recommendations) >= 3 and "Surprise" in reply.message


def test_build_query_is_natural_language(agent):
    from moodreel.schemas import MoodProfile

    q = build_query(MoodProfile(primary="tired", goal="shift", target_tones=["cosy", "funny"], key_phrase="long day"))
    assert q.startswith("A cosy, funny film") and "drained" in q and "long day" in q


# --------------------------------------------------------------------- LLM loop


class ScriptedLLM:
    """Plays back a fixed sequence of responses; can reference ids found by search."""

    name = "scripted"

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def chat(self, messages, tools):
        self.calls.append(messages)
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def _pick_from_search(messages):
    import json

    tool_msgs = [m for m in messages if m.get("role") == "tool" and m.get("name") == "search_movies"]
    results = json.loads(tool_msgs[-1]["content"])["results"]
    picks = [{"movie_id": r["movie_id"], "reason": f"You said long day — {r['title']} is gentle. Extra sentence. Third sentence dropped."} for r in results[:3]]
    picks.append({"movie_id": 123456789, "reason": "hallucinated id"})
    return LLMResponse(tool_calls=[ToolCall("recommend", {
        "message": "Soft landing incoming.", "picks": picks,
        "mood": {"primary": "tired", "secondary": "lonely", "energy": "low", "goal": "shift"},
    })])


async def test_llm_agent_tool_loop(search_index):
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[ToolCall("detect_emotion", {"text": "long day"})]),
        LLMResponse(tool_calls=[ToolCall("search_movies", {"mood_query": "cosy gentle", "filters": {"limit": 4}})]),
        _pick_from_search,
    ])
    agent = MoodReelAgent(search_index, EmotionClassifier(), llm=llm, typing_delay=0)
    reply = await chat(agent, "long day, feeling kind of lonely", user="u-llm")
    assert reply.engine == "llm"
    assert reply.message == "Soft landing incoming."
    assert len(reply.recommendations) == 3  # hallucinated id dropped
    assert reply.mood.secondary == "lonely"
    assert all("Third sentence" not in r.reason for r in reply.recommendations)
    assert len(llm.calls) == 3
    tool_names = [m.get("name") for m in llm.calls[-1] if m.get("role") == "tool"]
    assert tool_names == ["detect_emotion", "search_movies"]


async def test_llm_followup_then_no_second_question(search_index):
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[ToolCall("ask_followup", {"question": "Sit with it or lift you up?", "options": ["Sit", "Lift"]})]),
        LLMResponse(tool_calls=[ToolCall("ask_followup", {"question": "Again?"})]),
        LLMResponse(tool_calls=[ToolCall("search_movies", {"mood_query": "uplifting"})]),
        _pick_from_search,
    ])
    agent = MoodReelAgent(search_index, EmotionClassifier(), llm=llm, typing_delay=0)
    first = await chat(agent, "rough day", user="u-llm2")
    assert first.question == "Sit with it or lift you up?"
    second = await chat(agent, "lift", user="u-llm2", session=first.session_id)
    assert second.recommendations and not second.question


async def test_llm_failure_falls_back_to_rules(search_index):
    class Broken:
        name = "broken"

        async def chat(self, messages, tools):
            raise ConnectionError("model offline")

    agent = MoodReelAgent(search_index, EmotionClassifier(), llm=Broken(), typing_delay=0)
    reply = await chat(agent, "happy and want something fun", user="u-broken")
    assert reply.engine == "rules" and reply.recommendations


async def test_llm_that_never_finishes_falls_back(search_index):
    llm = ScriptedLLM([LLMResponse(content="hmm let me think")] * 10)
    agent = MoodReelAgent(search_index, EmotionClassifier(), llm=llm, typing_delay=0)
    reply = await chat(agent, "in a great mood", user="u-chatty")
    assert reply.engine == "rules" and reply.recommendations


def test_parse_tool_calls_formats():
    text, calls = parse_tool_calls('Sure!<tool_call>\n{"name": "search_movies", "arguments": {"mood_query": "x"}}\n</tool_call>')
    assert text == "Sure!" and calls[0].name == "search_movies" and calls[0].arguments == {"mood_query": "x"}
    _, calls = parse_tool_calls('```json\n{"name": "get_movie_details", "arguments": {"movie_id": 5}}\n```')
    assert calls[0].arguments["movie_id"] == 5
    _, calls = parse_tool_calls('{"name": "recommend", "parameters": {"message": "hi"}}')
    assert calls[0].name == "recommend"
    text, calls = parse_tool_calls("just chatting")
    assert text == "just chatting" and calls == []
