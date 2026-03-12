# Extra analyses for genomes in the MycoTools database

Your genome assemblies and annotations are curated and safely stored in the lab's shared MycoTools database - great! There are so many analyses you can automatically perform within MycoTools now. 

We have a metadata catalog for the MycoTools database, marked with the date it was last updated (example at time of writing this:  /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_07.08.25.csv). You should only ever use the most up-to-date version of this catalog, for any purpose. 

When you submit genomic information into the MycoTools database, the database itself has only a few metadata fields (strain name, species name, etc.), which isn't enough for many of our uses (host data, other taxonomy fields, BUSCO, etc.). So it's essential that we keep the metadata catalog up to date with the MycoTools database.

Here are the basic analyses that still need to be run so that you can fully populate the metadata catalog with the proper information. This includes:

1) QUAST (genome assembly statistics)

2) annotationStats (genome annotation statistics)

3) BUSCO (to assess genome completeness, as well as use the identified BUSCOs in cano.py)

The metadata for each NCBI accession should also be uploaded to this database. 

This walkthrough will show you how to run all of these analyses automatically, then integrate this metadata into the metadata catalog. 

<br>

---

## QUAST 

The software QUAST generates basic genome statistics (N50, genome length, GC%, etc). 

The generate_quast_jobs.py script will generate and submit individual QUAST analyses on any given genome already in MycoTools. This script will take either:

1) a file containing a list of ome codes (--ome_list), or

2) the mtdb used to integrate the omes into the MycoTools database (--mtdb), or

3) a command telling QUAST to run on all genomes in the MycoTools catalog that do not have QUAST results yet (--all_missing_quast).

```bash
python /project/arsef/databases/mycotools/scripts/generate_quast_jobs.py \
    --ome_list omes.txt \
    --catalog /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.09.26.csv \
    --output_base /project/arsef/databases/mycotools/database_stats/quast \
    --script_dir /project/arsef/databases/mycotools/database_stats/quast/__quast_scripts \
    --log_dir /project/arsef/databases/mycotools/database_stats/quast/__quast_logs

python /project/arsef/databases/mycotools/scripts/generate_quast_jobs.py \
    --all_missing_quast \
    --catalog /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_03.09.26.csv \
    --output_base /project/arsef/databases/mycotools/database_stats/quast \
    --script_dir /project/arsef/databases/mycotools/database_stats/quast/__quast_scripts \
    --log_dir /project/arsef/databases/mycotools/database_stats/quast/__quast_logs
```

`--ome_list` Flag used to specify a single-column ome list input (.txt, .tsv, .csv...)

`--mtdb` Flag used to specify a .mtdb file input

`--all_missing_quast` Include this flag if you want to run QUAST on all genomes in the database that do not have QUAST metadata yet. 

`--no_submit` Include if you want to inspect the generated quast jobs instead of automatically submitting them.

After all the QUAST jobs have completed, now you need to parse the QUAST transposed reports with the QUAST parsing script:

```bash
python /project/arsef/databases/mycotools/scripts/parse_quast_reports.py
```

This script will automatically parse the folder with all the collected QUAST results (/project/arsef/databases/mycotools/database_stats/quast/individual_reports) and compile all the transposed reports into a single report file (/project/arsef/databases/mycotools/database_stats/quast/quast_summary_combined.tsv). This report will contain ALL the QUAST results of previous runs, as well as your most recently submitted jobs.

Helpful logs of the missing reports/errors can be found here: /project/arsef/databases/mycotools/database_stats/quast/

<br>

---

## annotationStats

There is a built-in function in MycoTools that calculates annotation statistics. 

Point it at the whole MycoTools database to get the updated information. Make sure to provide the most up-to-date version of the MycoTools mtdb.

This may take a few minutes on the login node (~5 minutes), especially if you're running it on the whole database.

```bash
source activate /project/arsef/environments/mycotools/

annotationStats /project/arsef/databases/mycotools/mycotoolsdb/mtdb/20260307.mtdb > /project/arsef/databases/mycotools/database_stats/annotation_stats/mtdb_annotation_stats_03.11.26.tsv

```

<br>

---

## BUSCO (fungi)

I have made a [script](extra_analyses/scripts/make_busco_fungi_scripts.py) that automatically takes either 

1) the mtdb produced when you run predb2mtdb, or

2) a file containing a list of ome codes, or 

3) literally any tsv/csv whose first column is a list of ome codes (no header). 

This script will then run a BUSCO analysis **(fungi_odb10)** on each genome. The fungi_odb10 is the hard-coded default because cano.py depends on these BUSCO results all using the same BUSCO database. Do not attempt to change the BUSCO dataset in this command. If you need to run a different BUSCO dataset on your genomes, you need to generate your own BUSCO commands.

```bash
module load miniconda

python3 /project/arsef/databases/mycotools/scripts/make_busco_fungi_scripts.py -i /project/arsef/databases/mycotools/problem_busco_omes.txt --submit --skip-existing
```

Leave off the "--submit" if you want to preview the created BUSCO job scripts without running them. 

If "--skip-existing" is specified, the script will skip any ome that already has a short summary file in :short_summary in /project/arsef/databases/mycotools/database_stats/busco/fungi/by_ome/<ome>/<ome>/

This script will log any ome that did not successfully complete the BUSCO analyses, so that you can re-run them with more time/RAM. 

After all the BUSCO jobs have completed, now you need to parse the BUSCO txt output with the BUSCO parsing script:

```bash
python /project/arsef/databases/mycotools/scripts/parse_busco_summaries.py
```

This will automatically parse the folder with all the collected BUSCO results (/project/arsef/databases/mycotools/database_stats/busco/fungi/short_summaries) and compile all the info for every ome into a single file. If you don't see your ome in that file, it means either the BUSCO run was unsucessful, or the final summary file was not copied over (known issue for some omes, not sure why).

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
  --entrez_email your_email@cornell.edu \
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
    