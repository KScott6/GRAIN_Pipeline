#!/usr/bin/env python3
"""Generate (and optionally submit) QUAST arrays and aggregate MycoTools reports.

Usage:
  python make_quast_array.py --mtdb 20261023.mtdb --run-name new_genomes --submit
  python make_quast_array.py -i omes.txt --run-name test --limit 5

The --merge-run mode is used by the generated dependent SLURM job.
"""
import argparse
import csv
import fcntl
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE = Path('/project/arsef/databases/mycotools/database_stats/quast')
FNA = Path('/project/arsef/databases/mycotools/mycotoolsdb/data/fna')
COLUMN_MAP = {
    '# contigs (>= 0 bp)': 'QUAST_count_contigs_0_bp',
    '# contigs (>= 1000 bp)': 'QUAST_count_contigs_1000_bp',
    '# contigs (>= 5000 bp)': 'QUAST_count_contigs_5000_bp',
    '# contigs (>= 10000 bp)': 'QUAST_count_contigs_10000_bp',
    '# contigs (>= 25000 bp)': 'QUAST_count_contigs_25000_bp',
    '# contigs (>= 50000 bp)': 'QUAST_count_contigs_50000_bp',
    'Total length (>= 0 bp)': 'QUAST_Total_length_0_bp',
    'Total length (>= 1000 bp)': 'QUAST_Total_length_1000_bp',
    'Total length (>= 5000 bp)': 'QUAST_Total_length_5000_bp',
    'Total length (>= 10000 bp)': 'QUAST_Total_length_10000_bp',
    'Total length (>= 25000 bp)': 'QUAST_Total_length_25000_bp',
    'Total length (>= 50000 bp)': 'QUAST_Total_length_50000_bp',
    '# contigs': 'QUAST_count_contigs',
    'Largest contig': 'QUAST_Largest_contig',
    'Total length': 'QUAST_Total_length',
    'GC (%)': 'QUAST_GC',
    'N50': 'QUAST_N50',
    'N90': 'QUAST_N90',
    'auN': 'QUAST_auN',
    'L50': 'QUAST_L50',
    'L90': 'QUAST_L90',
    "# N's per 100 kbp": 'QUAST_count_N_s_per_100_kbp',
}
OUTPUT_COLS = ['OME', *COLUMN_MAP.values()]


def read_omes(path, mtdb=False):
    seen = set()
    omes = []
    with path.open(encoding='utf-8-sig') as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            ome = line.split('\t', 1)[0].strip() if mtdb else line.strip().split()[0]
            if ome.lower() in ('ome', '#ome'):
                continue
            if ome and ome not in seen:
                seen.add(ome)
                omes.append(ome)
    return omes


def valid_report(path):
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        with path.open(newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            if 'Assembly' not in (reader.fieldnames or []):
                return False
            rows = list(reader)
            return len(rows) == 1 and bool(rows[0].get('Assembly'))
    except (OSError, csv.Error, UnicodeError):
        return False


def write_atomic_tsv(path, rows):
    fd, temp = tempfile.mkstemp(prefix='.quast_', suffix='.tsv', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS, delimiter='\t', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def merge(run):
    BASE.mkdir(parents=True, exist_ok=True)
    reports_dir = BASE / 'individual_reports'
    summary = BASE / 'quast_summary_combined.tsv'
    lock_path = BASE / '.quast_merge.lock'
    # Serializes merges from independently finishing arrays.
    with lock_path.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows, malformed = [], []
        for path in sorted(reports_dir.glob('*_transposed_report.tsv')):
            ome = path.name[:-len('_transposed_report.tsv')]
            try:
                with path.open(newline='') as f:
                    reader = csv.DictReader(f, delimiter='\t')
                    if 'Assembly' not in (reader.fieldnames or []):
                        raise ValueError('Missing Assembly column')
                    data = list(reader)
                    if len(data) != 1 or not data[0].get('Assembly'):
                        raise ValueError(f'Expected one nonempty assembly row, got {len(data)}')
                    row = {'OME': ome}
                    for source, target in COLUMN_MAP.items():
                        row[target] = data[0].get(source, '')
                    rows.append(row)
            except (OSError, csv.Error, UnicodeError, ValueError) as exc:
                malformed.append(f'{ome}\t{path}\t{exc}')
        write_atomic_tsv(summary, rows)
        (BASE / 'malformed_reports.txt').write_text('\n'.join(malformed) + ('\n' if malformed else ''))
        expected = read_omes(run / 'omes.txt') if run and (run / 'omes.txt').exists() else []
        found = {row['OME'] for row in rows}
        missing = [ome for ome in expected if ome not in found]
        if run:
            (run / 'missing_reports.txt').write_text('\n'.join(missing) + ('\n' if missing else ''))
        print(f'Combined QUAST summary: {summary}')
        print(f'Parsed reports: {len(rows)}')
        print(f'Malformed reports: {len(malformed)}')
        print(f'Missing from this run: {len(missing)}')
        if missing:
            print('Missing genome list:', run / 'missing_reports.txt')
        if malformed:
            print('Malformed report details:', BASE / 'malformed_reports.txt')
        # A failed genome does not prevent good genomes from being included.


def run_command(command):
    print('Running:', shlex.join(command), flush=True)
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    print(result.stdout.strip(), flush=True)
    return result.stdout.strip()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    inputs = p.add_mutually_exclusive_group()
    inputs.add_argument('-i', '--ome-list', '--ome_list', dest='ome_list', type=Path, help='One OME per line')
    inputs.add_argument('--mtdb', type=Path, help='MTDB TSV; first column is OME')
    p.add_argument('--merge-run', type=Path, help=argparse.SUPPRESS)
    p.add_argument('--run-name', default=None)
    p.add_argument('--limit', type=int)
    p.add_argument('--concurrency', type=int, default=25)
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('--mem', default='8G')
    p.add_argument('--time', default='04:00:00')
    p.add_argument('--account', default='arsef')
    p.add_argument('--partition', default='ceres')
    p.add_argument('--submit', action='store_true', help='Submit array and dependent report merge')
    p.add_argument('--rerun', action='store_true', help='Recompute genomes with completed reports')
    args = p.parse_args()

    if args.merge_run:
        merge(args.merge_run)
        return
    if not (args.ome_list or args.mtdb):
        p.error('Provide -i/--ome-list or --mtdb')
    if args.limit is not None and args.limit < 1:
        p.error('--limit must be positive')
    if args.threads < 1 or args.concurrency < 1:
        p.error('--threads and --concurrency must be positive')
    source = args.mtdb or args.ome_list
    if not source.is_file():
        p.error(f'Input not found: {source}')
    requested = read_omes(source, mtdb=bool(args.mtdb))
    if args.limit is not None:
        requested = requested[:args.limit]
    reports = BASE / 'individual_reports'
    selected, skipped, missing = [], [], []
    for ome in requested:
        fna = FNA / f'{ome}.fna'
        if not fna.is_file() or fna.stat().st_size == 0:
            missing.append(ome)
        elif not args.rerun and valid_report(reports / f'{ome}_transposed_report.tsv'):
            skipped.append(ome)
        else:
            selected.append(ome)
    print(f'Input unique genomes: {len(requested)}')
    print(f'Selected genomes: {len(selected)}')
    print(f'Skipped already complete: {len(skipped)}')
    print(f'Skipped missing/empty FNAs: {len(missing)}')
    if not selected:
        print('No new QUAST tasks needed. No jobs submitted.')
        return
    run_name = args.run_name or datetime.now().strftime('quast_%Y%m%d_%H%M%S_%f')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', run_name):
        p.error('--run-name may contain only letters, numbers, underscores, periods and hyphens')
    run = BASE / 'array_runs' / run_name
    if run.exists():
        p.error(f'Run directory already exists: {run}; choose a new --run-name')
    run.mkdir(parents=True)
    (BASE / '__quast_logs').mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    (BASE / 'by_ome').mkdir(exist_ok=True)
    (run / 'omes.txt').write_text('\n'.join(selected) + '\n')
    (run / 'skipped_complete.txt').write_text('\n'.join(skipped) + ('\n' if skipped else ''))
    (run / 'missing_fna.txt').write_text('\n'.join(missing) + ('\n' if missing else ''))
    # Use literal absolute paths in generated scripts so they can be submitted from anywhere.
    script_path = Path(__file__).resolve()
    array_script = run / 'quast_array.sbatch'
    array_script.write_text(f'''#!/usr/bin/env bash
#SBATCH --job-name=quast_array
#SBATCH --account={args.account}
#SBATCH --partition={args.partition}
#SBATCH --cpus-per-task={args.threads}
#SBATCH --mem={args.mem}
#SBATCH --time={args.time}
#SBATCH --array=0-{len(selected)-1}%{args.concurrency}
#SBATCH --output={BASE}/__quast_logs/quast_%A_%a.out
#SBATCH --error={BASE}/__quast_logs/quast_%A_%a.err
set -Eeuo pipefail
module load quast
RUN={shlex.quote(str(run))}
BASE={shlex.quote(str(BASE))}
FNA={shlex.quote(str(FNA))}
OME=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$RUN/omes.txt")
[[ -n "$OME" ]] || {{ echo "OME not found for task $SLURM_ARRAY_TASK_ID" >&2; exit 1; }}
OUTPUT="$BASE/by_ome/$OME"
REPORT="$BASE/individual_reports/${{OME}}_transposed_report.tsv"
mkdir -p "$OUTPUT" "$BASE/individual_reports"
quast -t "$SLURM_CPUS_PER_TASK" -o "$OUTPUT" "$FNA/$OME.fna"
[[ -s "$OUTPUT/report.tsv" && -s "$OUTPUT/transposed_report.tsv" ]] || {{ echo "QUAST reports missing: $OME" >&2; exit 1; }}
cp "$OUTPUT/transposed_report.tsv" "$REPORT"
echo "Completed QUAST: $OME"
''')
    merge_script = run / 'quast_merge.sbatch'
    merge_script.write_text(f'''#!/usr/bin/env bash
#SBATCH --job-name=quast_merge
#SBATCH --account={args.account}
#SBATCH --partition={args.partition}
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output={run}/merge_%j.out
#SBATCH --error={run}/merge_%j.err
set -Eeuo pipefail
python3 {shlex.quote(str(script_path))} --merge-run {shlex.quote(str(run))}
''')
    print(f'Manifest: {run / "omes.txt"}')
    print(f'Array script: {array_script}')
    print(f'Merge script: {merge_script}')
    if args.submit:
        reply = run_command(['sbatch', '--parsable', str(array_script)])
        job_id = reply.split(';', 1)[0]
        if not job_id.isdigit():
            raise RuntimeError(f'Could not parse SLURM array job ID: {reply}')
        (run / 'array_job_id.txt').write_text(job_id + '\n')
        try:
            merge_reply = run_command(['sbatch', '--parsable', f'--dependency=afterany:{job_id}', str(merge_script)])
            (run / 'merge_job_id.txt').write_text(merge_reply.split(';', 1)[0] + '\n')
        except subprocess.CalledProcessError:
            print(f'Array submitted ({job_id}), but automatic merge submission failed. Submit {merge_script} manually when the array finishes.', file=sys.stderr)
            raise
    else:
        print('NOT SUBMITTED. Add --submit to submit the array and dependent merge.')


if __name__ == '__main__':
    main()
