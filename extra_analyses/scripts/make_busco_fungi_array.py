#!/usr/bin/env python3
"""Create/submit fungal BUSCO SLURM arrays with safe incremental metadata updates.

Successful array tasks:
  1. run BUSCO (fungi_odb10, genome mode),
  2. validate and atomically save an individual summary,
  3. update the combined metadata CSV under a filesystem lock,
  4. remove ONLY miniprot_align_fungi_odb10_out.log from this OME's BUSCO logs.

A dependent 'afterany' merge job reconciles the entire CSV when an array ends.

Examples:
  python make_busco_fungi_array.py -i omes.txt --run-name test --limit 5 --submit
  python make_busco_fungi_array.py --mtdb /path/to/incoming.mtdb --run-name ncbi --submit
  python make_busco_fungi_array.py --merge-only
  python make_busco_fungi_array.py --update-ome fuspro7
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

BASE = Path('/project/arsef/databases/mycotools/database_stats/busco/fungi')
FNA = Path('/project/arsef/databases/mycotools/mycotoolsdb/data/fna')
LINEAGE = Path('/project/arsef/databases/funannotate_databases/fungi_odb10')
SUMMARY_DIR = BASE / 'short_summaries'
BY_OME = BASE / 'by_ome'
CSV_PATH = BASE / 'busco_summary_table.csv'
LOCK_PATH = BASE / '.busco_summary_table.lock'
LOG_NAME = 'miniprot_align_fungi_odb10_out.log'
FIELDNAMES = [
    'OME',
    'BUSCO_fungi_Complete_count', 'BUSCO_fungi_Complete_percent',
    'BUSCO_fungi_Single_count', 'BUSCO_fungi_Single_percent',
    'BUSCO_fungi_Duplicated_count', 'BUSCO_fungi_Duplicated_percent',
    'BUSCO_fungi_Fragmented_count', 'BUSCO_fungi_Fragmented_percent',
    'BUSCO_fungi_Missing_count', 'BUSCO_fungi_Missing_percent',
    'BUSCO_fungi_Total_count',
]
COUNTS = {
    'Complete BUSCOs (C)': 'BUSCO_fungi_Complete_count',
    'Complete and single-copy BUSCOs (S)': 'BUSCO_fungi_Single_count',
    'Complete and duplicated BUSCOs (D)': 'BUSCO_fungi_Duplicated_count',
    'Fragmented BUSCOs (F)': 'BUSCO_fungi_Fragmented_count',
    'Missing BUSCOs (M)': 'BUSCO_fungi_Missing_count',
    'Total BUSCO groups searched': 'BUSCO_fungi_Total_count',
}
PCT_NAMES = [
    'BUSCO_fungi_Complete_percent', 'BUSCO_fungi_Single_percent',
    'BUSCO_fungi_Duplicated_percent', 'BUSCO_fungi_Fragmented_percent',
    'BUSCO_fungi_Missing_percent',
]
PCT_PATTERN = re.compile(
    r'C:\s*([\d.]+)%\s*\[\s*S:\s*([\d.]+)%\s*,\s*D:\s*([\d.]+)%\s*\]\s*,\s*'
    r'F:\s*([\d.]+)%\s*,\s*M:\s*([\d.]+)%\s*,\s*n:\s*(\d+)'
)
OME_PATTERN = re.compile(r'[A-Za-z0-9_.-]+\Z')


def read_omes(path, mtdb=False):
    seen, omes = set(), []
    with path.open(encoding='utf-8-sig') as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            ome = line.split('\t', 1)[0].strip() if mtdb else line.split()[0]
            if ome.lower() in ('ome', '#ome'):
                continue
            if not OME_PATTERN.fullmatch(ome):
                raise ValueError(f'Invalid OME identifier in {path}: {ome!r}')
            if ome not in seen:
                seen.add(ome)
                omes.append(ome)
    return omes


def parse_summary(path, ome):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'Missing or empty BUSCO summary: {path}')
    row = {'OME': ome}
    summary_line = None
    with path.open(encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if line.startswith('C:'):
                summary_line = line
            for phrase, col in COUNTS.items():
                if phrase in line:
                    m = re.match(r'^\s*(\d+)\s+', line)
                    if not m:
                        raise ValueError(f'Malformed count for {phrase} in {path}: {line!r}')
                    row[col] = int(m.group(1))
                    break
    if summary_line is None:
        raise ValueError(f'BUSCO C:S:D:F:M summary line not found: {path}')
    p = PCT_PATTERN.search(summary_line)
    if not p:
        raise ValueError(f'Malformed percentage summary line: {path}: {summary_line!r}')
    for col, value in zip(PCT_NAMES, p.groups()[:5]):
        row[col] = float(value)
    total = int(p.group(6))
    if 'BUSCO_fungi_Total_count' in row and row['BUSCO_fungi_Total_count'] != total:
        raise ValueError(f'Conflicting total BUSCO count in {path}')
    row['BUSCO_fungi_Total_count'] = total
    missing = [col for col in FIELDNAMES if col not in row]
    if missing:
        raise ValueError(f'Incomplete BUSCO counts in {path}: {missing}')
    if (row['BUSCO_fungi_Single_count'] + row['BUSCO_fungi_Duplicated_count']
            != row['BUSCO_fungi_Complete_count']):
        raise ValueError(f'Inconsistent complete/single/duplicated counts: {path}')
    if (row['BUSCO_fungi_Complete_count'] + row['BUSCO_fungi_Fragmented_count']
            + row['BUSCO_fungi_Missing_count'] != total):
        raise ValueError(f'Inconsistent complete/fragmented/missing counts: {path}')
    if any(not 0 <= row[c] <= 100 for c in PCT_NAMES):
        raise ValueError(f'Invalid percentage in {path}')
    return row


def write_atomic_csv(rows):
    BASE.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=BASE, prefix='.busco_table_', suffix='.csv')
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator='\n')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, CSV_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_existing_rows():
    rows = {}
    if not CSV_PATH.exists():
        return rows
    with CSV_PATH.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError('Existing BUSCO CSV has an unexpected schema. Run --merge-only '
                             'to rebuild it from individual summaries before submitting arrays.')
        for row in reader:
            ome = row.get('OME', '').strip()
            if ome:
                rows[ome] = row
    return rows


def update_one(ome):
    """One successful BUSCO task updates its row, serializing concurrent writers."""
    if not OME_PATTERN.fullmatch(ome):
        raise ValueError(f'Invalid OME: {ome!r}')
    row = parse_summary(SUMMARY_DIR / f'{ome}.txt', ome)
    BASE.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = read_existing_rows()
        rows[ome] = row
        write_atomic_csv(rows[k] for k in sorted(rows))
    print(f'Updated BUSCO summary table: {ome} ({len(rows)} total rows)', flush=True)


def merge_all(run=None):
    """Rebuild the complete table from valid summaries, even when some tasks fail."""
    BASE.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows, malformed = {}, []
        for path in sorted(SUMMARY_DIR.glob('*.txt')):
            ome = path.stem
            if not OME_PATTERN.fullmatch(ome):
                malformed.append(f'{ome}\t{path}\tInvalid OME')
                continue
            try:
                rows[ome] = parse_summary(path, ome)
            except (OSError, ValueError) as exc:
                malformed.append(f'{ome}\t{path}\t{exc}')
        # A malformed file must not wipe a previously valid row from the table.
        # Prefer parsing current valid summaries; preserve valid historical rows only
        # if their corresponding summary has gone missing, but not if malformed.
        write_atomic_csv(rows[k] for k in sorted(rows))
        (BASE / 'malformed_busco_summaries.tsv').write_text(
            'OME\tpath\terror\n' + '\n'.join(malformed) + ('\n' if malformed else '')
        )
        expected = read_omes(run / 'omes.txt') if run and (run / 'omes.txt').is_file() else []
        missing = [ome for ome in expected if ome not in rows]
        if run:
            (run / 'missing_summaries.txt').write_text('\n'.join(missing) + ('\n' if missing else ''))
    print(f'Combined BUSCO CSV: {CSV_PATH}')
    print(f'Valid unique summaries: {len(rows)}')
    print(f'Malformed summaries: {len(malformed)}')
    print(f'Missing from this run: {len(missing)}')


def valid_central_summary(ome):
    try:
        parse_summary(SUMMARY_DIR / f'{ome}.txt', ome)
        return True
    except (OSError, ValueError):
        return False


def shell_run(cmd):
    print('Running:', shlex.join(cmd), flush=True)
    output = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if output.stdout:
        print(output.stdout.strip(), flush=True)
    return output.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group()
    src.add_argument('-i', '--ome-list', '--ome_list', dest='ome_list', type=Path)
    src.add_argument('--mtdb', type=Path)
    parser.add_argument('--update-ome', help=argparse.SUPPRESS)
    parser.add_argument('--merge-only', action='store_true', help='Rebuild CSV from all short summaries')
    parser.add_argument('--merge-run', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--run-name', default=None)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--concurrency', type=int, default=25)
    parser.add_argument('--threads', type=int, default=16)
    parser.add_argument('--mem', default='96G')
    parser.add_argument('--time', default='12:00:00')
    parser.add_argument('--account', default='arsef')
    parser.add_argument('--partition', default='ceres')
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--rerun', action='store_true')
    args = parser.parse_args()

    if args.update_ome:
        update_one(args.update_ome)
        return
    if args.merge_only or args.merge_run:
        merge_all(args.merge_run)
        return
    if not (args.ome_list or args.mtdb):
        parser.error('Provide -i/--ome-list or --mtdb (or --merge-only)')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.threads < 1 or args.concurrency < 1:
        parser.error('--threads and --concurrency must be positive')
    source = args.mtdb or args.ome_list
    if not source.is_file():
        parser.error(f'Input file does not exist: {source}')
    requested = read_omes(source, mtdb=bool(args.mtdb))
    if args.limit is not None:
        requested = requested[:args.limit]
    selected, skipped, missing = [], [], []
    for ome in requested:
        fna = FNA / f'{ome}.fna'
        if not fna.is_file() or fna.stat().st_size == 0:
            missing.append(ome)
        elif not args.rerun and valid_central_summary(ome):
            skipped.append(ome)
        else:
            selected.append(ome)
    print(f'Unique requested OMEs: {len(requested)}')
    print(f'Selected: {len(selected)}; existing valid summaries skipped: {len(skipped)}; missing/empty FNAs: {len(missing)}')
    if not selected:
        print('No BUSCO array needed. To refresh existing CSV, run --merge-only.')
        return
    run_name = args.run_name or datetime.now().strftime('busco_%Y%m%d_%H%M%S_%f')
    if not OME_PATTERN.fullmatch(run_name):
        parser.error('Invalid run name; use letters, digits, _, . or -')
    run = BASE / 'array_runs' / run_name
    if run.exists():
        parser.error(f'Run directory already exists: {run}')
    run.mkdir(parents=True)
    (BASE / 'logs').mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    BY_OME.mkdir(parents=True, exist_ok=True)
    (run / 'omes.txt').write_text('\n'.join(selected) + '\n')
    (run / 'skipped_complete.txt').write_text('\n'.join(skipped) + ('\n' if skipped else ''))
    (run / 'missing_fna.txt').write_text('\n'.join(missing) + ('\n' if missing else ''))
    script = Path(__file__).resolve()
    batch = run / 'busco_array.sbatch'
    batch.write_text(f'''#!/usr/bin/env bash
#SBATCH --job-name=busco_{run_name[:35]}
#SBATCH --account={args.account}
#SBATCH --partition={args.partition}
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={args.threads}
#SBATCH --mem={args.mem}
#SBATCH --time={args.time}
#SBATCH --array=0-{len(selected)-1}%{args.concurrency}
#SBATCH --output={BASE}/logs/busco_%A_%a.out
#SBATCH --error={BASE}/logs/busco_%A_%a.err
set -Eeuo pipefail
MANIFEST={shlex.quote(str(run / 'omes.txt'))}
OME="$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$MANIFEST")"
[[ -n "$OME" ]] || {{ echo "No OME for task $SLURM_ARRAY_TASK_ID" >&2; exit 1; }}
module load miniconda/24.7.1-2
source activate /project/arsef/environments/funannotate
export AUGUSTUS_CONFIG_PATH="$(dirname "$(dirname "$(which augustus)")")/config/"
FNA={shlex.quote(str(FNA))}/"$OME".fna
PARENT={shlex.quote(str(BY_OME))}/"$OME"
SUMMARY_DIR={shlex.quote(str(SUMMARY_DIR))}
mkdir -p "$PARENT" "$SUMMARY_DIR"
cd "$PARENT"
PYTHONWARNINGS='ignore::SyntaxWarning' \\
busco -i "$FNA" -o "$OME" -m genome -l {shlex.quote(str(LINEAGE))} -c "$SLURM_CPUS_PER_TASK" -f
# Select only a nonempty, specific fungi_odb10 summary from this OME.
SUMMARY=""
for candidate in \\
  "$PARENT/$OME"/short_summary.specific.*fungi_odb10*.txt \\
  "$PARENT"/short_summary.specific.*fungi_odb10*.txt; do
    if [[ -s "$candidate" ]]; then
        SUMMARY="$candidate"
        break
    fi
done
[[ -n "$SUMMARY" ]] || {{ echo "No fungi_odb10 BUSCO summary for $OME" >&2; exit 1; }}
# Stage the summary atomically to prevent readers from seeing a partial file.
STAGED="$(mktemp "$SUMMARY_DIR/.${{OME}}.XXXXXX")"
trap 'rm -f "$STAGED"' EXIT
cp "$SUMMARY" "$STAGED"
# The Python update validates before adding it to the central table.
# Use a temporary filename until validation succeeds.
python3 {shlex.quote(str(script))} --validate-summary "$STAGED" --validate-ome "$OME"
mv -f "$STAGED" "$SUMMARY_DIR/$OME.txt"
python3 {shlex.quote(str(script))} --update-ome "$OME"
# Delete ONLY the known giant Miniprot stdout log(s) for this OME.
# Do not touch other logs, the full BUSCO output, or sequence files.
for log_dir in "$PARENT/$OME/logs" "$PARENT/logs"; do
    if [[ -f "$log_dir/{LOG_NAME}" && ! -L "$log_dir/{LOG_NAME}" ]]; then
        rm -f -- "$log_dir/{LOG_NAME}"
        echo "Removed Miniprot log: $log_dir/{LOG_NAME}"
    fi
done
echo "Completed BUSCO, summary updated, Miniprot log cleaned: $OME"
''')
    merge_batch = run / 'busco_merge.sbatch'
    merge_batch.write_text(f'''#!/usr/bin/env bash
#SBATCH --job-name=busco_merge
#SBATCH --account={args.account}
#SBATCH --partition={args.partition}
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output={run}/merge_%j.out
#SBATCH --error={run}/merge_%j.err
set -Eeuo pipefail
python3 {shlex.quote(str(script))} --merge-run {shlex.quote(str(run))}
''')
    print('Array script:', batch)
    print('Merge script:', merge_batch)
    if args.submit:
        jobid = shell_run(['sbatch', '--parsable', str(batch)]).split(';')[0]
        if not jobid.isdigit():
            raise RuntimeError(f'Unexpected sbatch reply: {jobid}')
        (run / 'array_job_id.txt').write_text(jobid + '\n')
        try:
            mergeid = shell_run(['sbatch', '--parsable', f'--dependency=afterany:{jobid}', str(merge_batch)]).split(';')[0]
            (run / 'merge_job_id.txt').write_text(mergeid + '\n')
        except subprocess.CalledProcessError:
            print(f'Array {jobid} submitted but merge job submission failed. Submit {merge_batch} manually.', file=sys.stderr)
            raise
    else:
        print('Jobs NOT submitted. Add --submit to launch the array and dependent merge.')


if __name__ == '__main__':
    # Kept as a hidden CLI mode for validating staged reports before publication.
    if '--validate-summary' in sys.argv:
        p = argparse.ArgumentParser()
        p.add_argument('--validate-summary', type=Path, required=True)
        p.add_argument('--validate-ome', required=True)
        a = p.parse_args()
        parse_summary(a.validate_summary, a.validate_ome)
        print(f'Validated BUSCO summary for {a.validate_ome}')
    else:
        main()
