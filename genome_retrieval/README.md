# NCBI genome retrieval

This walkthrough describes how to download genome assemblies, optional annotation files, and structured metadata from NCBI in bulk. This is the first step to incorporating public genome data into our lab's shared MycoTools database. 

This walkthrough will assume you are on the arsef SCINet project and are trying to download to our shared genome database, but you can make this work for your own purposes with minimal changes. 

Ideally, we would use MycoTools to directly download NCBI accessions of interest. However, MycoTools does not automatically store as much metadata as I'd like, and it only incorporates entries that have both an assembly and a corresponding annotation file. So we need to perform this workaround instead.

Please be aware of any limitations/restrictions on any of the NCBI accessions you want to incorporate. 

<br> 

You will provide:

1) A list of taxon names OR a list of NCBI assembly accessions

2) the current version of the MycoTools metadata database
   

And the scripts in this walkthrough will:

1) Pull requested genomes from NCBI (while verifying they are not duplicates of a genome already in the database) 

2) Retrieve structured metadata for each accession and append the metadata from the new genomes into a shared metadata file. 

<br>

---

<br>

## Step 1 - get a list of new genome accessions to download

You will need access to the ncbi_datasets software. If you are on SCINet you can use the shared ncbi_datasets conda environment. If you are doing your own independent genome pull, you need to make your own ncbi_datasets conda environment.

With the fetch_ncbi_metadata_and_merge.py script, you will provide either a list of taxa or a list of accessions (txt or csv). 

If you provide the path to the lab's genome metadata catalog (make sure you're using the most recent version!), the script will automatically deduplicate any incoming genome data. If you do NOT provide a link to a metadata sheet, the script will fetch metadata for any genome matching your desired taxa/accessions, without performing deduplication.

I like to organize all the genome retrieval output in the ./bulk_genome_annotation/genome_retrieval folder, separated by data of retrieval.
```bash
mkdir /project/arsef/projects/bulk_genome_annotation/genome_retrieval/3.12.26
cd /project/arsef/projects/bulk_genome_annotation/genome_retrieval/3.12.26
```

Use the fetch_ncbi_metadata_and_merge.py to take incoming search parameters (taxa names or accessions) and prepare for the download. You can give a custom prefix to your output files with --prefix.

You can provide a csv or txt file that is a single-column list of taxa names (e.g. Ambrosiella, Fusarium virguliforme, etc.), like so:

```bash
module load miniconda
source activate /project/arsef/environments/ncbi_datasets

python /project/arsef/scripts/fetch_ncbi_metadata_and_merge.py \
  --taxa_file /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/desired_taxa.txt \
  --master_metadata /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_07.08.25.csv \
  --outdir /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/ncbi_metadata_by_taxa_py \
  --prefix new_genomes \
  --write_all_fetched
```

Or you can provide a csv or txt file that is a single-column list of NCBI accessions:

```bash
python /project/arsef/scripts/fetch_ncbi_metadata_and_merge.py \
  --accessions_file /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/desired_accessions.txt \
  --master_metadata /project/arsef/databases/mycotools/MTDB_metadata_COMPLETE_07.08.25.csv \
  --outdir /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/ncbi_metadata_by_acc \
  --prefix new_genomes \
  --keep_raw_organism_name \
  --write_all_fetched
```


```bash
python /project/arsef/scripts/fetch_ncbi_metadata_and_merge.py \
  --accessions_file /project/arsef/projects/bulk_genome_annotation/genome_retrieval/metadata_update/accession_list.txt \
  --outdir /project/arsef/projects/bulk_genome_annotation/genome_retrieval/metadata_update \
  --prefix metadata_update \
  --keep_raw_organism_name \
  --write_all_fetched
```


`--keep_raw_organism_name` keeps the raw "organism" name reported by NCBI. Recommended to use this flag, for recordkeeping purposes. 

Either option will result in several output files:

1) <prefix>.<accessions/taxa>.ALL_FETCHED.tsv : all of the accessions in NCBI that match your search parameters.
   
2) <prefix>.<accessions/taxa>.MASTER_UPDATED.csv : an unpolished but updated metadata file that includes all the old genomes info, as well as any new unique genome accessions and their metadata. 
   
3) <prefix>.<accessions/taxa>.NEW_ONLY.tsv : a list of the accessions that passed the deduplication step.

Take a look at the <prefix>.<accessions/taxa>.NEW_ONLY.tsv file. If you don't want to progress with any specific accession, you can simply delete that row from this file, save the file, and progress in this pipeline.


### dealing with accessions that already have annotations

(Note: if your accessions already have associated annotations, nothing is stopping you from directly downloading them to the MycoTools database via MycoTools itself. If you do the downloading via Mycotools, you still need to download the extra metadata for the metadata catalog.)

If some of your accessions already have annotations - great! You don't have to worry about annotating them yourself, if you don't want. You can move these already-annotated accessions into their own folder, so they don't get in the way. 

```bash
python /project/arsef/scripts/move_annotated_genome.py \
  --src /project/arsef/projects/bulk_genome_annotation/needs_annotation/3.2.26/ncbi_metadata_by_taxa_py/ncbi_downloads \
  --dest /project/arsef/projects/bulk_genome_annotation/needs_annotation/3.2.26/already_annotated
```

The --src folder needs to have a /fna and /gff subfolder; if an accession has both a .fna and a .gff, it will be moved into the folder you specified with --dest.

Then, you can make a predb file for the annotated accessions like this:

```bash
python /project/arsef/scripts/make_predb_from_downloads.py \
  --fna_dir /project/arsef/projects/bulk_genome_annotation/needs_annotation/3.2.26/already_annotated/fna \
  --gff_dir /project/arsef/projects/bulk_genome_annotation/needs_annotation/3.2.26/already_annotated/gff \
  --metadata /project/arsef/projects/bulk_genome_annotation/needs_annotation/3.2.26/ncbi_metadata_by_taxa_py_OLD/new_genomes.taxa.NEW_ONLY.tsv \
  --out /project/arsef/databases/mycotools/split_predb/3.2.26.predb.tsv
```

Then contact the MycoTools database admin (Kelsey) so she can incorporate your new accessions into the database. 

<br>

## Step 2 - download the genome assemblies (optionally, their annotations as well)

Now you can provide the <prefix>.<accessions/taxa>.NEW_ONLY.tsv file to the download_ncbi_batches.py script. This script will download these new accessions will automatically. You will probably want to run this step as a job if you are downloading a large number of accessions.

Note that the --with_annotation flag controls whether annotation files are requested. All genome assemblies are downloaded regardless.

You will also need to provide a path to the output folder you want to create and download to - this output folder is created automatically.

Here is an example command where I provide the NEW_ONLY.tsv output from my first command, and point the output to a folder I want to make in the bulk genome annotation folder. Make sure to provide your NCBI API key. 

```bash
source activate /project/arsef/environments/ncbi_datasets # activate ncbi_datasets environment if it's not already activated

python /project/arsef/scripts/download_ncbi_batches.py \
  --metadata /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/ncbi_metadata_by_taxa_py/new_genomes.taxa.NEW_ONLY.tsv \
  --outdir /project/arsef/projects/bulk_genome_annotation/needs_annotation/1.14.26/ncbi_downloads \
  --with_annotation \
  --api_key "ABC12345667789" # include your API key
```

Options:

`--metadata` Provide the full path to the <prefix>.<accessions/taxa>.NEW_ONLY.tsv file generated by fetch_ncbi_metadata_and_merge.py OR any csv/tsv file that contains a list of NCBI accessions you want. This option assumes the name of the column containing the accessions is called "assembly_acc" (see --accession_col).

`--accession_col` If you are providing some random file of NCBI accessions and the header is NOT "assembly_acc", put your header here. 

`--outdir` Full path to your desired output directory.

`--sleep` How many seconds to wait between NCBI queries (default: 10). If you are having issues with downloading, try increasing this value!

`--chunk_size` How many accessions in each chunk your are querying to NCBI. If you are having issues with downloading, try lowering this value!

`--api_key` Provide your NCBI API key for reduced download limits.

`--with_annotation` Use this flag if you want to download annotation files as well as assembly files.

`--resume` Use this flag if you want to manually re-start a download. Will automatically skip accessions you successfully downloaded.

`--retries` How many times you want to try an automatic re-start of failed accession downloads (default: 3 attempted retries).


Congrats! Running this script should result in your genomes and annotations being downloaded in one place. The genome assemblies will be in the "fna" folder and if there were any annotations, they will be in "gff". 

You probably want to annotate your assemblies now - check out the [SCINet Funannotate walkthrough](https://github.com/KScott6/GRAIN_Pipeline/blob/8f5853107a8a3672ca51db8a4620887c31376b93/genome_annotation/README.md) to get one step closer to incorporating these genomes into the lab MycoTools database. 

<br>

Notes:

If you are downloading many accessions, you should probably submit this as a job. If you run into any issues with this step, there are many helpful log files that are generated in your specified output folder. 

Although there were no explicitly stated NCBI genome download limits, I started to get intermittent download denials around my 1000th accession and I got completely cut off around my 25000th accession. Between the cutoffs and the occasional normal download failures, it took three attempts to download all the genomes from my list of 5438 accessions.

Of the 5438 genomes I downloaded, only 1447 had associated annotation files (~26%). All data downloaded for these accessions (faa, gff, fna, etc) was only 327GB.

There are a few discrepancies (<30 accessions) between the initial list of accessions I thought I would have and my final list of accessions. I suspect this may be due to different versions of genomes, or version reporting errors. There are so many opportunities where a genome can fall through the cracks in this pipeline - if this ever got to be a more polished workflow this would need to have many extra checks.