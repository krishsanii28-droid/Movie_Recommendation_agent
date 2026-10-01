"""Emotion classifier: Hugging Face model with a lexicon fallback.

The HF model (``j-hartmann/emotion-english-distilroberta-base``) returns scores
for anger, disgust, fear, joy, neutral, sadness, surprise. We blend those with
the lexicon, which also yields nuanced states (tired, lonely, heartbroken...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from moodreel.config import Settings, get_settings
from moodreel.emotion.lexicon import BASE_EMOTIONS, lexicon_emotions
from moodreel.log import get_logger

logger = get_logger("emotion")

BASE_TO_STATE = {
    "joy": "happy",
    "sadness": "sad",
    "anger": "angry",
    "fear": "anxious",
    "surprise": "curious",
    "disgust": "angry",
    "neutral": "neutral",
}


@dataclass
class EmotionResult:
    scores: dict[str, float]  # base emotions, sums to ~1
    states: dict[str, float] = field(default_factory=dict)  # nuanced states -> weight
    source: str = "lexicon"

    @property
    def top(self) -> str:
        return max(self.scores, key=self.scores.get)  # type: ignore[arg-type]

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "states": self.states,
            "top": self.top,
            "source": self.source,
        }


class _Backend(Protocol):
    def __call__(self, text: str) -> dict[str, float]: ...


class HFEmotionBackend:
    def __init__(self, model: str, token: str | None = None) -> None:
        from transformers import pipeline  # heavy import

        self._pipe = pipeline("text-classification", model=model, top_k=None, token=token or None)

    def __call__(self, text: str) -> dict[str, float]:
        out = self._pipe(text[:512])
        rows = out[0] if out and isinstance(out[0], list) else out
        return {r["label"].lower(): float(r["score"]) for r in rows}


class EmotionClassifier:
    def __init__(self, backend: _Backend | None = None, name: str = "lexicon") -> None:
        self._backend = backend
        self.name = name

    def detect(self, text: str) -> EmotionResult:
        lex_scores, states = lexicon_emotions(text)
        if self._backend is None or not text.strip():
            return EmotionResult(lex_scores, states, "lexicon")
        try:
            hf = self._backend(text)
        except Exception as exc:  # model hiccup -> degrade gracefully
            logger.warning("HF emotion model failed (%s); lexicon only", exc)
            return EmotionResult(lex_scores, states, "lexicon")
        # Lexicon hits carry nuance / Indian phrasing; weight them in when present.
        w = 0.4 if states else 0.0
        scores = {
            e: round((1 - w) * hf.get(e, 0.0) + w * lex_scores.get(e, 0.0), 4)
            for e in BASE_EMOTIONS
        }
        if not states:
            top = max(scores, key=scores.get)  # type: ignore[arg-type]
            if top != "neutral" and scores[top] > 0.45:
                states = {BASE_TO_STATE[top]: round(scores[top], 2)}
        return EmotionResult(scores, states, "hf+lexicon")


_CLASSIFIER: EmotionClassifier | None = None


def get_classifier(settings: Settings | None = None) -> EmotionClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is not None:
        return _CLASSIFIER
    settings = settings or get_settings()
    if settings.emotion_backend in ("auto", "hf"):
        try:
            backend = HFEmotionBackend(settings.emotion_model, settings.hf_token)
            _CLASSIFIER = EmotionClassifier(backend, name=settings.emotion_model)
            logger.info("using HF emotion model %s", settings.emotion_model)
            return _CLASSIFIER
        except Exception as exc:
            if settings.emotion_backend == "hf":
                raise
            logger.warning("HF emotion model unavailable (%s); using lexicon", exc)
    _CLASSIFIER = EmotionClassifier()
    return _CLASSIFIER
