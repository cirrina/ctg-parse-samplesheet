# ctg-parse-samplesheet

Designed to work with a speicified conda environment provided in singularity container.  

## usage
```
singularity exec \
  --bind /projects/fs1/ \ 
  /projects/fs1/shared/ctg-containers/ctg-parse-samplesheet/singularity-ctg-samplesheet-1.1.sif \
  /projects/fs1/shared/ctg-tools/bin/ctg-parse-samplesheet/1.2/parse-samplesheet.bash \
  -s /home/percebe/tmp/CTG_SampleSheet.2021_148.csv
```