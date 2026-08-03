"""
project_config.py: single source of truth for the whole thesis project.

Import at the top of EVERY analysis notebook (training, cv, robustness,
interpretability, error analysis):

    import sys
    from pathlib import Path
    _here = Path.cwd()
    sys.path.insert(0, str(_here if (_here / "project_config.py").exists() else _here / "scripts"))
    from project_config import *

    model_df = load_model_df()
    y = model_df["phq9"]

Then use the CONSTANTS below everywhere. Never redefine `acoustic` inline again.
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
REPEATED_CV_SEEDS = range(20)

# ---------------------------------------------------------------------------
# Data location: works whether a notebook runs from scripts/ or the data root
# ---------------------------------------------------------------------------
def _resolve_data_dir() -> Path:
    module_dir = Path(__file__).resolve().parent          # .../scripts
    for cand in (module_dir.parent, module_dir, Path.cwd(), Path.cwd().parent):
        if (cand / "model_df.csv").exists():
            return cand
    raise FileNotFoundError("model_df.csv not found near project_config.py or cwd")

DATA_DIR = _resolve_data_dir()

# ---------------------------------------------------------------------------
# Clinical / demographic feature sets (UPPERCASE = canonical constants)
# ---------------------------------------------------------------------------
DEMO     = ["age", "gender", "education_years"]
PSYCH    = ["ctq_sf", "LES", "SSRS", "gad7", "PSQI"]
CLINICAL = DEMO + PSYCH                                    # 8
_ID_TARGET = ["subject_key", "phq9"]

# ---------------------------------------------------------------------------
# A-priori functional-collapse rule: keep mean + coefficient of variation per
# LLD, drop the redundant/noise-prone percentile, percentile-range, and
# rising/falling-slope functionals. (Note: 'RisingSlope'/'FallingSlope', NOT
# bare 'slope', so the spectral slopeV LLDs are preserved.)
# ---------------------------------------------------------------------------
_DROP_MARKERS = ["percentile", "pctlrange", "RisingSlope", "FallingSlope"]

def collapse_functionals(names):
    return [c for c in names if not any(m in c for m in _DROP_MARKERS)]

# ---------------------------------------------------------------------------
# Canonical acoustic feature sets, derived once from model_df's columns
# ---------------------------------------------------------------------------
def load_model_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "model_df.csv", dtype={"subject_key": str})

_MDF = load_model_df()
ACOUSTIC_FULL = [c for c in _MDF.columns if c not in _ID_TARGET + CLINICAL]   # 88
ACOUSTIC      = collapse_functionals(ACOUSTIC_FULL)                           # 72  <-- USE THIS

# Convenience combined sets
DEMO_ACOUSTIC     = DEMO + ACOUSTIC
CLINICAL_ACOUSTIC = CLINICAL + ACOUSTIC

# Canonical subject ordering (as int) — matches model_df's row order. Aligning every
# subject-level table to this makes KFold(shuffle, random_state) assign identical folds
# across notebooks, so results built from recordings match the model_df-based results.
CANONICAL_ORDER = _MDF["subject_key"].astype(int).tolist()

# ---------------------------------------------------------------------------
# Per-recording -> subject-level aggregation (drop-recordings / noise experiments)
# ---------------------------------------------------------------------------
def subject_means(df, feats=None):
    """Aggregate an ALREADY-LOADED per-recording df to subject means, aligned to
    CANONICAL_ORDER so fold assignments match the model_df-based tables."""
    if feats is None:
        feats = ACOUSTIC
    X = df.groupby("subject_id")[feats].mean()
    X.index = X.index.astype(int)
    X = X.loc[[i for i in CANONICAL_ORDER if i in X.index]]   # canonical order
    y = df.groupby("subject_id")["phq9"].first()
    y.index = y.index.astype(int)
    y = y.loc[X.index]
    return X, y

def subject_table(csv, feats=None):
    """Load a per-recording CSV and aggregate to aligned subject means."""
    if feats is None:
        feats = ACOUSTIC
    f = pd.read_csv(DATA_DIR / csv, dtype={"subject_id": str}).dropna(subset=["phq9"])
    missing = [c for c in feats if c not in f.columns]
    if missing:
        raise ValueError(f"{csv} missing {len(missing)} features, e.g. {missing[:3]}")
    return subject_means(f, feats)

# ---------------------------------------------------------------------------
# Acoustic feature -> interpretable category (GeMAPS; Eyben et al. 2016).
# Perturbation measures jitter + shimmer grouped with HNR under Voice quality.
# ---------------------------------------------------------------------------
def categorize(feat):
    if feat in DEMO:  return "Demographics"
    if feat in PSYCH: return "Clinical"
    fl = feat.lower()
    if any(k in fl for k in ["segmentlength", "segmentspersec", "peakspersec"]): return "Timing/Pauses"
    if "f0semitone" in fl:                                                        return "Pitch"
    if "loudness" in fl or "equivalentsoundlevel" in fl:                          return "Loudness/Energy"
    if any(k in fl for k in ["jitter", "shimmer", "hnr", "h1-h2", "h1-a3"]):      return "Voice quality"
    if re.match(r"f[123](frequency|bandwidth|amplitude)", fl):                    return "Formants"
    if any(k in fl for k in ["alpharatio", "hammarberg", "slope", "spectralflux", "mfcc"]): return "Spectral"
    return "Other"

# ---------------------------------------------------------------------------
# Canonical repeated-CV scorer --> returns {metric: (mean, std)} across seeds.
# Use this everywhere instead of per-notebook `evaluate` copies.
# ---------------------------------------------------------------------------
def repeated_cv(estimator, X, y, seeds=REPEATED_CV_SEEDS, n_splits=10):
    from sklearn.model_selection import KFold, cross_val_predict
    from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
    from scipy.stats import pearsonr
    rows = []
    for s in seeds:
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=s)
        p = cross_val_predict(estimator, X, y, cv=kf, n_jobs=-1)
        rows.append({"MAE": mean_absolute_error(y, p),
                     "RMSE": np.sqrt(mean_squared_error(y, p)),
                     "R2": r2_score(y, p),
                     "r": pearsonr(y, p)[0]})
    d = pd.DataFrame(rows)
    return {k: (d[k].mean(), d[k].std()) for k in ["MAE", "RMSE", "R2", "r"]}


if __name__ == "__main__":
    print(f"DATA_DIR = {DATA_DIR}")
    print(f"DEMO={len(DEMO)} PSYCH={len(PSYCH)} CLINICAL={len(CLINICAL)} "
          f"ACOUSTIC_FULL={len(ACOUSTIC_FULL)} ACOUSTIC={len(ACOUSTIC)}")
    assert len(ACOUSTIC) == 72, f"Expected 72 collapsed features, got {len(ACOUSTIC)}"
    print("OK — 72-feature acoustic set is canonical.")
