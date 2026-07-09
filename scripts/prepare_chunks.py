"""
Batch Processing Preparation Script for LLM Log Parsing.

This script loads the 500 synthetic server logs from JSON/JSONL, shuffles them randomly,
splits them into 4 equal chunks of 125 records, and writes each chunk into a separate
text file formatted with strict delimiters (`<LOG_START>` / `<LOG_END>`) and only `ID`
and `log` string (excluding `category`).

Output Directory: `data/processing_chunks/`
Files generated: `logs_chunk_1.txt`, `logs_chunk_2.txt`, `logs_chunk_3.txt`, `logs_chunk_4.txt`
"""

import argparse
import json
import pathlib
import random
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
            # Try loading as standard JSON array first; if fails, fall back to line-by-line JSONL
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


def format_log_entry(record: Dict[str, Any]) -> str:
    """
    Formats a single log record exactly according to specification:
    <LOG_START>
    ID: {id}
    {log_string}
    <LOG_END>
    """
    log_id = record.get("id", "UNKNOWN")
    log_string = str(record.get("log", "")).strip()

    return f"<LOG_START>\nID: {log_id}\n{log_string}\n<LOG_END>"


def process_and_split_logs(input_path: pathlib.Path, output_dir: pathlib.Path, num_chunks: int = 4):
    """
    Loads logs, shuffles them, splits into `num_chunks` equal parts, and writes to text files.
    """
    print(f"Loading logs from: {input_path}")
    records = load_logs(input_path)
    total_records = len(records)
    print(f"Loaded {total_records} records successfully.")

    if total_records == 0:
        raise ValueError("No records found in the input file.")

    # Shuffle records randomly so categories are evenly mixed across chunks
    random.shuffle(records)

    # Calculate chunk size (e.g. 500 / 4 = 125)
    chunk_size = (total_records + num_chunks - 1) // num_chunks

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Splitting {total_records} records into {num_chunks} chunks (approx {chunk_size} records per chunk)...")

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, total_records)
        chunk = records[start_idx:end_idx]

        if not chunk:
            continue

        chunk_num = i + 1
        output_file = output_dir / f"logs_chunk_{chunk_num}.txt"

        formatted_entries = [format_log_entry(rec) for rec in chunk]
        file_content = "\n\n".join(formatted_entries) + "\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(file_content)

        print(f"Saved {output_file} ({len(chunk)} logs)")

    print(f"\nAll {num_chunks} chunks saved successfully in directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Prepare synthetic log records for batch LLM processing.")
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
