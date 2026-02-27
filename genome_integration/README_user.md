# Integrating data into MycoTools (SCINet / ARSEF)

This walkthrough describes how to integrate genome assemblies and annotations into our lab's shared MycoTools database. This walkthrough is designed for SCINet users in the arsef project. If you are not SCINet/arsef, you are much better off learning to use MycoTools from the official [MycoTools tutorials](https://github.com/xonq/mycotools).

My documentation for setting up and maintaining the SCINet/ARSEF MycoTools database can be found [here](https://github.com/KScott6/GRAIN_Pipeline/blob/a51cc1b9470d76adadf37f83b2d9cc6fcba7c437/genome_integration/README_admin.md).

---

## Adding custom assemblies/annotations to an already exisiting database

### Step 1 : make the predb

A predb is a tsv file with the accession information, assembly and annotations paths, species information, source, and restricted-use information for each sample. You can make one using the commands from MycoTools yourself, make one yourself (follow (example predb file)[genome_integration/examples/example.predb]), or just use the output predb provided by the GRAIN acqusition or annotation steps. 

**Important note:** You will need to specify where each new assembly/annotation came from; either from "ncbi", "jgi", or "new" from your own lab. I have put down all the NCBI assemblies with OUR annotations as "new" and you should do the same.  

<br>

### Step 2: curate the predb into a mtdb

```bash
module load miniconda
source activate /project/arsef/environments/mycotools

# IMPORTANT: check you are linked to the mtdb you want to add to
mtdb
# should be "/project/arsef/databases/mycotools/mycotoolsdb/mtdb/[date of last update].mtdb"

#then curate your predb
mtdb predb2mtdb [path to .predb]
```

This command will create a mtdb labeled with the date, like:  /project/arsef/mycotools_test/jgi_download/predb2mtdb_20250417/predb2mtdb.mtdb

This step is also standardizing the input files - renaming contigs, files, etc. Strain names will have special characters and whitespaces removed, as will "complex" species names (e.g. "oxysporum f. sp. lycopersici" -> "oxysporumfsplycopersici").

It's pretty fast for individual genomes, about 15-20 seconds per genome on the login node. Adds up quickly though! If you want to incoporate a LOT of genomes (>100), it may be best to split these up into multiple input datasets.

<br>

### Step 3 : integrating the mtdb

At this point, check the mtdb and make sure all the data is there and correct. 

Change permissions on this folder so Kelsey has access. 

Then, the admin (Kelsey) will add to the already existing database by providing this mtdb file.

```bash
mtdb update -a /project/arsef/mycotools_test/jgi_download/predb2mtdb_20250417/predb2mtdb.mtdb
```

You will see the metadata in the mtdb (/mtdb/) has been updated, and the new assemblies/annotations have been added to the /data folders. That's it! Your new genome information has been added to the shared database and you can now run any MycoTools commands you want on these assemblies/annotations. 

However, you still need to add your genome metadata to the MycoTools metadata sheet. This includes information such as basic genome assembly/annotation stats, taxonomy, common NCBI metadata fields, etc. This will help all users select which genomes to include in their analyses in the future.

Additionally, there are many [extra analyses](https://github.com/KScott6/GRAIN_Pipeline/blob/a51cc1b9470d76adadf37f83b2d9cc6fcba7c437/extra_analyses/README.md) you can run with your new genomic information. If you want to run [cano.py](https://github.com/KScott6/cano.py) and make phylogenomic trees with these genomes, you still need to run BUSCO and integrate the results into the database stats folder.



<br>

---

## Downloading new genomes through MycoTools 

Skip this step if you are following the GRAIN pipeline and have your own genome assemblies/annotations in hand already.

MycoTools has the option to download genomes/annotations straight from NCBI and JGI. However, it is limited to only downloading accessions/portals which have BOTH assemblies and annotations. Even if NCBI genomes have annotations, I prefer using my scripts to integrate them into mycotools (vs downloading via mycotools ncbi_dwld), because my scripts prepare the accession metadata for our metadata catalog.

Note: I've noticed the stored metadata in some rare NCBI accessions will completely break the download step for MycoTools. Who inserts a "\t" into a metadata field??

When you download genomes from JGI/NCBI, you can either pass a table with all the jgi portal names or NCBI accessions, or just provide a single single portal/accession. This step doesn't add this info to your mtdb yet. It just downloads it locally and makes a premtdb, so you can later add this info to your mtdb. 

Example downloading a single portal from JGI:

```bash
cd /project/arsef/mycotools_test/jgi_download

jgiDwnld -i Ustbr1 -a -g
# then enter the mycotools password
```

This will download the fna and gff for the JGI portal "Ustbr1" into /project/arsef/mycotools_test/jgi_download/fna/ and /project/arsef/mycotools_test/jgi_download/gff3/, respectively. 

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


---

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
ome2name concatenated.nex.contree > full_name.tree
```

<br>

---

## Other Notes

* You cannot specifiy custom MycoTools ome names when starting a database or adding genomes. 

* MycoTools automatically edits out whitespaces/special characters/etc in the strain names, as wella as complex species names.

* I was having problems because I had changed my JGI login info. I couldn't change the actual contents of my passwords manager with mtdb manage, so I deleted the .mycotools folder in my home folder. This allowed me to re-run the "mtdb manage -p" command and re-set my NCBI and JGI info, as well as make a new mycotools password.

* Try as I might, I cannot get any steps that require the MycoTools password to work as a submitted slurm job. This isn't usually a problem, unless I'm trying to add large numbers of new assemblies/annotations into the databse. I eneded up splitting my large genome submission run into smaller chunks, then running those chunks one by one on the login node.

