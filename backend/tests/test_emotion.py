import pytest

from moodreel.emotion.classifier import EmotionClassifier
from moodreel.emotion.mood import analyze_mood, blend_group
from moodreel.emotion.safety import assess_distress, care_message

clf = EmotionClassifier()


def analyze(text, **kw):
    return analyze_mood(text, clf.detect(text), **kw)


def test_primary_and_secondary_emotions():
    p = analyze("so tired and kind of lonely tonight")
    assert {p.primary, p.secondary} == {"tired", "lonely"}
    assert p.energy == "low"


@pytest.mark.parametrize("text,goal", [
    ("I'm sad, cheer me up", "shift"),
    ("I'm sad and just want a good cry", "stay"),
    ("heartbroken", "unclear"),
    ("in a great mood!", "stay"),
    ("long day, want something cosy", "shift"),
])
def test_mood_goal(text, goal):
    assert analyze(text).goal == goal


def test_sliders_override_defaults():
    p = analyze("I feel sad", shift_slider=0.9, energy_slider=0.9)
    assert p.goal == "shift" and p.energy == "high"
    assert "uplifting" in p.target_tones


def test_context_parsing():
    p = analyze("watching with my parents, Malayalam or Tamil, nothing violent, about 2 hours")
    ctx = p.context
    assert ctx.company == "family"
    assert set(ctx.languages) == {"ml", "ta"}
    assert "violence" in ctx.avoid and "sexual content" in ctx.avoid
    assert ctx.time_available == 120


def test_negated_tone_requests_are_not_requested():
    p = analyze("no horror please, something funny")
    assert "horror" in p.context.avoid
    assert "scary" not in p.target_tones and "funny" in p.target_tones


def test_followup_answer_refines_prior():
    first = analyze("feeling low after a breakup")
    assert first.goal == "unclear"
    second = analyze("lift me up", prior=first)
    assert second.primary == first.primary and second.goal == "shift"
    assert "romantic" not in second.target_tones[:3]


def test_vague_input_flagged():
    assert analyze("idk").vague
    assert not analyze("idk, something funny").vague


def test_chip_sets_state():
    p = analyze("", chip="think")
    assert p.primary == "curious" and "mind-bending" in p.target_tones


def test_group_blend():
    a = analyze("exhausted, Malayalam please")
    b = analyze("I want to laugh, Malayalam or Hindi, no horror")
    g = blend_group([("Asha", a), ("Ravi", b)])
    assert g.context.languages == ["ml"]
    assert "horror" in g.context.avoid
    assert g.context.company == "friends"
    assert "Asha" in g.summary and "Ravi" in g.summary


@pytest.mark.parametrize("text,level", [
    ("I want to die", "crisis"),
    ("i feel hopeless and worthless", "elevated"),
    ("sad day at work", "none"),
    ("this movie will kill me with laughter", "none"),
])
def test_distress(text, level):
    assert assess_distress(text) == level


def test_care_message():
    assert care_message("none") is None
    msg = care_message("crisis")
    assert "14416" in str(msg.helplines) and "112" in msg.text
