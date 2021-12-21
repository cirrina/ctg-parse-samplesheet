#!/bin/bash
echo " ----------------------- "
echo " ctg SampleSheet Parser  "
echo " ----------------------- "
echo " parses & checks samplesheet into demux-ready sheet to use with ctg-demux script"
echo " parses & checks samplesheet into demux-ready sheet "
python --version
source ~/miniconda3/etc/profile.d/conda.sh
# conda init bash
conda activate ctg-parse-samplesheet
python --version
echo " Running python script: parse-sampelsheet.py"
python parse-samplesheet.py /Users/david/scripts/ctg-parse-samplesheet/SampleSheet-2021_145.csv
