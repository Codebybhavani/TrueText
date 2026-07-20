import os
import joblib
from lime.lime_text import LimeTextExplainer

import features  # noqa: F401 - required so joblib can unpickle StyleFeatureExtractor

HERE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(HERE, "model.pkl")

_model = None
_explainer = LimeTextExplainer(class_names=["Human", "AI"])


def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "model.pkl not found. Run: python generate_dataset.py && python train_model.py"
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def style_stats(text: str) -> dict:
    """Human-readable version of the same stylometric features used by the model."""
    vals = features._extract_one(text)
    d = dict(zip(features.FEATURE_NAMES, vals))
    return {
        "avg_sentence_len": round(d["avg_sentence_len"], 1),
        "burstiness": round(d["burstiness"], 2),
        "vocab_richness": round(d["vocab_richness"], 3),
        "contraction_rate": round(d["contraction_rate"], 2),
        "passive_rate": round(d["passive_rate"], 2),
        "transition_rate": round(d["transition_rate"], 2),
    }


def predict_fast(text: str) -> dict:
    """Probabilities only, no LIME — used for instructor batch mode so 20-30
    files don't take forever (LIME re-runs the model dozens of times per call)."""
    model = load_model()
    proba = model.predict_proba([text])[0]
    human_p, ai_p = float(proba[0]), float(proba[1])
    label = "AI Generated" if ai_p >= 0.5 else "Human Written"
    return {
        "label": label,
        "ai_probability": round(ai_p * 100, 2),
        "human_probability": round(human_p * 100, 2),
        "word_count": len(text.split()),
    }


def predict(text: str) -> dict:
    model = load_model()
    proba = model.predict_proba([text])[0]
    human_p, ai_p = float(proba[0]), float(proba[1])
    label = "AI Generated" if ai_p >= 0.5 else "Human Written"

    def predict_proba_fn(texts):
        return model.predict_proba(texts)

    num_features = min(10, max(3, len(text.split())))
    try:
        exp = _explainer.explain_instance(text, predict_proba_fn, num_features=num_features, labels=(1,))
        word_weights = exp.as_list(label=1)
    except Exception:
        word_weights = []

    highlighted = [{"word": w, "weight": round(float(wt), 4)} for w, wt in word_weights]

    return {
        "label": label,
        "ai_probability": round(ai_p * 100, 2),
        "human_probability": round(human_p * 100, 2),
        "highlighted_words": highlighted,
        "style": style_stats(text),
    }
