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

---

## QUAST 

---

## annotationStats

---

## BUSCO (fungi)

I have made a [script](extra_analyses/scripts/make_busco_fungi_scripts.py) that automatically takes either 1) the mtdb produced when you run predb2mtdb, 2) a list of ome codes, or 3) literally any tsv/csv whose first column is a list of ome codes (no header). This script will then run a BUSCO analysis (fungi_osb10) on each genome and the output will automatically be formatted for use in cano.py (you will still need to do extra steps to integrate the BUSCO output into the metadata catalog).

```bash
module load miniconda

/project/arsef/databases/mycotools/database_stats/busco/fungi/make_busco_fungi_scripts.py -i /project/arsef/databases/mycotools/split_predb/predb2mtdb_20260226/predb2mtdb.mtdb --submit --skip-existing
```

Leave off the "--submit" if you want to preview the created BUSCO job scripts without running them. 

If "--skip-existing" is specified, the script will skip any ome that already has a short summary file in :short_summary in /project/arsef/databases/mycotools/database_stats/busco/fungi/by_ome/<ome>/<ome>/

This script will log any ome that did not successfully complete the BUSCO analyses, so that you can re-run them with more time/RAM. 

After all the BUSCO jobs have completed, now you can parse the BUSCO txt output with the BUSCO parsing script:

```bash
python /project/arsef/databases/mycotools/database_stats/busco/fungi/parse_busco_summaries.py
```

This will automatically parse the folder with all the collected BUSCO results (/project/arsef/databases/mycotools/database_stats/busco/fungi/short_summaries) and compile all the info for every ome into a single file. If you don't see your ome in that file, it means either the BUSCO run was unsucessful, or the final summary file was not copied over (known issue for some omes, not sure why).


---

## Integrating metadata into metadata catalog

Here is how I integrate the results from the extra analyses into the metadata catalog. This can be done all at once, for all necessary analyses, or it can be performed after every analysis. In any case, this script will avoid overwriting any data that is already in the catalog. It will only ever submit information to a completely empty field. 

```bash
python /project/arsef/databases/mycotools/scripts/submit_metadata.py --metadata /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_07.08.25.csv   --busco /project/arsef/databases/mycotools/database_stats/busco/fungi/busco_summary_table.csv
```

Options:

`--metadata` Path to the CURRENT metadata catalog

`--quast` Path to the QUAST output for your new samples

`--ncbi_data` Path to the ncbi metadata

`--taxonomy` Path to the taxonomy output

`--busco` Path to the output of the parse_busco_summaries.py script. By default, should be "/project/arsef/databases/mycotools/database_stats/busco/fungi/busco_summary_table.csv"

`--annotationStats` Path to the output of MycoTools' annotationStats command. 


This command will generate a new metadata catalog with the suffix ".merged". You should check this new file, making sure everything looks good. Once verified, you can rename this new file with the current date - **this is now the current version of the metadata catalog**. Move the old version of the catalog into: /project/arsef/databases/mycotools/outdated_metadata_catalogs

