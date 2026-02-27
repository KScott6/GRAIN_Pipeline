#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Generate (and optionally submit) BUSCO SLURM jobs for OMEs listed in the FIRST column "
            "of any input file (mtdb/list/tsv/csv)."
        )
    )
    p.add_argument(
        "-i", "--input",
        required=True,
        help="Input file: first column contains OME codes. No header required."
    )
    p.add_argument(
        "--submit",
        action="store_true",
        help="Submit each generated script with sbatch. Otherwise, only write scripts."
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip OMEs that already have a short_summary in by_ome/<ome>/<ome>/."
    )
    return p.parse_args()


def read_first_column(path: Path):
    omes = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 1st column token (whitespace) then strip comma if CSV-ish
            token = line.split()[0].split(",")[0]
            omes.append(token)

    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for o in omes:
        if o not in seen:
            uniq.append(o)
            seen.add(o)
    return uniq


def main():
    args = parse_args()

    # === CONFIGURATION ===
    fna_dir = Path("/project/arsef/databases/mycotools/mycotoolsdb/data/fna")

    script_output_dir = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/scripts")
    log_output_dir = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/logs")
    busco_output_base = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/by_ome")
    summary_output_dir = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/short_summaries")

    busco_db = "/project/arsef/databases/funannotate_databases/fungi_odb10"
    conda_env = "/project/arsef/environments/funannotate"

    fail_log = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/failed_submissions.txt")
    missing_fna_log = Path("/project/arsef/databases/mycotools/database_stats/busco/fungi/missing_fna.txt")

    # SLURM resources
    slurm_ntasks = 36
    slurm_time = "48:00:00"
    slurm_mem_per_cpu = "8000MB"
    slurm_partition = "ceres"

    # === SETUP ===
    script_output_dir.mkdir(parents=True, exist_ok=True)
    log_output_dir.mkdir(parents=True, exist_ok=True)
    busco_output_base.mkdir(parents=True, exist_ok=True)
    summary_output_dir.mkdir(parents=True, exist_ok=True)

    # Reset logs for this run
    fail_log.write_text("")
    missing_fna_log.write_text("")

    # === READ OMES ===
    input_path = Path(args.input)
    omes = read_first_column(input_path)
    if not omes:
        raise SystemExit(f"No OMEs found in first column of: {input_path}")

    print(f"[i] Loaded {len(omes)} OMEs from {input_path}")

    for ome in omes:
        fna = fna_dir / f"{ome}.fna"
        if not fna.exists():
            missing_fna_log.open("a").write(f"{ome}\n")
            print(f"[!] Missing genome FASTA: {fna} (skipping)")
            continue

        # We want BUSCO layout:
        # by_ome/<ome>/<ome>/(logs, run_fungi_odb10, short_summary...)
        ome_parent_dir = busco_output_base / ome
        ome_busco_dir = ome_parent_dir / ome  # where BUSCO actually writes outputs
        final_summary = summary_output_dir / f"{ome}.txt"

        # Expected summary path(s) inside by_ome/<ome>/<ome>/
        # We don't hardcode lineage string in case BUSCO varies slightly.
        expected_summary_glob = f"short_summary.specific.*.{ome}.txt"

        if args.skip_existing:
            existing = list(ome_busco_dir.glob(expected_summary_glob))
            if existing:
                print(f"[i] Skip existing BUSCO summary for {ome}: {existing[0]}")
                continue

        slurm_script_path = script_output_dir / f"{ome}_busco.sh"
        slurm_out = log_output_dir / f"{ome}_%j.out"
        slurm_err = log_output_dir / f"{ome}_%j.err"

        slurm_script = f"""#!/bin/bash
#SBATCH --job-name={ome}_busco
#SBATCH --output={slurm_out}
#SBATCH --error={slurm_err}
#SBATCH --ntasks={slurm_ntasks}
#SBATCH --time={slurm_time}
#SBATCH --mem-per-cpu={slurm_mem_per_cpu}
#SBATCH --partition={slurm_partition}
#SBATCH --account=arsef

set -euo pipefail

module load miniconda/24.7.1-2
source activate {conda_env}

export AUGUSTUS_CONFIG_PATH=$(dirname $(dirname $(which augustus)))/config/

# Create parent dir and run BUSCO from there so it creates nested <ome>/ output
mkdir -p "{ome_parent_dir}"
cd "{ome_parent_dir}"

PYTHONWARNINGS="ignore::SyntaxWarning" \\
busco -i "{fna}" -o "{ome}" -m genome -l "{busco_db}" -c {slurm_ntasks} -f

# Copy summary to shared short_summaries/<ome>.txt for downstream parsing
summary_found=$(ls -1 "{ome_busco_dir}"/short_summary.specific.*.{ome}.txt 2>/dev/null | head -n 1 || true)
if [ -n "$summary_found" ]; then
  cp "$summary_found" "{final_summary}"
else
  echo "BUSCO summary missing for {ome}" >&2
  echo "{ome}" >> "{fail_log}"
fi
"""

        slurm_script_path.write_text(slurm_script)
        print(f"Wrote {slurm_script_path}")

        if args.submit:
            try:
                res = subprocess.run(
                    ["sbatch", str(slurm_script_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"Submitted {ome}: {res.stdout.strip()}")
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to submit {ome}: {e.stderr.strip()}")
                fail_log.open("a").write(f"{ome}\n")

    print(f"[done] Scripts in: {script_output_dir}")
    if missing_fna_log.read_text().strip():
        print(f"[warn] Missing .fna list: {missing_fna_log}")
    if fail_log.read_text().strip():
        print(f"[warn] Failures logged: {fail_log}")


if __name__ == "__main__":
    main()