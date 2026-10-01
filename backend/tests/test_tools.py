import random

from moodreel.agent import tools
from moodreel.agent.ranking import diversity_score, movie_similarity
from moodreel.agent.tools import ToolBox
from moodreel.emotion.classifier import EmotionClassifier
from moodreel.emotion.mood import analyze_mood
from moodreel.schemas import MoodContext, MoodProfile

clf = EmotionClassifier()


def profile_for(text: str, **kw) -> MoodProfile:
    return analyze_mood(text, clf.detect(text), **kw)


def test_detect_emotion_returns_base_scores_and_states():
    out = tools.detect_emotion(clf, "I'm so tired and lonely tonight")
    assert set(out["scores"]) >= {"joy", "sadness", "anger", "fear", "neutral"}
    assert abs(sum(out["scores"].values()) - 1) < 0.01
    assert {"tired", "lonely"} <= set(out["states"])
    assert out["top"] == "sadness"


def test_detect_emotion_understands_indian_phrasing():
    assert "tired" in tools.detect_emotion(clf, "thak gaya yaar")["states"]
    assert "bored" in tools.detect_emotion(clf, "bore adikkunnu")["states"]
    assert "sad" in tools.detect_emotion(clf, "mood off")["states"]
    assert "sad" in tools.detect_emotion(clf, "not happy today")["states"]


def test_search_movies_returns_diverse_slots(search_index):
    profile = profile_for("long day, want something cosy and funny")
    out = tools.search_movies(search_index, "cosy funny warm", {"limit": 4}, base_profile=profile)
    res = out["results"]
    assert len(res) == 4
    assert len({r["movie_id"] for r in res}) == 4
    slots = {r["slot"] for r in res}
    assert "Safe pick" in slots or "Top pick" in slots
    movies = [search_index.movies[r["movie_id"]] for r in res]
    assert diversity_score(movies) > 0.45
    assert any({"cosy", "funny", "light", "feel-good"} & set(m.tones) for m in movies)


def test_search_movies_respects_language_avoid_and_runtime(search_index):
    profile = profile_for("something thrilling")
    out = tools.search_movies(
        search_index,
        "tense thriller",
        {"languages": ["ml"], "avoid": ["violence", "horror"], "max_runtime": 140},
        base_profile=profile,
    )
    for r in out["results"]:
        m = search_index.movies[r["movie_id"]]
        assert m.language == "ml"
        assert not {"violence", "horror"} & set(m.content_flags)
        assert m.runtime <= 150


def test_search_movies_relaxes_impossible_constraints(search_index):
    profile = MoodProfile(context=MoodContext(languages=["te"], time_available=60))
    out = tools.search_movies(search_index, "anything", {}, base_profile=profile)
    assert len(out["results"]) >= 3
    assert out["relaxed"]


def test_search_excludes_ids(search_index):
    profile = profile_for("cosy")
    first = tools.search_movies(search_index, "cosy", {}, base_profile=profile)["results"]
    excl = {r["movie_id"] for r in first}
    second = tools.search_movies(search_index, "cosy", {}, base_profile=profile, exclude=excl)[
        "results"
    ]
    assert not excl & {r["movie_id"] for r in second}


def test_distress_keeps_recommendations_gentle(search_index):
    profile = profile_for("sad")
    profile.distress = "crisis"
    res = tools.search_movies(search_index, "sad", {}, base_profile=profile)["results"]
    for r in res:
        assert not {"horror", "violence", "heavy"} & set(
            search_index.movies[r["movie_id"]].content_flags
        )


def test_movie_details_and_providers(search_index):
    movie_id = next(iter(search_index.movies))
    details = tools.get_movie_details(search_index, movie_id)
    assert details["id"] == movie_id and "providers" not in details
    prov = tools.get_watch_providers(search_index, movie_id)
    assert prov["region"] == "IN" and "stream" in prov
    assert tools.get_movie_details(search_index, -1)["error"]
    assert "note" in tools.get_watch_providers(search_index, movie_id, region="US")


def test_feedback_updates_history_and_taste(search_index):
    user = "test-user-feedback"
    comedy = next(m for m in search_index.movies.values() if "funny" in m.tones)
    slow = next(m for m in search_index.movies.values() if "slow-burn" in m.tones)
    assert tools.save_feedback(user, comedy.id, "loved")["ok"]
    assert tools.save_feedback(user, slow.id, "too_slow")["ok"]
    assert "error" in tools.save_feedback(user, slow.id, "meh")
    hist = tools.get_user_history(user)
    assert comedy.id in hist["loved"] and comedy.id in hist["seen"]
    assert hist["tone_affinity"]["funny"] > 0
    assert hist["tone_affinity"]["slow-burn"] < 0


def test_toolbox_logs_steps_and_handles_errors(search_index):
    box = ToolBox(
        search_index, clf, user_id="u1", profile=profile_for("happy"), rng=random.Random(1)
    )
    out = box.call("search_movies", {"mood_query": "feel-good"})
    assert out["results"] and box.seen_candidates
    assert "_scored" not in ToolBox.for_llm(out)
    assert "error" in box.call("get_movie_details", {})
    assert "error" in box.call("nope", {})
    assert len(box.steps) == 3


def test_movie_similarity_bounds(search_index):
    a, b = list(search_index.movies.values())[:2]
    assert movie_similarity(a, a) == 1.0
    assert 0 <= movie_similarity(a, b) <= 1
