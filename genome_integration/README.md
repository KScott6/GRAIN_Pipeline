# Adding new genome assemblies and annotations to MycoTools (SCINet / ARSEF)

This walkthrough describes how to integrate genome assemblies and annotations into our lab's shared MycoTools database. This walkthrough is designed for SCINet users in the arsef project. If you are not SCINet/arsef, you are much better off learning to use MycoTools from the official [MycoTools tutorials](https://github.com/xonq/mycotools).

---

## Setting up MycoTools 

Skip this step if you are using our shared MycoTools conda environment and shared database.

If you feel like setting up your own MycoTools installation and database, you can follow the following commands. Don't do this if you want to use the lab's MycoTools database. 

Create environment and download software:

```bash
module load miniconda/24.7.1-2

conda config --add channels defaults
conda config --add channels bioconda
conda config --add channels conda-forge
conda config --set channel_priority strict

conda create --prefix /project/arsef/environments/mycotools mycotools
source activate /project/arsef/environments/mycotools
conda update mycotools
mtdb -d
```

<br>

## Downloading new genomes through MycoTools 

Skip this step if you are following the GRAIN pipeline and have your own genome assemblies/annotations in hand already.

MycoTools has the option to download genomes/annotations straight from NCBI and JGI. However, it is limited to only downloading accessions/portals which have BOTH assemblies and annotations. 

Note: I've noticed the stored metadata in some rare NCBI accessions will completely break the download step for MycoTools. Who inserts a "\t" into a metadata field??

When you download genomes from JGI/NCBI, you can either pass a table with all the jgi portal names or NCBI accessions, or just provide a single single portal/accession. This step doesn't add this info to your mtdb yet. It just downloads it locally and makes a premtdb, so you can later add this info to your mtdb. 

Example downloading a single portal from JGI:

```bash
cd /project/arsef/mycotools_test/jgi_download

jgiDwnld -i Ustbr1 -a -g
# then enter the mycotools password
```

This will download the fna and gff for the JGI portal Ustbr1 into /project/arsef/mycotools_test/jgi_download/fna/ and /project/arsef/mycotools_test/jgi_download/gff3/, respectively. 

It will also create a single predb file, with all the paths to the fna and gff, as well as the genus/species info and source: /project/arsef/mycotools_test/jgi_download/Ustbr1.predb.tsv.

You can also download multiple portals at once. First, make a single column datasheet with the column called "assembly_acc". The column contained a list of JGI portals I knew were not use-restricted. 

Example downloading multiple portals from JGI:

```bash
cd /project/arsef/mycotools_test/jgi_download

jgiDwnld -i /project/arsef/mycotools_test/jgi_download/jgi_portals_input.txt -a -g
# then enter the mycotools password
```

Similarly, this downloads all the data into the fna and gff3 folder, and creates a predb file called: /project/arsef/mycotools_test/jgi_download/jgi_portals_input.txt.predb.tsv

You can compile all your predbs into one large predbs, then move forward with one large file, when first initializing a database. 

Note:  You cannot specifiy custom MycoTools ome names when starting a database or adding genomes. 

Starting a new mtdb:

You can start a brand new mtdb by providing either a curated mtdb, or just a predb. Here I provided a predb with genomes I downloaded using jgi_Dwnld, but you can create a mtdb with just your own custom genomes if you want.

```bash
#if you want to make a BRAND NEW mtdb (should only have to do this once if you want to have one giant mtdb)
mtdb update -i /project/arsef/mycotools_test/ --predb /project/arsef/mycotools_test/test_jgi.predb
```

This would create a mtdb in: /project/arsef/mycotools_test/mycotoolsdb/

All the genomic info would be available in: /project/arsef/mycotools_test/mycotoolsdb/data/

Note: based on the weird errors I'm getting, I suspect if you try to cram a predb into the initialization step and you have fna/gff files that "fail", it just will not work. Always initialize with a single genome that you know will pass, then just add the rest with the add commands (where failed genomes are simply ignored instead of stopping the whole process). 

<br>

## Add new genomes/annotations to an already exisiting database

This is how you add your new assemblies and annotations to the lab MycoTools database.

**Important note:** You will need to specify where each new assembly/annotation came from; either from NCBI, JGI, or "new" from your own lab. I have put down all the NCBI assemblies with OUR annotations as "new" and you should do the same.  

If you are adding data to an already-existing mtdb, you need to pre-curate the predb into a mtdb, then provide that mtdb via 'mtdb update'.

```bash
module load miniconda
source activate /project/arsef/environments/mycotools

# IMPORTANT: check you are linked to the mtdb you want to add to
mtdb

#then curate your predb
mtdb predb2mtdb /project/arsef/mycotools_test/jgi_download/Ustbr1.predb.tsv
```

This command would create a mtdb labeled with the date, like:  /project/arsef/mycotools_test/jgi_download/predb2mtdb_20250417/predb2mtdb.mtdb

At this point, check the mtdb and make sure all the data is there and correct.

Then, the admin (Kelsey) will add to the already existing database by providing this mtdb file.

```bash
mtdb update -a /project/arsef/mycotools_test/jgi_download/predb2mtdb_20250417/predb2mtdb.mtdb
```

You will see the metadata in the mtdb (/mtdb/) has been updated, and the new assemblies/annotations have been added to the /data folders. 


## Making modular MycoTools databases

Helpful if you want to run MycoTools commands on different subsets of your genomes.

```bash
module load miniconda/24.7.1-2
source activate /project/arsef/environments/mycotools

mtdb extract --ome -o /project/arsef/projects/hypocreales_tree/standard_dataset_v2/standard_dataset_v2.mtdb
```

<br>

## Other useful MycoTools commands

Getting annotation stats for a mtdb. Very quick!

```bash
annotationStats /project/arsef/databases/mycotools/mycotoolsdb/mtdb/20250708.mtdb > mtdb_annotation_stats.tsv
```

Renaming tips on phylogenetic trees (omes to genus/species names, strains, accessions):

```bash
ome2name concatenated.nex.contree > full_name.newick
```

---

## Other Important Notes

MycoTools automatically edits out whitespaces/special characters/etc in the strain names. Maybe the complex species names as well?

I was having problems because I had changed my JGI login info. I couldn't change the actual contents of my passwords manager with mtdb manage, so I deleted the .mycotools folder in my home folder. This allowed me to re-run the "mtdb manage -p" command and re-set my NCBI and JGI info, as well as make a new mycotools password.

Try as I might, I cannot get any steps that require the MycoTools password to work as a submitted slurm job. Instead, I split large genome submission runs into chunks, then running those chunks one by one on the login node.