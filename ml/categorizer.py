"""Expense categoriser: TF-IDF (word + character n-grams) + a linear classifier.

* Bootstrapped on synthetic statement text (ml/dataset.py).
* Personalised: the user's own labelled transactions are added with a higher sample weight.
* Evaluated honestly: besides a random split we also hold out whole *merchants* (GroupKFold),
  which measures how well the model handles merchants it has never seen.
"""
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, StratifiedKFold, cross_val_score
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

import config
from core import database
from ml.dataset import generate_dataset

MODEL_KINDS = {"logreg": "Logistic Regression", "linear_svm": "Linear SVM", "naive_bayes": "Complement Naive Bayes"}
USER_SAMPLE_WEIGHT = 5.0
_NOISE = {"upi", "neft", "imps", "pos", "txn", "ref", "okhdfcbank", "oksbi", "okaxis", "ybl", "ibl", "paytm",
          "order", "mumbai", "pune", "bangalore", "delhi", "hyderabad", "chennai", "nagpur"}
_CACHE = {}


def clean_text(text):
    """Lower-case, drop digits/punctuation and statement boilerplate (UPI, NEFT, bank handles, ...)."""
    s = re.sub(r"[^a-z]+", " ", str(text).lower())
    return " ".join(t for t in s.split() if t not in _NOISE and len(t) > 1)


def build_pipeline(kind="logreg"):
    features = FeatureUnion([
        ("word", TfidfVectorizer(preprocessor=clean_text, ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(preprocessor=clean_text, analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
    ])
    clf = {"logreg": lambda: LogisticRegression(max_iter=2000, C=10),
           "linear_svm": lambda: LinearSVC(C=1.0),
           "naive_bayes": lambda: ComplementNB(alpha=0.3)}[kind]()
    return Pipeline([("features", features), ("clf", clf)])


class CategoryModel:
    def __init__(self, kind="logreg"):
        self.kind = kind
        self.pipeline = build_pipeline(kind)

    def fit(self, descriptions, labels, sample_weight=None):
        self.pipeline.fit(list(descriptions), list(labels), clf__sample_weight=sample_weight)
        return self

    def predict_proba(self, descriptions):
        """DataFrame of class probabilities (rows = descriptions, columns = categories)."""
        X = list(descriptions)
        clf = self.pipeline.named_steps["clf"]
        feats = self.pipeline.named_steps["features"].transform(X)
        if hasattr(clf, "predict_proba"):
            p = clf.predict_proba(feats)
        else:  # LinearSVC: softmax over decision scores
            d = clf.decision_function(feats)
            e = np.exp(d - d.max(axis=1, keepdims=True))
            p = e / e.sum(axis=1, keepdims=True)
        return pd.DataFrame(p, columns=clf.classes_)

    def predict(self, descriptions, types=None):
        """DataFrame[Category, Confidence]. `types` ('Income'/'Expense' per row) restricts the choices."""
        descriptions = list(descriptions)
        if not descriptions:
            return pd.DataFrame(columns=["Category", "Confidence"])
        p = self.predict_proba(descriptions)
        if types is not None:
            mask = np.array([[config.category_type(c) == t for c in p.columns] for t in types])
            p = p.where(mask, 0.0)
            p = p.div(p.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        return pd.DataFrame({"Category": p.idxmax(axis=1).values, "Confidence": p.max(axis=1).values})

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)


# ------------------------------------------------------------------- training
def train_model(user_labelled=None, kind="logreg", n_per_class=120):
    """Synthetic bootstrap data + (optionally) the user's labelled rows, weighted higher."""
    base = generate_dataset(n_per_class)
    X, y = base["description"].tolist(), base["category"].tolist()
    w = [1.0] * len(X)
    if user_labelled is not None and not user_labelled.empty:
        ok = user_labelled[user_labelled["category"].isin(config.ALL_CATEGORIES)]
        X += ok["description"].tolist()
        y += ok["category"].tolist()
        w += [USER_SAMPLE_WEIGHT] * len(ok)
    return CategoryModel(kind).fit(X, y, sample_weight=w)


def _path(user_id):
    return config.MODEL_DIR / f"categorizer_user{user_id}.joblib"


def get_model(user_id):
    """Cached per-user model; loads from disk or trains on first use."""
    if user_id in _CACHE:
        return _CACHE[user_id]
    model = None
    if _path(user_id).exists():
        try:
            model = CategoryModel.load(_path(user_id))
        except Exception:
            model = None  # e.g. saved with another scikit-learn version -> retrain
    if model is None:
        model = train_model(database.get_labelled_descriptions(user_id))
        try:
            model.save(_path(user_id))
        except OSError:
            pass
    _CACHE[user_id] = model
    return model


def retrain(user_id):
    """Retrain with the user's labelled transactions. Returns the number of user examples used."""
    labelled = database.get_labelled_descriptions(user_id)
    model = train_model(labelled)
    try:
        model.save(_path(user_id))
    except OSError:
        pass
    _CACHE[user_id] = model
    return len(labelled)


# ----------------------------------------------------------------- evaluation
def evaluate_models(n_per_class=120, seed=42, kinds=tuple(MODEL_KINDS)):
    """Macro-F1 for each model under a random split and under unseen-merchant splits."""
    df = generate_dataset(n_per_class, seed)
    X, y, groups = df["description"].tolist(), df["category"].tolist(), df["merchant"].tolist()
    rows = []
    for kind in kinds:
        pipe = build_pipeline(kind)
        rand = cross_val_score(pipe, X, y, scoring="f1_macro",
                               cv=StratifiedKFold(5, shuffle=True, random_state=seed))
        unseen = cross_val_score(pipe, X, y, scoring="f1_macro", cv=GroupKFold(5), groups=groups)
        rows.append({"Model": MODEL_KINDS[kind], "Random split F1": rand.mean(), "Unseen-merchant F1": unseen.mean(),
                     "Unseen std": unseen.std()})
    return pd.DataFrame(rows)


def detailed_report(kind="logreg", n_per_class=120, seed=42):
    """Train on some merchants, test on different ones. Returns (labels, confusion matrix, report DataFrame)."""
    df = generate_dataset(n_per_class, seed)
    train_idx, test_idx = next(GroupShuffleSplit(test_size=0.25, random_state=seed).split(df, groups=df["merchant"]))
    tr, te = df.iloc[train_idx], df.iloc[test_idx]
    model = CategoryModel(kind).fit(tr["description"], tr["category"])
    pred = model.predict(te["description"])["Category"]
    labels = sorted(df["category"].unique())
    cm = confusion_matrix(te["category"], pred, labels=labels)
    report = pd.DataFrame(classification_report(te["category"], pred, output_dict=True, zero_division=0)).T
    return labels, cm, report
