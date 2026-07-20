"""
Trains an AI-text classifier: TF-IDF (word patterns) + stylometric features
(sentence-length uniformity, contractions, passive voice, etc. — see features.py)
combined via FeatureUnion, then Logistic Regression.

Usage:
    python train_model.py                      # uses data/train_data.csv (demo data)
    python train_model.py --csv path/to.csv     # use your own real dataset
                                                 # (columns: text,label; label=1 AI, 0 Human)
"""
import argparse
import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from features import StyleFeatureExtractor  # noqa: F401 (must be importable for unpickling)

HERE = os.path.dirname(__file__)


def build_pipeline():
    return Pipeline([
        ("features", FeatureUnion([
            ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1, 2),
                                       stop_words="english", min_df=2)),
            ("style", Pipeline([
                ("extract", StyleFeatureExtractor()),
                ("scale", StandardScaler()),
            ])),
        ])),
        ("clf", LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced")),
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=os.path.join(HERE, "data", "train_data.csv"))
    parser.add_argument("--out", default=os.path.join(HERE, "model.pkl"))
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        raise FileNotFoundError(
            f"{args.csv} not found. Run generate_dataset.py first, or point --csv at your own dataset."
        )

    df = pd.read_csv(args.csv).dropna(subset=["text", "label"])
    df = df[df["text"].str.split().str.len() >= 5]  # drop unusably short rows
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    print(classification_report(y_test, preds, target_names=["Human", "AI"]))

    joblib.dump(pipeline, args.out)
    print(f"Model saved to {args.out}")


if __name__ == "__main__":
    main()
