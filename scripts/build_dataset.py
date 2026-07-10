"""
Dataset Preparation Script for Edge Logging Firewall Fine-Tuning.

This script:
1. Loads the Raw Logs (`data/raw_logs/raw_logs.jsonl`) into memory (500 objects).
2. Loads and combines the arrays from all four Target JSON files (`data/target/target_1.json` through `target_4.json`) into a single list of 500 targets.
3. Matches each Raw Log to its corresponding Target JSON using the `id` key.
4. Formats the matched pair into the strict Hugging Face ChatML format:
   {"messages": [{"role": "system", "content": "You are an Edge Logging Firewall. Analyze backend production logs, ignore irrelevant noise, redact sensitive PII, and output ONLY valid JSON matching the telemetry schema."}, {"role": "user", "content": "<raw log>"}, {"role": "assistant", "content": "<target JSON string>"}]}
5. Drops the `id` key entirely from the final output (both top-level and inside `<target JSON string>`).
6. Randomly shuffles the 500 ChatML objects.
7. Performs an 80/20 train/test split.
8. Saves 400 objects as `data/training/train_data.jsonl` and 100 objects as `data/training/test_data.jsonl`.
"""

import argparse
import json
import pathlib
import random
from typing import List, Dict, Any

SYSTEM_PROMPT = (
    "You are an Edge Logging Firewall. Analyze backend production logs, "
    "ignore irrelevant noise, redact sensitive PII, and output ONLY valid JSON "
    "matching the telemetry schema."
)


def load_raw_logs(raw_logs_path: pathlib.Path) -> Dict[Any, Dict[str, Any]]:
    """Loads raw logs from JSONL file into a dict keyed by id."""
    if not raw_logs_path.exists():
        raise FileNotFoundError(f"Raw logs file not found: {raw_logs_path}")

    raw_logs = {}
    with open(raw_logs_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "id" not in obj:
                raise KeyError("Raw log object missing 'id' field")
            raw_logs[obj["id"]] = obj
    return raw_logs


def load_targets(target_dir: pathlib.Path) -> Dict[Any, Dict[str, Any]]:
    """Loads all target JSON arrays from target_*.json files into a dict keyed by id."""
    if not target_dir.exists():
        raise FileNotFoundError(f"Target directory not found: {target_dir}")

    target_files = sorted(target_dir.glob("target_*.json"))
    if not target_files:
        raise FileNotFoundError(f"No target_*.json files found in {target_dir}")

    targets = {}
    for t_file in target_files:
        with open(t_file, "r", encoding="utf-8") as f:
            arr = json.load(f)
            if not isinstance(arr, list):
                raise ValueError(f"Target file {t_file} must contain a JSON array")
            for obj in arr:
                if "id" not in obj:
                    raise KeyError(f"Target object in {t_file} missing 'id' field")
                targets[obj["id"]] = obj
    return targets


def build_chatml_dataset(
    raw_logs_path: pathlib.Path,
    target_dir: pathlib.Path,
    output_dir: pathlib.Path,
    seed: int = 42,
):
    print(f"Loading raw logs from: {raw_logs_path}")
    raw_logs = load_raw_logs(raw_logs_path)
    print(f"Loaded {len(raw_logs)} raw log records.")

    print(f"Loading target JSONs from: {target_dir}")
    targets = load_targets(target_dir)
    print(f"Loaded {len(targets)} target records.")

    if len(raw_logs) != len(targets):
        print(f"Warning: Count mismatch between raw logs ({len(raw_logs)}) and targets ({len(targets)})")

    matched_ids = sorted(set(raw_logs.keys()).intersection(set(targets.keys())))
    print(f"Matched {len(matched_ids)} records by 'id'.")

    chatml_objects = []
    for item_id in matched_ids:
        raw_obj = raw_logs[item_id]
        target_obj = targets[item_id]

        raw_log_str = raw_obj.get("log", "")

        # Drop 'id' from target dictionary before converting to string
        target_clean = {k: v for k, v in target_obj.items() if k != "id"}
        target_json_str = json.dumps(target_clean, ensure_ascii=False)

        chatml_entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_log_str},
                {"role": "assistant", "content": target_json_str},
            ]
        }
        chatml_objects.append(chatml_entry)

    # Randomly shuffle the ChatML objects
    random.seed(seed)
    random.shuffle(chatml_objects)

    # Perform 80/20 split
    split_idx = int(len(chatml_objects) * 0.8)
    train_data = chatml_objects[:split_idx]
    test_data = chatml_objects[split_idx:]

    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train_data.jsonl"
    test_path = output_dir / "test_data.jsonl"

    print(f"\nSaving {len(train_data)} train samples to {train_path}...")
    with open(train_path, "w", encoding="utf-8") as f:
        for entry in train_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Saving {len(test_data)} test samples to {test_path}...")
    with open(test_path, "w", encoding="utf-8") as f:
        for entry in test_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("\nDataset preparation pipeline finished successfully!")


def main():
    parser = argparse.ArgumentParser(description="Build Hugging Face ChatML dataset from raw logs and target JSONs.")
    parser.add_argument(
        "--raw-logs",
        "-r",
        type=pathlib.Path,
        default=pathlib.Path("data/raw_logs/raw_logs.jsonl"),
        help="Path to raw_logs.jsonl (default: data/raw_logs/raw_logs.jsonl)",
    )
    parser.add_argument(
        "--target-dir",
        "-t",
        type=pathlib.Path,
        default=pathlib.Path("data/target"),
        help="Directory containing target_*.json files (default: data/target)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=pathlib.Path,
        default=pathlib.Path("data/training"),
        help="Directory to save train_data.jsonl and test_data.jsonl (default: data/training)",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Random seed for shuffling (default: 42)",
    )

    args = parser.parse_args()
    build_chatml_dataset(args.raw_logs, args.target_dir, args.output_dir, args.seed)


if __name__ == "__main__":
    main()
