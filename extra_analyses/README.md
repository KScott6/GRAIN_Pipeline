# Extra analyses for genomes in the MycoTools database

Your genome assemblies and annotations are curated and safely stored in the lab's shared MycoTools database - great! There are so many analyses you can automatically perform within MycoTools now. 

But there are some basic analyses that still need to be run so that you can fully populate the metadata catalog with the proper information. This includes:

1) QUAST (genome assembly statistics)

2) annotationStats (genome annotation statistics)

3) BUSCO (to assess genome completeness, as well as use the identified BUSCOs in cano.py)

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

```


