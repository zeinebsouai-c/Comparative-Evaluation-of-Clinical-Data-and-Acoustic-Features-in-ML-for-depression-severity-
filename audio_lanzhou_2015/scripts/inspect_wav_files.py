"""Loop over all subject folders, inspect every .wav file, and write a summary CSV.

Expected layout:
    <base_dir>/
        02010001/
            01.wav, 02.wav, ... 29.wav
        02010002/
            ...

For each .wav file we record: subject id, file name, duration (s), sample rate (Hz),
and number of channels.
"""

import csv
import wave
from pathlib import Path

import pandas as pd

from project_paths import DATA_DIR, SUBJECTS_XLSX, WAV_INVENTORY, require

# Directory that contains the subject-id folders. This script lives in
# <data_root>/scripts/, so the subject folders are one level up (DATA_DIR).
BASE_DIR = DATA_DIR
OUTPUT_CSV = WAV_INVENTORY


def load_subject_metadata() -> dict:
    """Map subject id (as int) -> metadata dict (type, PHQ-9) from the metadata sheet.

    Folder names are zero-padded (e.g. '02010001') while the spreadsheet stores
    the id as an integer (2010001), so we key the map on the int value.
    """
    df = pd.read_excel(
        require(SUBJECTS_XLSX, "Place the MODMA metadata sheet in the data root."),
        usecols=["subject id", "type", "PHQ-9"],
    )
    df = df.dropna(subset=["subject id"])
    meta = {}
    for _, row in df.iterrows():
        phq9 = row["PHQ-9"]
        meta[int(row["subject id"])] = {
            "type": str(row["type"]),
            "phq9": None if pd.isna(phq9) else int(phq9),
        }
    return meta


def inspect_wav(path: Path) -> dict:
    """Return metadata for a single .wav file using the stdlib `wave` module."""
    with wave.open(str(path), "rb") as wf:
        n_frames = wf.getnframes()
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        duration = n_frames / sample_rate if sample_rate else 0.0
    return {
        "sample_rate": sample_rate,
        "n_channels": n_channels,
        "duration_sec": round(duration, 3),
    }


def main() -> None:
    rows = []
    subject_meta = load_subject_metadata()
    missing_types = set()

    # Subject folders: directories whose name is all digits (the subject id).
    subject_dirs = sorted(
        d for d in BASE_DIR.iterdir() if d.is_dir() and d.name.isdigit()
    )

    for subject_dir in subject_dirs:
        subject_id = subject_dir.name
        meta_row = subject_meta.get(int(subject_id))
        if meta_row is None:
            missing_types.add(subject_id)
        subject_type = meta_row["type"] if meta_row else None
        subject_phq9 = meta_row["phq9"] if meta_row else None
        for wav_path in sorted(subject_dir.glob("*.wav")):
            try:
                meta = inspect_wav(wav_path)
            except (wave.Error, EOFError) as exc:
                print(f"  ! Could not read {wav_path}: {exc}")
                meta = {"sample_rate": None, "n_channels": None, "duration_sec": None}
            rows.append(
                {
                    "subject_id": subject_id,
                    "type": subject_type,
                    "phq9": subject_phq9,
                    "file_name": wav_path.name,
                    "duration_sec": meta["duration_sec"],
                    "sample_rate": meta["sample_rate"],
                    "n_channels": meta["n_channels"],
                }
            )

    fieldnames = ["subject_id", "type", "phq9", "file_name", "duration_sec", "sample_rate", "n_channels"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Inspected {len(subject_dirs)} subjects, {len(rows)} .wav files.")
    if missing_types:
        print(f"  ! No 'type' found for {len(missing_types)} subjects: {sorted(missing_types)}")
    print(f"Wrote inventory to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
