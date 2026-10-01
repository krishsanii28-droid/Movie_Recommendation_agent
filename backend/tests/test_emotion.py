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


@pytest.mark.parametrize(
    "text,goal",
    [
        ("I'm sad, cheer me up", "shift"),
        ("I'm sad and just want a good cry", "stay"),
        ("heartbroken", "unclear"),
        ("in a great mood!", "stay"),
        ("long day, want something cosy", "shift"),
    ],
)
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


@pytest.mark.parametrize(
    "text,level",
    [
        ("I want to die", "crisis"),
        ("i feel hopeless and worthless", "elevated"),
        ("sad day at work", "none"),
        ("this movie will kill me with laughter", "none"),
    ],
)
def test_distress(text, level):
    assert assess_distress(text) == level


def test_care_message():
    assert care_message("none") is None
    msg = care_message("crisis")
    assert "14416" in str(msg.helplines) and "112" in msg.text


# --- Stage 2 regressions ---------------------------------------------------------


def test_explicit_request_decides_goal():
    p = analyze("Scared of the dark but I want a horror movie tonight, bring it on")
    assert p.goal == "stay" and p.target_tones[0] == "scary"
    assert analyze("so stressed, need something inspiring").goal == "shift"


def test_anything_but_and_except_are_negations():
    assert "horror" in analyze("anything but horror").context.avoid
    assert "horror" in analyze("any genre except horror").context.avoid
    assert "scary" not in analyze("anything but horror").requested_tones


def test_gore_is_not_all_violence():
    ctx = analyze("Tamil thriller, no gore").context
    assert "gore" in ctx.avoid and "violence" not in ctx.avoid


def test_kid_safe_cues_avoid_violence_and_horror():
    for text in ("something for the kids", "wholesome family night", "an animated movie"):
        assert {"violence", "horror"} <= set(analyze(text).context.avoid), text


@pytest.mark.parametrize(
    "text,minutes",
    [
        ("Need a 2-hour max thriller", 120),
        ("only two hours", 120),
        ("about 1.5 hrs", 90),
        ("90 minutes", 90),
    ],
)
def test_time_parsing(text, minutes):
    assert analyze(text).context.time_available == minutes


def test_group_keeps_explicit_requests_unless_someone_vetoes():
    joe = analyze("something scary!")
    ammu = analyze("Malayalam only")
    assert "scary" in blend_group([("Joe", joe), ("Ammu", ammu)]).requested_tones
    veto = analyze("no horror please")
    assert "scary" not in blend_group([("Joe", joe), ("Sam", veto)]).requested_tones


def test_light_requests_clash_with_heavy_tones():
    from moodreel.emotion.mood import clash_tones

    assert "hard-hitting" in clash_tones("neutral", "stay", [], ["light"])
    assert "scary" not in clash_tones(
        "scared", "shift", [], ["scary"]
    )  # never penalise an explicit ask


@pytest.mark.parametrize("text", ["I don't want to be here anymore", "there's no point in living"])
def test_passive_ideation_is_crisis(text):
    assert assess_distress(text) == "crisis"


def test_grief_and_anxiety_vocabulary():
    assert analyze("my dog died last week").primary == "sad"
    assert analyze("can't sleep, mind racing about my interview").primary == "anxious"
