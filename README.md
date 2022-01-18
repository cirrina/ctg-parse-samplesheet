# ctg-parse-samplesheet

Tool used for parsing ctg inhouse IEM (Illeumina Experiment Manager) style SampleSheets. 
The script will i) check and correct some illegal character and file formating errors and ii) check that basic ctg SampleSheet critereas are fullfilled. 

The script will generate:

- One SampleSheet used for bcl2fastq demux of the entire runfolder (`SampleSheet-demux-{runfolder}`). The script assumes that Illumina `RunFolder` parameter is supplied in SampleSheet `[Header]` section
- One (or more) project-specific SampleSheets (`SampleSheet-ctg-{ProjectId}.csv`). These sampleSheets are the primary input for pipelines such as 'ctg-rnasq'. Based on the input SampleSheet, the script adds fastq and bam file namings to the `[Data]` section.

The pyton script is executed in conda using a singularity container.  


## usage
```
singularity exec \
  --bind /projects/fs1/ \ 
  /projects/fs1/shared/ctg-containers/ctg-parse-samplesheet/singularity-ctg-samplesheet-1.1.sif \
  /projects/fs1/shared/ctg-tools/bin/ctg-parse-samplesheet/1.2/parse-samplesheet.bash \
  -s /home/percebe/tmp/CTG_SampleSheet.2021_148.csv
```

## Dependecies

The python script is built for Python 3.7 or above.




## Script folder structure 


## Singularity container

The bash script will execute the python script using a singularity container conda environment with python 3.9.4.


### Build container
The container is buit on ldb server:

```
singularity build --fakeroot singularity-ctg-parse-samplesheet.sif singularity-parse-samplesheet.def
```

### Containers on lsens-4 

```
projects/fs1/shared/ctg-containers/ctg-parse-samplesheet/singularity-ctg-samplesheet-1.1.sif
```

