import csv
import re
import pandas as pd
import os
import sys
import argparse

print(f' ===== ctg-parse-samplesheet ====')
print(f' ...  ')
print(f' ... ... ')
print(f' ... ... ... ')

## -------------------------------
##  Input Args
## -------------------------------
print("Python version")
print (sys.version)

parser = argparse.ArgumentParser()
parser.add_argument("--samplesheet", required=True, help="File namne - SampleSheet to parse")
parser.add_argument("--forcesamplename", required=True, default=True, help="if to force Sample_Name(s) supplied in [Data] column to the same as Sample_ID")
parser.add_argument("--fastqsuffix", required=True, default="_001.fastq.gz", help="Suffix needed to auto-generate fastq file names generated by bcl2fastq. If NULL no bam file names will be genrerated")
parser.add_argument("--bamsuffix", required=True, default="_Aligned.sortedByCoord.out.bam", help="Suffix needed to auto generate bam file names (typically generated by STAR). If NULL no bam file names will be genrerated")
parser.add_argument("--forcefastqnames", required=True, default=False, help="Set to true if to overwrite fastq filenames. By defualt (fastq_1/fastq_2) columns will not be overwritten if present (even though fastq_suffix is supplied)")
parser.add_argument("--forcebamnames", required=True, default=False, help="Set to true if to overwrite bam filenames. By defualt (bam) column will not be overwritten if present (even though bam_suffix is supplied)")
parser.add_argument("--allowdupsoverlanes", required=True, default=True, help="If to allow duplicates (within one project) on multiple lanes. Rare on NovaSeq but can be found for S4 with lane divider. One sample may be run on both lane 1/2 or on 3/4.")
parser.add_argument("--collapselanes", required=True, default=True, help="Like allow_dups_over_lanes, affects project specific samplsheets NOT demux sheet.  special cases - when a single (same) sample is present in multiple lanes AND --noLaneSplitting is True in bcl2fastq. Then SampleSheet should be collapsed from Lane to individual sample (fastq R1/R2 files )")


args = parser.parse_args()
sheet_name = args.samplesheet
force_Sample_Name = args.forcesamplename  # if to force Sample_Name(s) supplied in [Data] column to the same as Sample_ID
fastq_suffix = args.fastqsuffix # "Suffix needed to auto-generate fastq file names generated by bcl2fastq. If NULL no bam file names will be genrerated"
bam_suffix = args.bamsuffix  ## "Suffix needed to auto generate bam file names (typically generated by STAR). If NULL no bam file names will be genrerated"
force_fastq_names = args.forcefastqnames # Set to true if to overwrite fastq filenames. By defualt (fastq_1/fastq_2) columns will not be overwritten if present (even though fastq_suffix is supplied)
force_bam_names = args.forcebamnames # Set to true if to overwrite bam filenames. By defualt (bam) column will not be overwritten if present (even though bam_suffix is supplied)
allow_dups_over_lanes = args.allowdupsoverlanes # If to allow duplicates (within one project) on multiple lanes. Rare on NovaSeq but can be found for S4 with lane divider. One sample may be run on both lane 1/2 or on 3/4.
collapse_lanes = args.collapselanes ## Like allow_dups_over_lanes, affects project specific samplsheets NOT demux sheet.  special cases - when a single (same) sample is present in multiple lanes AND --noLaneSplitting is True in bcl2fastq. Then SampleSheet should be collapsed from Lane to individual sample (fastq R1/R2 files )

## -------------------------------
##  Params temp debug local
## -------------------------------
# os.chdir('/Users/david/training/nbis-python/') ## use if local
# sheet_name = 'uroscan-validation2.csv' ## use if local

# The Sample_Project, Sample_ID, and Sample_Name columns accept alphanumeric characters, hyphens (-), and underscores (_).
# force_Sample_Name = True  # if to force Sample_Name(s) supplied in [Data] column to the same as Sample_ID
# fastq_suffix = "_001.fastq.gz" # "Suffix needed to auto-generate fastq file names generated by bcl2fastq. If NULL no bam file names will be genrerated"
# bam_suffix = "_Aligned.sortedByCoord.out.bam"  ## "Suffix needed to auto generate bam file names (typically generated by STAR). If NULL no bam file names will be genrerated"
# force_fastq_names = False # Set to true if topai overwrite fastq filenames. By defualt (fastq_1/fastq_2) columns will not be overwritten if present (even though fastq_suffix is supplied)
# force_bam_names = False # Set to true if to overwrite bam filenames. By defualt (bam) column will not be overwritten if present (even though bam_suffix is supplied)
#
# ## ADD UNIQUE FASTQ IF MULTIPLE LANES * collapse lanes * Special cases when same sample is distributed over multiple lanes within a single project.
# allow_dups_over_lanes = True # If to allow duplicates (within one project) on multiple lanes. Rare on NovaSeq but can be found for S4 with lane divider. One sample may be run on both lane 1/2 or on 3/4.
# collapse_lanes = True ## Like allow_dups_over_lanes, affects project specific samplsheets NOT demux sheet.  special cases - when a single (same) sample is present in multiple lanes AND --noLaneSplitting is True in bcl2fastq. Then SampleSheet should be collapsed from Lane to individual sample (fastq R1/R2 files )
# #force_fastq_names = False

## -------------------------------
##  Start
## -------------------------------
cwd = os.path.basename(os.getcwd())

## SectionDict is used to store the different SampleSheet (IEM) sections
sectionDict = {
    '[Header]': {},
    '[Reads]': {},
    '[Settings]': {},
    '[Data]': {}
    }
# print(sectionDict.keys())

## a dictionary is used to find the corresponding [Data] section to a [Header] param
## the dictionary will also control how to collapse non-unique values
## header_col = {data_col, allowMultiple}
params_dict = {
        'ProjectID': ['Sample_Project', False],
        'PipelineName': ['PipelineName', False],
        'PipelineVersion': ['PipelineVersion', False],
        'PipelineProfile': ['PipelineProfile', False],
        'Species': ['Sample_Species', True],
        'email-ctg': ['email_ctg',False],
        'name-pi': ['name_pi','use_multiple',False],
        'email-customer': ['email_customer','use_multiple',False,],
        'Assay': ['Assay', False],
        'IndexAdapters': ['IndexAdapters', False],
        'Strandness': ['Sample_Strandness', False],
        'FragmentationTime': ['fragmentation_time', False],
        'PCR-cycles': ['pcr_cycles', False],
        'Paired': ['Sample_Paired', False],
        'PoolConcNovaSeq': ['Pool_Conc_NovaSeq',False],
        'PoolMolarityNovaSeq': ['Pool_Molarity_NovaSeq', False]
        }

## READ THE SAMPLESHEET
## =====================
## use encoding='utf-8-sig' to remove the Byte Order Mark (BOM) from your input (often present in csv DOS files from lab)
## loop through all rows & Save the different Sheet sections into dictionary
## --------------------------------------------------
header_rows=[] # keep track of all rows (params) in [Header] seciton. if duplicate found - raise error

with open(sheet_name, 'r', encoding='utf-8-sig') as csvfile:
    allines = csv.reader(csvfile, delimiter=(','), quotechar='"', skipinitialspace=True)
    print(f' ... Reading SampleSheet: "{sheet_name}"')
    myLine = 0
    for row in allines:
        # if myLine==0 and row[0]!='[Header]': Warn if first line is not [Header]
        if myLine==0: firstrow = row # save first row - to get max no of columns/commas
        myLine+=1
        ## do not read all blank lines. skip these!
        if all(elem == '' for elem in row):
            print(' ... ... blank row, skipping')
            continue
        if(row[0] in sectionDict.keys()):
            print(f' ... ... reading metadata section: {row[0]}')
            current_s = row[0] # current section
            s_index = 0
            continue
        elif not row:
            s_index += 1
            continue
        else:
            ## read each row and save in section-specific dictionary.
            ## replace very illegal characters wtih blanks ("")
            p = re.compile(r'[ÅåÄäÖö\+]')
            i = 0
            for row_i in row:
                row[i] = p.sub('', row_i)
                ## replace TRUE/FALSE (excel style) with True/Fals .
                row[i] = row[i].replace("FALSE", "false")
                row[i] = row[i].replace("False", "false")
                row[i] = row[i].replace("TRUE", "true")
                row[i] = row[i].replace("True", "true")
                i+=1

            ## save lines in sectionDict
            ## for non [Header] section, do not name
            if not current_s in ['[Header]','[Settings]']:
                sectionDict[current_s][s_index] = row
            ## for [Header] section name the row indexes keys same as params
            elif current_s in ['[Header]','[Settings]']:
                if row[0] in header_rows:
                    raise ValueError(f' ... ... Error: Duplicate [Header] params detected: "{row[0]}"')
                if current_s=='[Header]':
                    header_rows.append(row[0])
                sectionDict[current_s][row[0]] = row
            s_index += 1

# Read & check some parameters defined in [Header]. Save some params for later use
# =========================================================================
print(f' ... Checking some [Header] params')
header_paired=() ## if paired or not. used
header_runfolder=()
for row in sectionDict['[Header]']:
    # print(row)
    if row == 'Paired':
        print(f' ... ... found [Header] param "Paired": checking ...')
        header_paired = sectionDict['[Header]'][row][1]
        if not header_paired in ['true','false']:
            raise ValueError('[Header] param "Paired" incorrectly specified. Set to "true" or "false"' )
        print(f' ... ... ... ok')
    if row == 'Strandness':
        print(f' ... ... found [Header] param "Strandness": checking ...')
        header_strandness = sectionDict['[Header]'][row][1]
        if not header_strandness in ['forward','reverse']:
            raise ValueError('[Header] param "Strandness" incorrectly specified. Set to "forward" or "reverse"' )
        print(f' ... ... ... ok')
    # For Illumina RunFolder:
    # If not defined, RunFolder to Execution dir.
    if row == 'RunFolder':
        # print(f' ... ... found[Header] param "RunFolder"')
        header_runfolder = sectionDict['[Header]'][row][1]
        if not header_runfolder:
            print(f' ... ... RunFolder not specified ...')
            if os.path.isfile('./RTAComplete.txt'):
                sectionDict['[Header]'][row][1] = cwd
                header_runfolder = cwd
                print(f' ... ... ... Found "RTAComplete.txt" - Currect dir is a RunFolder. Setting "RunFolder" to current dir: "{cwd}"')
            else:
                print(f' ... ... ... "RTAComplete.txt" not in current dir. Leave RunFolder unspecified.')
print(f' ... ok')

## Add NumberSamples param if not present
if "NumberSamples" not in header_rows:
    print(f' ... ... "NumberSamples" not found: adding param to [Header]')
    sectionDict['[Header]']['NumberSamples']=['NumberSamples','']
    header_rows.append('NumberSamples')



# [Data] section - generate Pandas Data Frame
# ==========================================
print(f' ... Generating dataframe for [Data] section')
df = pd.DataFrame(sectionDict['[Data]'])
df = df.transpose() # transpose from dict
df.rename(columns=df.iloc[0], inplace=True) # first [Data] row is headers
df = df.iloc[1: , :]

# Force Sanmple_Name to Sample_ID (if option `force_Sample_Name`)
if force_Sample_Name:
    print(f' ... ... forcing "Sample_Name" column to same as "Sample_ID"')
    df["Sample_Name"] = df["Sample_ID"]

## Curate [Data] all Columns that contain only blank values
print(f'... ... dropping all [Data] columns with only blank values')
datacols = df.keys().tolist()
for col in datacols:
    if all(elem == '' for elem in df[col].tolist()): # If all Lane are blank ''
        print(f' ... ... ... dropping "{col}"')
        df = df.drop([col], axis=1) # remove column
    elif not df[col].tolist(): # if all values blank
        print(f' ... ... ... dropping "{col}"')
        df = df.drop([col], axis=1) # remove column
print(f' ... ... ... ok')

## Curate [Data] - Check columns
print(f' ... ... Checking if required [Data] columns are present')
if not all(elem in df.columns.tolist() for elem in ['Sample_Name', 'Sample_ID', 'Sample_Project']):
    raise ValueError('Not all columns of Sample_ID and Sample_Project are present in [Data] section of file' )
print(f' ... ... ... ok')

## Curate [Data] - Sample_ID, _Name and _Project columns accept alphanumeric characters, hyphens (-), and underscores (_)
## replace illegal characters with underscore
check_cols = ['Sample_ID', 'Sample_Name', 'Sample_Project']
print(f' ... ... Checking for illegal characters in columns: "{check_cols}" ')
for col in check_cols:
    regular_expression = '[^a-zA-Z0-9\-\_]'
    reg_flag = df[col].str.contains(regular_expression)
    if any(reg_flag):
        mystring = ' '.join([str(elem) for elem in df[col][reg_flag]])
        print(f' ... ... ... found illegal character(s) in "{col}": {mystring}')
        print(f' ... ... ... ... replacing with "_"')
        df[col] = df[col].replace(regular_expression, '_', regex=True)
    regular_expression = '\\s+'
    reg_flag = df[col].str.contains(regular_expression) ## not needed. should be covered above
    if any(reg_flag):
        print(f' ... ... ... found whitespace(s) in "{col}": {mystring}')
        print(f' ... ... ... ... removing these')
        df[col] = df[col].replace('\\s+', '', regex=True)
print(f' ... ... ... ok')



# [Data] section
# Add .fastq & .bam file names to main DF ("fastq_1" (R1), "fastq_2" (R2) and "bam" ). Requred for ctg-rnaseq pipeline
# should be same name as outputed from bcl2fastq demux (and STAR bams)
# blc2fastq filename logic:
#  **{samplename}\_{S1}\_{L001}\_{R1}\_001.fastq.gz**
#  Using the 'noLaneSplitting' flag, L001 will NOT be in fastq name
# Requres that the global 'Paired' parameter is defined in [Header] section

if fastq_suffix: # First check if fastq suffix is provided
    print(f' ... ... Fastq suffix provided ("{fastq_suffix}"). Adding fastq file names to [Data] section' )
    ## header paired defined above from [Header]-Paried para (true/false). If not raise error
    if not header_paired:
        raise ValueError(' ... ... ... Error: "Paired" (true or false) must be defined in [Header] section when adding fastq files!' )
    ## If fastq datacolumns present then requre
    datacols = df.keys().tolist()
    if not force_fastq_names and any([dc in ['fastq_1','fastq_2'] for dc in datacols]):
        print(' ... ... ... Error: "fastq_1" and/or "fastq_2" [Data] columns detected' )
        print(' ... ... ... You must set "force_fastq_names" to overwrite these columns')
        print(' ... ... ... skipping ...' )
    if force_fastq_names or not any([dc in ['fastq_1','fastq_2'] for dc in datacols]):
        print(f' ... ... ... generating bcl2fastq file names using {fastq_suffix} suffix - sequential numbering based on rows' )
        # Loop through all sample rows in data. File names determined by sample id, row number, and fastq suffix
        row_i = 0
        fastq_1 = []
        fastq_2 = []
        for sample_id in df["Sample_ID"].tolist():
            fastq_1.append(f'{sample_id}_S{row_i+1}_R1{fastq_suffix}') # fastq_1.append(f'{sample_id}_S{row_i+1}_L001_R1_{fastq_suffix}')
            fastq_2.append(f'{sample_id}_S{row_i+1}_R2{fastq_suffix}') # fastq_2.append(f'{sample_id}_S{row_i+1}_L001_R2_{fastq_suffix}')
            row_i+=1
        df["fastq_1"] = fastq_1
        print(f' ... ... ... added fastq_1 file names using "{fastq_suffix}"suffix' )
        if(header_paired in ['true']):
            df["fastq_2"] = fastq_2
            print(f' ... ... ... added fastq_2 file names using "{fastq_suffix}" suffix' )
else:
    print(f' ... ... no fastq_suffix provided. Will not add fastq file names to [Data] section' )

if bam_suffix:
    print(f' ... ... bam suffix provided  ("{bam_suffix}"). Adding bam file names to [Data] section' )
    datacols = df.keys().tolist()
    if not force_bam_names and any([dc in ['bam'] for dc in datacols]):
        print(' ... ... ... Error: "bam" [Data] column detected' )
        print(' ... ... ... You must set "force_bam_names" to overwrite this column')
        print(' ... ... ... skipping ...' )
    if force_bam_names or not any([dc in ['bam'] for dc in datacols]):
        row_i = 0
        bam = []
        for sample_id in df["Sample_ID"].tolist():
            bam.append(f'{sample_id}{bam_suffix}')
            row_i+=1
        df["bam"] = bam
        print(f' ... ... ... added bam file names using "{bam_suffix}" suffix' )
else:
    print(f' ... ... no bam_suffix provided. Will not add bam file names to [Data] section' )
print(f' ... ... ... ok' )



# [Data] section
## Check if any duplicated sample_ids exits.
# # ==========================================
# Duplicate samples IDs are accepted if same project but only if a project is on different Lanes (This is Rare)
# Also, option allow_dups_over_lanes, if false, then follow strict rule of no duplicates, regardless if different Lane or not
#if "Lane" in df.columns:
print(f' ... ... Double-check that no duplicate Sample IDs exist' )
if not allow_dups_over_lanes:
    print(f' ... ... ... "allow_dups_over_lanes" set to {allow_dups_over_lanes}. Duplicate Sample_IDs are strictly forbidden.')
    sid = df['Sample_ID'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print(f' ... ... ... Warning: Duplicate(s) detected: {dupes}')
        raise ValueError('Error: Duplicate sample names detected - not allowed when allow_dups_over_lanes argument is set to False' )
elif "Lane" not in df.columns:
    print(f' ... ... ... [Data] "Lane" column not specified - Duplicate Sample_IDs are strictly forbidden.')
    sid = df['Sample_ID'].map(str) + '  ' + df['Sample_Project'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print(f' ... ... ... Warning: Duplicate(s) detected: {dupes}')
        raise ValueError('Error: Duplicate sample names detected - not allowed' )
# elif len(all_projects)==1:
else:
    print(f' ... ... ... [Data] "Lane" column is specified')
    print(f' ... ... ... "allow_dups_over_lanes" argument set to True. Duplicate Sample_IDs are allowed but only if in different lanes.')
    sid = df['Lane'].map(str) + '  ' + df['Sample_ID'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print(f' ... ... ... Warning: Duplicate(s) detected: {dupes}')
        raise ValueError('Error: Duplicate sample names detected wihtin a lane - not allowed !!' )
# not sure if need to include beliw ...
# elif len(all_projects) >1 :
#     print(f' ... ... ... [Data] "Lane" column is specified & samples are from different "Sample_Project"')
#     print(f' ... ... ... "allow_dups_over_lanes" set to {allow_dups_over_lanes}. Duplicate Sample_IDs are allowed but only between lanes.')
#     sid = df['Sample_ID'].map(str)
#     seen = set()
#     dupes = [x for x in sid if x in seen or seen.add(x)]
#     if dupes:
#         print(f' ... ... ... Warning: Duplicate(s) detected: {dupes}')
#         raise ValueError('Error: Duplicate sample names detected - refrain from using same Sample IDs between projects within one flowcell' )
print(f' ... ... ... ok' )


# [Data] section
## Split df into multiple data frames based on Project ID (one df per project)
## This to save project-specific/uniqe sample sheets & initiate project specific nextflow pipelines
# # ==========================================
dfs = dict(tuple(df.groupby('Sample_Project')))
all_projects = set(dfs.keys()) # set all_projects list with all project names




# [Data] section
## Define the (max) number of columns of sheet to write. May have changed from import
# The first row must have columns (commas) mathcing the [Data] section
n_columns = df.shape[1]



#  Write Sample Sheets
# =====================================================


# 1. One samplesheet with full parsed output
#   - Name: CTG_SampleSheet.parsed.csv
print(f' ... ------------------------------------- ')
sheet_out = f'{sheet_name.replace(".csv","")}.parsed.csv'
#sheet_out = f'CTG_SampleSheet.parsed.csv' # the runfolder is added to samplesheet name. defaults to current dir.
fh_out = open(sheet_out,'w', encoding='utf-8')
# create the csv writer
writer = csv.writer(fh_out, lineterminator='\n')
print(f' ... writing demux specific samplesheet:  {sheet_out}')

for s in sectionDict.keys():
    if s == '[Header]':
        # set NumberSamples param in [Header] (and warn if different from what is supplied)
        headerrow = ['']*n_columns #
        headerrow[0] = '[Header]'
        writer.writerow(headerrow) # write first row of file as is - max number of comma separators needed for bcl2fastq
        for row in sectionDict[s]: # step through all rows of the [Header] dict list

            if row == 'SharedFlowCell':
                if len(all_projects) > 1:
                    print(f' ... ... mutiple projects in "Sample_Project" - setting "SharedFlowCell" to "true" ')
                    sectionDict[s][row][1] = 'true'
                else:
                    sectionDict[s][row][1] = 'false'
                    print(f' ... ... only one project in "Sample_Project" - setting "SharedFlowCell" to "false" ')
                    sectionDict[s][row][1] = 'false'
            if row == 'NumberSamples':
                mykeys=sectionDict['[Header]'].keys()
                n_samples = df.shape[0]
                s_samples = sectionDict[s][row][1]
                if not n_samples == sectionDict[s][row][1]:
                    print(f' ... ... Warning: Number of Sample_IDs ({n_samples}) do not match supplied "NumberSamples" ({s_samples})')
                sectionDict[s][row][1] = n_samples
                print(f' ... ... ... setting "NumberSamples" to: {n_samples}')

            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Reads]':
        writer.writerow(['']*n_columns)
        readsrow = ['']*n_columns
        readsrow[0] = '[Reads]'
        writer.writerow(readsrow)
        for row in sectionDict[s]:
            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Settings]':
        writer.writerow(['']*n_columns)
        settingsrow = ['']*n_columns
        settingsrow[0] = '[Settings]'
        writer.writerow(settingsrow)
        for row in sectionDict[s]:
            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Data]':
        writer.writerow(['']*n_columns)
        datarow = ['']*n_columns
        datarow[0] = '[Data]'
        writer.writerow(datarow)
        fh_out.close()
        with open(sheet_out, 'a') as f:
             df.to_csv(f, header=True, index=False)



# 2. One slimmed samplesheet used for demux with bcl2fastq.
#   - Name: CTG_SampleSHeet-demux.csv

## Genreate stripped [data] section for demux. Keep ony columns needed for demux (['Lane','Sample_ID','Sample_Name','Sample_Project',"index..."])
demux_patterns=['Lane','Sample_ID','Sample_Name','Sample_Project',"index","Index"]
demux_cols=[]
for cp in demux_patterns:
    cpi = [col for col in mycols if cp in col]
    if cpi:
        demux_cols = demux_cols+cpi

## bcl2fastq does not allow commas in [Data]. Create a cppy of the [data] df and replave all illegal characters
df_demux = df.replace('\"','', regex=True) # replace all double quotes with blanks
df_demux = df_demux.replace('\,',' ', regex=True) # replace all commas woth space

print(f' ... ------------------------------------- ')
sheet_out = f'CTG_SampleSheet.demux.{header_runfolder}.csv' # the runfolder is added to samplesheet name. defaults to current dir.
fh_out = open(sheet_out,'w', encoding='utf-8')
# create the csv writer
writer = csv.writer(fh_out, lineterminator='\n')
print(f' ... writing demux specific samplesheet:  {sheet_out}')

for s in sectionDict.keys():
    if s == '[Header]':
        # set NumberSamples param in [Header] (and warn if different from what is supplied)
        headerrow = ['']*n_columns #
        headerrow[0] = '[Header]'
        writer.writerow(headerrow) # write first row of file as is - max number of comma separators needed for bcl2fastq
        for row in sectionDict[s]: # step through all rows of the [Header] dict list

            if row == 'SharedFlowCell':
                if len(all_projects) > 1:
                    print(f' ... ... mutiple projects in "Sample_Project" - setting "SharedFlowCell" to "true" ')
                    sectionDict[s][row][1] = 'true'
                else:
                    sectionDict[s][row][1] = 'false'
                    print(f' ... ... only one project in "Sample_Project" - setting "SharedFlowCell" to "false" ')
                    sectionDict[s][row][1] = 'false'
            if row == 'NumberSamples':
                mykeys=sectionDict['[Header]'].keys()
                n_samples = df.shape[0]
                s_samples = sectionDict[s][row][1]
                if not n_samples == sectionDict[s][row][1]:
                    print(f' ... ... Warning: Number of Sample_IDs ({n_samples}) do not match supplied "NumberSamples" ({s_samples})')
                sectionDict[s][row][1] = n_samples
                print(f' ... ... ... setting "NumberSamples" to: {n_samples}')

            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Reads]':
        writer.writerow(['']*n_columns)
        readsrow = ['']*n_columns
        readsrow[0] = '[Reads]'
        writer.writerow(readsrow)
        for row in sectionDict[s]:
            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Settings]':
        writer.writerow(['']*n_columns)
        settingsrow = ['']*n_columns
        settingsrow[0] = '[Settings]'
        writer.writerow(settingsrow)
        for row in sectionDict[s]:
            if not all(elem == '' for elem in sectionDict[s][row]):
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                writer.writerow(current_row)
    if s == '[Data]':
        writer.writerow(['']*n_columns)
        datarow = ['']*n_columns
        datarow[0] = '[Data]'
        writer.writerow(datarow)
        fh_out.close()
        with open(sheet_out, 'a') as f:
             df_demux.to_csv(f, header=True, index=False)


#  3. One samplesheet per unique project (rnaseq pipeline).
#   NOT for demux - used for Nextflow - if multiple Lanes (and --noLaneSplitting) Needs one row per Sample fastq
#   - Name: samplesheet-ctg-YYYY.csv
#   - When writing these individual samplesheets update metadata (may have gone from 'multiple' to unique)
#        - RunFolder
#        - ProjectID
#        - Species/Sample_Species
#        - PipelineProfile
#        - ... etc

def harmonize_header_params(input_row=None, data_mat=None, data_col=None, allowMultiple=None, ingoreBlanks=None):
    ## function for harmonizing parameters that are present in [Header] and [Data] (individual samples)
    ## [Header] and [Data] param pairs often do not have identical names
    ## Main principle is to look at values in [Data] column and replace the [Header] with that value(s)
    ##  - if unique value in [Data] - Replace!
    ##  - if >1 value collapse 'multiple' (default), or separate values by comma.
    return_row = input_row
    if data_col in data_mat.columns.tolist():
        if len(data_mat[data_col].unique())== 1:
            return_row[1] = data_mat[data_col].tolist()[0]
        else:
            return_row[1] = 'multiple'
            if allowMultiple==False:
                raise ValueError(f'Error: Multiple values found in [Data] column "{data_col}" when harmonizing [Header] and [Data] params. Multiple values are not allowed within one and the same project as defined by the "params_dict" object in this python script. Values found were:  {data_mat[data_col].unique()}' )
        if not return_row[1]==input_row[1]:
            print(f' ... ... Harmonizing values. [Header] param "{input_row[0]}" changed from "{input_row[1]}" to [Data] "{data_col}" columns value: {return_row[1]}')
        # if return_row[1]==input_row[1]: ## no action

    return(return_row)
    ## end function


for project in all_projects:
    project_out = f'CTG_SampleSheet.project.{project}.csv'
    print(f' ... ------------------------------------- ')
    print(f' ... writing Project specific samplesheet:  {project_out}')
    fh_out = open(project_out,'w', encoding='utf-8')
    writer = csv.writer(fh_out, lineterminator='\n')

    for s in sectionDict.keys():

        ## [Header] - Harmonize Params
        if s == '[Header]':
            headerrow = ['']*n_columns
            headerrow[0] = '[Header]'
            writer.writerow(headerrow) # write first row of file as is - max number of comma separators needed for bcl2fastq

            ## set n samples
            if row == 'NumberSamples':
                mykeys=sectionDict['[Header]'].keys()
                n_samples = dfs[project].shape[0]
                sectionDict[s][row][1] = n_samples
                print(f' ... ... setting "NumberSamples" to: {n_samples}')

            ## [Header] - Harmonize Params
            ## Step through all rows in the Header dict. Temp save each as current_row. Check and print to file.
            print(f' ... ... Harmonizing [Header] params with [Data] columns')
            for row in sectionDict[s]:
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]

                ## harmonize_header_params function
                # If param found in params_dict use harmonize_header_params function to replace [Header] value (if needed). Note that all blank columns have allready been removed
                if current_row[0] in params_dict.keys():
                    current_row = harmonize_header_params(input_row=current_row, data_mat=dfs[project], data_col=params_dict[current_row[0]][0], allowMultiple=params_dict[current_row[0]][1])
                ## Write row to file
                if not all(elem == '' for elem in current_row):
                    writer.writerow(current_row)

        if s == '[Reads]':
            writer.writerow(['']*n_columns)
            readsrow = ['']*n_columns
            readsrow[0] = '[Reads]'
            writer.writerow(readsrow)
            for row in sectionDict[s]:
                if not all(elem == '' for elem in sectionDict[s][row]):
                    current_row = ['']*n_columns
                    current_row[0] = sectionDict[s][row][0]
                    current_row[1] = sectionDict[s][row][1]
                    writer.writerow(current_row)
        if s == '[Settings]':
            writer.writerow(['']*n_columns)
            settingsrow = ['']*n_columns
            settingsrow[0] = '[Settings]'
            writer.writerow(settingsrow)
            for row in sectionDict[s]:
                if not all(elem == '' for elem in sectionDict[s][row]):
                    current_row = ['']*n_columns
                    current_row[0] = sectionDict[s][row][0]
                    current_row[1] = sectionDict[s][row][1]
                    writer.writerow(current_row)
        if s == '[Data]':
            writer.writerow(['']*n_columns)
            datarow = ['']*n_columns
            datarow[0] = '[Data]'
            writer.writerow(datarow)
            fh_out.close()
            with open(project_out, 'a') as f:
                ## if collapse lanes * only keep unique sample-fastqs mappings in sample sheet
                ## only relevant if fastq file names are built (fastq_suffix given)
                dfs_write = dfs[project]
                if collapse_lanes and fastq_suffix and "Lane" in df.columns:
                    # dfs_write.drop('Lane', axis=1, inplace=True) # lane is no longer relevant -
                    dfs_write.drop_duplicates(subset=['Sample_ID'], inplace=True) ## collapse - drop rows with duplicated fastq files
                dfs[project].to_csv(f, header=True, index=False)
    print(f' ... ------------------------------------- ')
print(' ... ok ... ')
# close files
f.close()
csvfile.close()
#fh_out.close()
