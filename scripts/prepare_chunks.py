"""
Batch Processing Preparation Script for LLM Log Parsing.

This script loads log records from JSON/JSONL (`data/raw_logs/raw_logs.jsonl`),
takes the 500 JSON objects and divides them evenly into text chunks (default: 4 files
of 125 records each), without splitting multiline "log" strings into individual lines.

Output Directory: `data/processing_chunks/`
Files generated: `logs_chunk_1.txt`, `logs_chunk_2.txt`, etc.
"""

import argparse
import json
import pathlib
from typing import List, Dict, Any


def load_logs(file_path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    Loads logs from either a JSON Lines (.jsonl) file or a standard JSON array (.json) file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix.lower() == ".jsonl":
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        else:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                else:
                    raise ValueError("JSON file must contain a list of log objects.")
            except json.JSONDecodeError:
                f.seek(0)
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

    return records


def format_log_entry(event_id: Any, log_string: str) -> str:
    """
    Formats a single log object with `<LOG_START>` / `<LOG_END>` delimiters,
    printing the ID and the intact, multiline log string from the JSON.
    """
    return f"<LOG_START>\nID: {event_id}\n{log_string.strip()}\n<LOG_END>"


def process_and_split_logs(input_path: pathlib.Path, output_dir: pathlib.Path, num_chunks: int = 4):
    """
    Loads logs from JSON/JSONL and divides the JSON objects evenly into `num_chunks` text files.
    Each block keeps the multiline `log` string intact without line-by-line splitting.
    """
    print(f"Loading logs from: {input_path}")
    records = load_logs(input_path)
    total_records = len(records)
    print(f"Loaded {total_records} log records successfully.")

    if not records:
        raise ValueError("No records found in the input file.")

    # Calculate chunk size
    chunk_size = (total_records + num_chunks - 1) // num_chunks

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Splitting {total_records} intact log records into {num_chunks} chunks (~{chunk_size} records per chunk)...")

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, total_records)
        chunk = records[start_idx:end_idx]

        if not chunk:
            continue

        chunk_num = i + 1
        output_file = output_dir / f"logs_chunk_{chunk_num}.txt"

        # Format each record keeping the multiline log intact
        formatted_entries = [
            format_log_entry(rec.get("id", start_idx + idx + 1), rec.get("log", ""))
            for idx, rec in enumerate(chunk)
        ]
        file_content = "\n\n".join(formatted_entries) + "\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(file_content)

        print(f"Saved {output_file} ({len(chunk)} <LOG_START> blocks)")

    print(f"\nAll {num_chunks} chunks saved successfully in directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Prepare intact synthetic log blocks for batch LLM processing.")
    parser.add_argument(
        "--input",
        "-i",
        type=pathlib.Path,
        default=pathlib.Path("data/raw_logs/raw_logs.jsonl"),
        help="Path to the input JSON or JSONL log file (default: data/raw_logs/raw_logs.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=pathlib.Path,
        default=pathlib.Path("data/processing_chunks"),
        help="Directory to save the formatted chunk text files (default: data/processing_chunks)",
    )
    parser.add_argument(
        "--chunks",
        "-c",
        type=int,
        default=4,
        help="Number of chunks to split the records into (default: 4)",
    )

    args = parser.parse_args()
    process_and_split_logs(args.input, args.output_dir, args.chunks)


if __name__ == "__main__":
    main()
