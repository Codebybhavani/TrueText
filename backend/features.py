"""
Stylometric features, combined with TF-IDF in the model pipeline.

Relying on TF-IDF (word presence) alone makes a detector shortcut to
"contains the word 'furthermore' = AI", which breaks the moment real text
doesn't use those exact words. These numeric style signals — sentence length
uniformity, contraction use, vocabulary richness, function-word ratio, passive
voice — are the same signals real AI-detectors (GPTZero, etc.) lean on, and
they generalize far better to text the model has never seen.

IMPORTANT: this module must be importable under the same name at both
train time (train_model.py) and predict time (ml_model.py), because joblib
pickles a reference to "features.StyleFeatureExtractor", not the class body.
"""
import re
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

FORMAL_TRANSITIONS = [
    "furthermore", "moreover", "overall", "in conclusion", "however",
    "therefore", "additionally", "consequently", "significant role",
    "cannot be overstated", "it is important to note", "in summary",
    "as a result", "in addition", "on the other hand",
]

CONTRACTION_RE = re.compile(r"\b\w+'(?:t|re|ve|ll|d|s|m)\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)
PASSIVE_RE = re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", re.IGNORECASE)
SENT_SPLIT_RE = re.compile(r"[.!?]+")
WORD_RE = re.compile(r"[A-Za-z']+")


def _extract_one(text: str) -> list:
    text = text or ""
    sentences = [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]
    words = WORD_RE.findall(text)
    n_words = max(len(words), 1)
    n_sent = max(len(sentences), 1)

    sent_lengths = [len(WORD_RE.findall(s)) for s in sentences] or [n_words]
    avg_sent_len = float(np.mean(sent_lengths))
    burstiness = float(np.std(sent_lengths))  # low => uniform/robotic => AI-like

    lower_words = [w.lower() for w in words]
    vocab_richness = len(set(lower_words)) / n_words
    stopword_ratio = sum(1 for w in lower_words if w in ENGLISH_STOP_WORDS) / n_words
    avg_word_len = float(np.mean([len(w) for w in words])) if words else 0.0

    contraction_rate = len(CONTRACTION_RE.findall(text)) / n_sent
    first_person_rate = len(FIRST_PERSON_RE.findall(text)) / n_words
    passive_rate = len(PASSIVE_RE.findall(text)) / n_sent
    transitions = sum(text.lower().count(p) for p in FORMAL_TRANSITIONS) / n_sent

    punct_count = sum(1 for c in text if c in ",;:")
    punct_ratio = punct_count / max(len(text), 1)

    return [
        avg_sent_len, burstiness, vocab_richness, stopword_ratio, avg_word_len,
        contraction_rate, first_person_rate, passive_rate, transitions, punct_ratio,
    ]


FEATURE_NAMES = [
    "avg_sentence_len", "burstiness", "vocab_richness", "stopword_ratio", "avg_word_len",
    "contraction_rate", "first_person_rate", "passive_rate", "transition_rate", "punct_ratio",
]


class StyleFeatureExtractor(BaseEstimator, TransformerMixin):
    """Turns raw text into a fixed-size numeric feature vector."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.array([_extract_one(t) for t in X], dtype=float)
