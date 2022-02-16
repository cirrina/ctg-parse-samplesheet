# ctg-parse-samplesheet

Parse ctg inhouse IEM style SampleSheets for:

The script will i) check and correct some illegal character and file formating errors and ii) check that basic ctg SampleSheet critereas are fullfilled.

The script will generate samplesheets for:

- **ctg-demux2**: One SampleSheet used for bcl2fastq demux of the entire runfolder (named: `SampleSheet-demux-{runfolder}`). The ctg-demux2 script assumes that Illumina `RunFolder` parameter is supplied in SampleSheet `[Header]` section

- **ctg-rnaseq piepeline**: One (or more) project-specific SampleSheets (`SampleSheet-ctg-{ProjectId}.csv`) are generated. These sampleSheets are the primary input for pipelines such as `ctg-rnasq`. Based on the input SampleSheet, the script adds fastq and bam file namings to the `[Data]` section.

The pyton script is executed in conda using a singularity container.  

IEM (Illumina Experiment Manager)

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


## Behaviours and Logics 
Preceedenve
* 1) All blank rows are dropped
* 2. Drop all blank columns. This means that!! for a Header-Data pair, if the header value is specified, but data column is missing - defaults to that the column is left out.
* A param can be set in metadata_foo to add [Data] columns that are not present but their corresponding [Header] is... 
* for [Data] all blank columns are dropped. This means that [Header] may have a value for e.g. that apply for all assays, but then ALL must be blank. A new column will be created only if this row is not present. 
* The script checks if [Data] column exists and then tries to generate a [Header] value.


## DONTS
* enter values for ALL samples or NO samnples (within a singles project). If unknown use NaN.