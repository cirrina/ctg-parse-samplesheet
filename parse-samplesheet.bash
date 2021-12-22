#!/bin/bash

echo " ----------------------- "
echo " ctg SampleSheet Parser  "
echo " ----------------------- "
echo " check & parse samplesheet into demux-ready sheet - to use with ctg-demux script"


## Uncomment two lines below to run python shell script on local machine macOS
# source ~/miniconda3/etc/profile.d/conda.sh ## Needed to run at local
# conda activate ctg-parse-samplesheet
# conda init bash # not needed




# usage message
usage() {
    echo ""
    echo " usage : "
    echo " parse-samplesheet [ -s samplesheet ] "  1>&2
    echo ""
    echo " arguments : "
    echo "------------------- "
    echo " samplesheet    -s : IEM style laboratory SampleSheet. Project and pipeline specific parameters must be added "
    echo ""
}

exit_abnormal() {
  usage
  echo "";echo "";echo ""
  echo " !!! ERROR !!! "
  echo "";echo "";echo ""
  echo "";echo "";echo ""
  exit 1
}

# Read and control input arguments
while getopts ":s:" opt; do
    case $opt in
      s) samplesheet=$OPTARG
          ;;
      h) exit_abnormal
        ;;
      \?) echo echo ""; echo "Error:";"Invalid option -$OPTARG" >&2
        exit_abnormal ;;
      :) echo ""; echo "Error:"; echo " -${OPTARG} requires an argument!"
	     exit_abnormal ;;
    esac
done

# Check input arguments and variables
shift "$(( OPTIND -1 ))"

## Check Sample Sheet. if file is present in work directory.
if [ -z $samplesheet ]; then
  echo ""; echo ""; echo "Error:"
  echo "You must specify samplesheet: '-s' flag. "; echo ""
  exit_abnormal
fi
if [ ! -f $samplesheet ]; then
  echo ""; echo ""; echo "Error:"
  echo "SampleSheet does not exist"
  #echo "- Please specify correct samplesheet, or create a CTG_SampleSheet.csv in current runfolder"
  exit_abnormal
fi

### Exec python script
scriptdir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# python --version
echo " ... running python script: parse-sampelsheet.py"
python ${scriptdir}/parse-samplesheet.py ${samplesheet}