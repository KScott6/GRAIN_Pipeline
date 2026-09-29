# GRAIN_Pipeline

Genome Retrieval, Annotation & INtegration. 

A multi-part walkthrough to guide you through using my scripts for the automated bulk download of NCBI genomes, their genome annotation, and incorporating everything into the lab [MycoTools](https://github.com/xonq/mycotools) database.

This walkthrough is designed for SCINet users in the arsef project. 

---

Step 1:  Retrieve genomes

* assemble new genomes from your own WGS data, or
* [download genomes from NCBI](https://github.com/KScott6/GRAIN_Pipeline/blob/main/genome_retrieval/README.md)

Step 2:  Annotate genomes

* [annotate new genomes with Funannotate](https://github.com/KScott6/GRAIN_Pipeline/blob/main/genome_annotation/README.md)

Step 3: Integrate genomes into the MycoTools database

* [upload these new genomes assemblies and annotations into the shared lab MycoTools database](https://github.com/KScott6/GRAIN_Pipeline/blob/main/genome_integration/README_user.md)

Step 4: Extra Analyses (optional)

* [Running extra analyses](https://github.com/KScott6/GRAIN_Pipeline/blob/main/extra_analyses/README.md) is optional, but necessary if you want to use my other pipelines (like [cano.py](https://github.com/KScott6/cano.py))

* includes running software like BUSCO, QUAST, annotationStats (MycoTools)