#!/usr/bin/env python3

import argparse
import csv
from datetime import datetime
from pathlib import Path

BASE = Path("/project/arsef/databases/mycotools/database_stats/annotation_stats")
MASTER = BASE / "mtdb_annotation_stats_master.tsv"

parser = argparse.ArgumentParser()
parser.add_argument("--mtdb", required=True)
parser.add_argument("--batch-size", type=int, default=100)
args = parser.parse_args()

if args.batch_size < 1:
    parser.error("--batch-size must be at least 1")

# Read existing annotation statistics.
with MASTER.open(newline="") as handle:
    reader = csv.reader(handle, delimiter="\t")
    header = next(reader)
    if not header or header[0] != "#ome":
        raise ValueError("Unexpected master TSV header")

    completed = set()
    for row in reader:
        if not row or not row[0].strip():
            continue
        if row[0] in completed:
            raise ValueError(f"Duplicate ome in master TSV: {row[0]}")
        completed.add(row[0])

# Select full MTDB records for genomes not yet analyzed.
pending = []
seen = set()

with open(args.mtdb) as handle:
    for line in handle:
        ome = line.split("\t", 1)[0].strip()

        if not ome or ome.startswith("#"):
            continue
        if ome in seen:
            raise ValueError(f"Duplicate ome in MTDB: {ome}")

        seen.add(ome)

        if ome not in completed:
            pending.append(line.rstrip("\n") + "\n")

print(f"Genomes in MTDB: {len(seen)}")
print(f"Already analyzed: {len(seen & completed)}")
print(f"New genomes: {len(pending)}")

if not pending:
    print("Annotation statistics are up to date.")
    raise SystemExit(0)

# Create a fresh run directory, preserving all previous runs.
run_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
run_dir = BASE / "runs" / run_name
batch_dir = run_dir / "batches"
batch_dir.mkdir(parents=True)

for i in range(0, len(pending), args.batch_size):
    batch_number = i // args.batch_size
    batch_file = batch_dir / f"batch_{batch_number:04d}.mtdb"
    batch_file.write_text("".join(pending[i:i + args.batch_size]))

print(f"Number of batches: {(len(pending) + args.batch_size - 1) // args.batch_size}")
print(f"Run directory: {run_dir}")
print("No jobs submitted.")
