# Setting up MycoTools (SCINet / ARSEF)

This is my documentation for setting up our MycoTools database, specific to SCINet/ARSEF. If you are a member of ARSEF project and want to use the lab's shared database, you should not follow this walkthrough. Read the [SCINet/ARSEF MycoTools user walkthrough](https://github.com/KScott6/GRAIN_Pipeline/blob/a51cc1b9470d76adadf37f83b2d9cc6fcba7c437/genome_integration/README_user.md) instead.

To learn the basics of MycoTools, it's best to use the official [MycoTools tutorials](https://github.com/xonq/mycotools).

---

## Setting up MycoTools 

Creating environment and download software:

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

---

## Starting a new mtdb:

You can start a brand new mtdb by providing either a curated mtdb, or just a predb. Here I provided a predb with genomes I downloaded using jgi_Dwnld, but you can create a mtdb with just your own custom genomes if you want.

```bash
#if you want to make a BRAND NEW mtdb (should only have to do this once if you want to have one giant mtdb)
mtdb update -i /project/arsef/mycotools_test/ --predb /project/arsef/mycotools_test/test_jgi.predb
```

This would create a mtdb in: /project/arsef/mycotools_test/mycotoolsdb/

All the genomic info would be available in: /project/arsef/mycotools_test/mycotoolsdb/data/

Note: based on the weird errors I'm getting, I suspect if you try to cram a predb into the initialization step and you have fna/gff files that "fail", it just will not work. Always initialize with a single genome that you know will pass, then just add the rest with the add commands (where failed genomes are simply ignored instead of stopping the whole process). 

Note: I had some issues with starting a mtdb with only custom/lab-generated genomes. 