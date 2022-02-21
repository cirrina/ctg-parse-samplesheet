#!/bin/bash

echo " ----------------------- "
echo " ctg SampleSheet Parser  "
echo " ----------------------- "
echo " ... "
echo " check & parse samplesheet into demux-ready sheet - to use with ctg-demux script"
echo " ... "
echo " ... checking input args ..."

singularity_contatiner="/projects/fs1/shared/ctg-containers/ctg-parse-samplesheet/singularity-ctg-samplesheet-1.x.sif"

## Uncomment two lines below to run python shell script on local machine macOS
#source ~/miniconda3/etc/profile.d/conda.sh ## Needed to run at local
#conda activate ctg-parse-samplesheet


forcesamplename="True"
fastqsuffix="_001.fastq.gz"
bamsuffix="_Aligned.sortedByCoord.out.bam"
forcefastqnames="False"
forcebamnames="False"
allowdupsoverlanes="True"
collapselanes="True"

# usage message
usage() {
    echo ""
    echo " usage : "
    echo " parse-samplesheet [ -s samplesheet ] .... "  1>&2
    echo ""
    echo " arguments : "
    echo " samplesheet         -s : IEM style laboratory SampleSheet. Project and pipeline specific parameters must be added. "
    echo " forcesamplename     -x : Default 'True'. Set flag for 'False'. if to force Sample_Name(s) supplied in [Data] column to the same as Sample_ID"
    echo " fastqsuffix         -f : Default '_001.fastq.gz'. Suffix needed to auto-generate fastq file names generated by bcl2fastq. If NULL no bam file names will be genrerated"
    echo " bamsuffix           -b : Default '_Aligned.sortedByCoord.out.bam'. Suffix needed to auto generate bam file names (typically generated by STAR). If NULL no bam file names will be genrerated"
    echo " forcefastqnames     -g : Default 'False'. Set flag for 'True'. If to overwrite fastq filenames. By defualt (fastq_1/fastq_2) columns will not be overwritten if present (even though fastq_suffix is supplied)"
    echo " forcebamnames       -c : Default 'False'. Set flag for 'True'. If to overwrite bam filenames. By defualt (bam) column will not be overwritten if present (even though bam_suffix is supplied)"
    echo " allowdupsoverlanes  -d : Default 'True'. Set flag for 'False'. If to allow duplicates (within one project) on multiple lanes. Rare on NovaSeq but can be found for S4 with lane divider. One sample may be run on both lane 1/2 or on 3/4."
    echo " collapselanes       -e : Default 'True'. Set flag for 'False'. Like allow_dups_over_lanes, affects project specific samplsheets NOT demux sheet.  special cases - when a single (same) sample is present in multiple lanes AND --noLaneSplitting is True in bcl2fastq. Then SampleSheet should be collapsed from Lane to individual sample (fastq R1/R2 files )"
    echo ""
}

exit_abnormal() {
  usage
  exit 1
}

# Read and control input arguments
while getopts ":sxfbgcde" opt; do
    case $opt in
      s) samplesheet=$OPTARG
          ;;
      x) forcesamplename='False'
          ;;
      f) fastqsuffix=$OPTARG
          ;;
      b) bamsuffix=$OPTARG
          ;;
      g) forcefastqnames='True'
          ;;
      c) forcebamnames='True'
          ;;
      d) allowdupsoverlanes='False'
          ;;
      e) collapselanes='False'
          ;;
      h) exit_abnormal
          ;;
      \?) echo echo ""; echo "Error:";"Invalid option -$OPTARG" >&2
        exit 1 ;;
      :) echo ""; echo "Error:"; echo " -${OPTARG} requires an argument!"
	      exit 1 ;;
    esac
done

# Check input arguments and variables
shift "$(( OPTIND -1 ))"

## Check Sample Sheet. if file is present in work directory.
if [ -z $samplesheet ]; then
  echo ""; echo "";
  echo " Error: You must specify samplesheet: '-s' flag. "; echo ""
  exit 1
fi
if [ ! -f $samplesheet ]; then
  echo ""; echo "";
  echo " Eroor: SampleSheet does not exist"
  #echo "- Please specify correct samplesheet, or create a CTG_SampleSheet.csv in current runfolder"
  exit 1
fi

### Exec python script
scriptdir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# python --version
echo " ... running python script: parse-sampelsheet.py"
echo " ... check python script logfile: parse-samplesheet.log"
# python ${scriptdir}/parse-samplesheet.py ${samplesheet} ## to run local
singularity exec --bind \
    /projects/fs1/ ${singularity_contatiner} \
    python ${scriptdir}/parse-samplesheet.py \
      --samplesheet ${samplesheet} \
      --forcesamplename ${forcesamplename} \
      --fastqsuffix ${fastqsuffix} \
      --bamsuffix ${bamsuffix} \
      --forcefastqnames ${forcefastqnames}\
      --forcebamnames ${forcebamnames}\
      --allowdupsoverlanes ${allowdupsoverlanes}\
      --collapselanes ${collapselanes}  > parse-samplesheet.log &

print(' ... ------------------------------------- ')
print('  === OK ===')
