# Extra analyses for genomes in the MycoTools database

Your genome assemblies and annotations are curated and safely stored in the lab's shared MycoTools database - great! There are so many analyses you can automatically perform within MycoTools now. 

We have a metadata catalog for the MycoTools database, marked with the date it was last updated (example at time of writing this:  /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_07.08.25.csv). You should only ever use the most up-to-date version of this catalog, for any purpose. 

When you submit genomic information into the MycoTools database, the database itself has only a few metadata fields (strain name, species name, etc.), which isn't enough for many of our uses (host data, other taxonomy fields, BUSCO, etc.). So it's essential that we keep the metadata catalog up to date with the MycoTools database.

Here are the basic analyses that still need to be run so that you can fully populate the metadata catalog with the proper information. This includes:

1) BUSCO (to assess genome completeness, as well as use the identified BUSCOs in cano.py)

2) QUAST (genome assembly statistics)

3) annotationStats (genome annotation statistics)

The metadata for each NCBI accession should also be uploaded to this database. 

This walkthrough will show you how to run all of these analyses automatically, then integrate this metadata into the metadata catalog. 

<br>

---

## BUSCO (fungi)

The make_busco_fungi_array.py script automatically generates and submits SLURM job arrays to run BUSCO analyses on fungal genomes in the MycoTools database. The BUSCO results are then automatically compiled into the combined metadata table. By default, the script skips genomes that already have valid BUSCO summary files stored in /project/arsef/databases/mycotools/database_stats/busco/fungi/short_summaries/. This script will automatically delete the very large busco miniprot logs files upon successful completion. 

The script accepts either:

1) An .mtdb file produced by predb2mtdb, using --mtdb.

2) A text file containing a list of OME codes, one per line, using -i.

3) A headerless TSV file whose first column contains OME codes, using --mtdb.

The script runs BUSCO in genome mode using fungi_odb10 on each genome. Th fungal_odb10 dataset is hard-coded because cano.py depends on the BUSCO results all using the same reference database. **Do not change the BUSCO dataset.** If you need to use a different BUSCO lineage dataset, generate separate BUSCO commands.

Each OME is assigned to an individual task within a SLURM array. By default, the script allows 25 tasks to run concurrently.

<br>

To generate and automatically submit a BUSCO array from an MTDB file:

```bash
module load miniconda

python3 /project/arsef/databases/mycotools/scripts/make_busco_fungi_array.py \
    --mtdb /project/arsef/databases/mycotools/split_predb/predb2mtdb_20260701/predb2mtdb.mtdb \
    --run-name busco_new_genomes \
    --threads 16 \
    --mem 96G \
    --time 12:00:00 \
    --concurrency 25 \
    --submit
```

Alternatively, to use a list of OME codes:

```bash
python3 /project/arsef/databases/mycotools/scripts/make_busco_fungi_array.py \
    -i /path/to/ome_list.txt \
    --run-name busco_ome_list \
    --submit
```

Options:

`--mtdb`  Input MTDB file containing OME codes in its first column.

`-i` or `--ome-list`  Input text file containing OME codes.

`--submit`  Automatically submit the BUSCO array and its dependent summary-merging job.

`--run-name`  Name assigned to the array run. If omitted, a timestamped name is generated.

`--rerun` Rerun BUSCO even if an existing valid summary is present.

`--skip-existing` If specified, the script will skip any ome that already has a short summary file in :short_summary in /project/arsef/databases/mycotools/database_stats/busco/fungi/by_ome/<ome>/<ome>/

`--threads` Number of CPUs allocated to each array task (default: 16).

`--mem` Total memory allocated per array task (default: 96G).

    * Note : complicated, large, or low-quality genomes can consume a LOT of memory. Try with the default memory limit initally, then increase until the job successfully completes. I 1 TB memory is where I personally give up on any given genome.

`--time` Maximum runtime per task (default: 12:00:00).

`--concurrency` Maximum number of array tasks running simultaneously (default: 25).

`--merge-only`  Rebuild the combined BUSCO summary table from all existing individual summaries without running BUSCO again.


The script generates a new directory for each run under:

/project/arsef/databases/mycotools/database_stats/busco/fungi/array_runs/<run_name>/

This directory contains the OME manifest, generated SLURM scripts, lists of skipped genomes, and the submitted job IDs. If --submit is not specified, the scripts are generated but no jobs are submitted.

<br>

---

## QUAST 

QUAST calculates basic genome assembly statistics, including N50, N90, total assembly length, GC%, contig counts, and other assembly quality metrics.

The make_quast_array.py script generates SLURM job arrays to run QUAST on multiple genomes in parallel and compiles the completed results into a single summary file. Duplicated genomes will automatically be skipped.

The script accepts two types of input:

1) -i or --ome-list: A text file containing ome codes, one per line.

2) --mtdb: A MycoTools .mtdb file, such as the database generated when integrating new genomes. The script extracts ome codes from the first column.

To run QUAST on genomes from a MycoTools .mtdb file:

```bash
python /project/arsef/databases/mycotools/scripts/make_quast_array.py \
  --mtdb /project/arsef/databases/mycotools/mycotoolsdb/mtdb/20261023.mtdb \
  --run-name quast_update_01 \
  --concurrency 25 \
  --threads 4 \
  --time 04:00:00 \
  --submit
```

Options: 

`-i , --ome_list` Input text file containing ome codes, one per line.

`--mtdb` Input MycoTools .mtdb file. Ome codes are extracted from the first column.

`submit` Automatically submits the QUAST array and schedules the report compilation job.

`--run-name` Name assigned to the QUAST run and its output directory (Default: timestamp name).

`--concurrency` Maximum number of QUAST array tasks running simultaneously (Default: 25).

`--threads` Number of CPUs allocated to each QUAST task (Default: 4)

`--rerun` Reanalyzes selected genomes even when valid QUAST reports already exist.

Individual QUAST analyses are stored in: /project/arsef/databases/mycotools/database_stats/quast/by_ome/<OME>/

Individual reports are stored in: /project/arsef/databases/mycotools/database_stats/quast/individual_reports/<OME>_transposed_report.tsv

If any genomes in the submitted array fail to produce a valid report, their ome codes are recorded in: .../array_runs/<RUN_NAME>/missing_reports.txt

QUAST report compilation is completely automated. When the job is submitted with --submit, a secondary slurm job is scheduled for when all the QUAST jobs complete. This job will merge all the results, both old and new, into the maseter quast results file:  /project/arsef/databases/mycotools/database_stats/quast/quast_summary_combined.tsv

<br>

---

## annotationStats

There is a MycoTools function which calculates annotation statistics, including gene counts, CDS counts, transcript lengths, and other annotation metrics. The prepare_annotation_stats script will automatically create slurm jobs to easily run this command on any genome added into the database. 

The script will:

1) Read the current MycoTools database and compare its ome codes against the existing annotationStats master file.
2) Identify genomes that have not yet been analyzed.
3) Divide the new genomes into batches of 100.
4) Automatically submit a SLURM job array to calculate annotation statistics.
5) Schedule a separate SLURM job to validate and merge the results once the array finishes.
6) Back up the existing master file before adding any new results.

If all genomes have already been analyzed, the script exits without submitting any jobs.

```bash
python /project/arsef/databases/mycotools/scripts/update_annotation_stats.py \
  --mtdb /project/arsef/databases/mycotools/mycotoolsdb/mtdb/20261023.mtdb
```

`--mtdb`  Path to the MycoTools database to analyze. Required for a new run.

`--batch-size`  Number of genomes processed per SLURM array task (Default: 100).

`--cpus`  CPUs per slurm job. Also controls how many mycotools:annotationStats worker processes (Default: 2).

`--mem` Memory allocated per slurm job (Default: 16G).

`--concurrency `  Max number of array tasks running simultaneously (Default: 10).

`--resume`  Resume a previous run, rerunning only batches with missing or invalid results.

`--merge` Validate and merge results from an existing run. Normally called automatically by the SLURM merge job, but if a run fails you should resume the run and specify --merge.

The permanent annotationStats master file is located at:  /project/arsef/databases/mycotools/database_stats/annotation_stats/mtdb_annotation_stats_master.tsv


<br>

---


## Integrating metadata into metadata catalog

Here is how I integrate the results from the extra analyses into the metadata catalog. This can be done all at once, for all necessary analyses, or it can be performed after every analysis. In any case, this script will avoid overwriting any data that is already in the catalog. It will only ever submit information to a completely empty field (except for the NCBI taxnomy field, which is able to be overwritten in case of taxonomy updates).

This command will generate a new metadata catalog with a custom name of your choosing. You should check this new file, making sure everything looks good. Once verified, you can rename this new file with the current date - **which then becomes the current version of the metadata catalog**. Move the old version of the catalog into: /project/arsef/databases/mycotools/outdated_metadata_catalogs

```bash
python /project/arsef/databases/mycotools/scripts/submit_metadata.py \
  --metadata /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.06.26.csv \
  --mtdb /project/arsef/databases/mycotools/mycotoolsdb/mtdb/20260307.mtdb \
  --quast /project/arsef/databases/mycotools/database_stats/quast/quast_summary_combined.tsv \
  --busco /project/arsef/databases/mycotools/database_stats/busco/fungi/busco_summary_table.csv \
  --ncbi_metadata /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/ncbi_metadata_by_taxa_py/new_genomes.taxa.NEW_ONLY.tsv \
  --annotation_stats /project/arsef/databases/mycotools/database_stats/annotation_stats/mtdb_annotation_stats_03.11.26.tsv \
  --add_taxonomy \
  --entrez_email your_email@institution.edu \
  --entrez_api_key YOUR_NCBI_API_KEY \
  --out /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.06.26.taxonomy.csv
```

Options:

`--metadata` Path to the CURRENT metadata catalog

`--mtdb` Path to the CURRENT MycoTools database mtdb file

`--quast` Path to the output of the parse_busco_summaries.py script. By default, should be "/project/arsef/databases/mycotools/database_stats/quast/quast_summary_combined.tsv". You need to have run the "parse_quast_report.py" script to get an updated quast results sheet first!

`--busco` Path to the output of the parse_busco_summaries.py script. By default, should be "/project/arsef/databases/mycotools/database_stats/busco/fungi/busco_summary_table.csv". You need to have run the "parse_busco_summaries.py" script to get an updated busco results sheet first!

`--ncbi_metadata` Path to your ncbi metadata file (usually obtained in the GRAIN Retrieval step)

`--annotation_stats` Path to the output of MycoTools' annotationStats command

`--add_taxonomy` include this flag if you want to fill in the columns for phylum, class, order, and family. Requires a entrez email with "--entrez_email" and is greatly benefitted by supplying your NCBI API key with "--entrez_api_key"

`--entrez_email` provide your entrez email to obtain taxonomy via NCBI

`--entrez_api_key` (optional) Provide your NCBI API key to greatly speed up taxonomy lookup

<br>

Updating the metadata catalog can take a really long time, espcially if you're trying to integrate large amounts of new metatdata. You can speed things up by only integrating one type of metadata at a time:

```bash
python /project/arsef/databases/mycotools/scripts/submit_metadata.py \
  --metadata /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.11.26.csv \
  --busco /project/arsef/databases/mycotools/database_stats/busco/fungi/busco_summary_table.csv \
  --out /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.11.26.busco.csv
```

<br>

---


# Other fun scripts

Here are a few other scripts that work with the GRAIN/MycoTools workflow. 

## Make custom tree labels

Input must be tree (.tree, .newick) with only OME codes as tip labels. This script depends on the requested information being present in the supplied metadata catalog file. You can specify any of these fields, in any order, to get your tree labels.  If you put "assembly_acc", it will include the corresponding NCBI accessions, JGI portal, or your custom specified name (for custom-made genome assemblies/annotations).

```bash
python /project/arsef/databases/mycotools/scripts/add_taxonomy_to_tree.py \
    -i /project/arsef/projects/asilomar_project/canopy/prelim/final_tree/final_tree.contree \
    --fields genus,species \
    --catalog /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.09.26.csv \
    -o /project/arsef/projects/asilomar_project/canopy/prelim/final_tree/asilomar_prelim_final_tree_tax_short.tree
```
    