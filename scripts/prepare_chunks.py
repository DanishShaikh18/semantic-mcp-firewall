"""
Batch Processing Preparation Script for LLM Log Parsing.

This script loads log records from JSON/JSONL (`data/raw_logs/raw_logs.jsonl`),
splits any clustered multiline logs into distinct individual log events
(whether a multiline stack trace string, a single JSON line, or a single piped text line),
assigns each distinct log event its own unique sequential ID (1 to N), shuffles them randomly,
splits them into equal chunks, and writes each chunk into a separate text file
formatted with strict `<LOG_START>` / `<LOG_END>` delimiters (excluding `category`).

Output Directory: `data/processing_chunks/`
Files generated: `logs_chunk_1.txt`, `logs_chunk_2.txt`, etc.
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


def extract_distinct_events(log_text: str) -> List[str]:
    """
    Splits a multi-line log cluster into distinct individual log events:
    - Single JSON line (`{"timestamp": ...}`)
    - Single piped text line (`2026-06-25 ... | INFO | ...` or `10.240... - - [...] ...`)
    - Multiline stack trace string (`Traceback (most recent call last): ...` or `Error: connect ...\n    at ...`)
    """
    lines = [line.rstrip() for line in str(log_text).split("\n")]
    events = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # 1. Check if line starts a Python Traceback
        if line.strip().startswith("Traceback (most recent call last):"):
            trace_lines = [line]
            i += 1
            while i < n:
                curr = lines[i]
                # Check for traceback continuation lines
                if (
                    curr.startswith("  ")
                    or curr.startswith("\t")
                    or not curr.strip()
                    or curr.strip().startswith("File ")
                    or curr.strip().startswith("The above exception was")
                    or curr.strip().startswith("[SQL:")
                    or curr.strip().startswith("[parameters:")
                    or any(
                        curr.strip().startswith(exc)
                        for exc in (
                            "ValueError:",
                            "KeyError:",
                            "TypeError:",
                            "AttributeError:",
                            "RuntimeError:",
                            "ConnectionError:",
                            "ImportError:",
                            "OperationalError:",
                            "HTTPException:",
                            "ValidationError:",
                            "sqlalchemy.exc.",
                            "psycopg2.",
                            "starlette.exceptions.",
                            "pydantic.error_wrappers.",
                        )
                    )
                ):
                    trace_lines.append(curr)
                    i += 1
                else:
                    break
            while trace_lines and not trace_lines[-1].strip():
                trace_lines.pop()
            if trace_lines:
                events.append("\n".join(trace_lines))
            continue

        # 2. Check if line starts a Node.js / Express / Postgres stack trace
        if (
            line.strip().startswith("Error: ")
            or line.strip().startswith("TypeError: ")
            or line.strip().startswith("UnhandledPromiseRejectionWarning:")
        ) and (
            i + 1 < n
            and (lines[i + 1].strip().startswith("at ") or lines[i + 1].strip().startswith("UnhandledPromiseRejectionWarning:"))
        ):
            trace_lines = [line]
            i += 1
            while i < n:
                curr = lines[i]
                if curr.strip().startswith("at ") or curr.strip().startswith("UnhandledPromiseRejectionWarning:"):
                    trace_lines.append(curr)
                    i += 1
                else:
                    break
            events.append("\n".join(trace_lines))
            continue

        # 3. Otherwise, it's a single line (JSON line or piped text line)
        events.append(line.strip())
        i += 1

    return events


def format_log_entry(event_id: int, log_string: str) -> str:
    """
    Formats a single distinct log event exactly according to specification:
    <LOG_START>
    ID: {id}
    {log_string}
    <LOG_END>
    """
    return f"<LOG_START>\nID: {event_id}\n{log_string.strip()}\n<LOG_END>"


def process_and_split_logs(input_path: pathlib.Path, output_dir: pathlib.Path, num_chunks: int = 4):
    """
    Loads logs, flattens any clustered records into distinct individual log events,
    assigns each distinct event its own unique ID, shuffles them, splits into `num_chunks` parts,
    and writes to text files.
    """
    print(f"Loading logs from: {input_path}")
    raw_records = load_logs(input_path)
    print(f"Loaded {len(raw_records)} raw log records/clusters successfully.")

    if not raw_records:
        raise ValueError("No records found in the input file.")

    # Flatten into distinct log events
    distinct_events = []
    for rec in raw_records:
        log_text = rec.get("log", "")
        events = extract_distinct_events(log_text)
        for ev in events:
            if ev.strip():
                distinct_events.append({
                    "category": rec.get("category", "unknown"),
                    "log": ev.strip(),
                })

    total_distinct = len(distinct_events)
    print(f"Extracted exactly {total_distinct} distinct log events (stack traces, JSON lines, and text lines).")

    # Assign a unique sequential ID to each distinct log event before exporting
    for idx, ev_rec in enumerate(distinct_events, start=1):
        ev_rec["id"] = idx

    # Shuffle distinct events randomly so categories and event types are evenly mixed
    random.shuffle(distinct_events)

    # Calculate chunk size
    chunk_size = (total_distinct + num_chunks - 1) // num_chunks

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Splitting {total_distinct} distinct log events into {num_chunks} chunks (~{chunk_size} events per chunk)...")

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min(start_idx + chunk_size, total_distinct)
        chunk = distinct_events[start_idx:end_idx]

        if not chunk:
            continue

        chunk_num = i + 1
        output_file = output_dir / f"logs_chunk_{chunk_num}.txt"

        formatted_entries = [format_log_entry(rec["id"], rec["log"]) for rec in chunk]
        file_content = "\n\n".join(formatted_entries) + "\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(file_content)

        print(f"Saved {output_file} ({len(chunk)} distinct log events)")

    print(f"\nAll {num_chunks} chunks saved successfully in directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Prepare distinct synthetic log events for batch LLM processing.")
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
