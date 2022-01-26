# -*- coding: latin-1 -*-

import csv
import re
import pandas as pd
import os
import sys
import argparse


## -------------------------------
##  Input Args
## -------------------------------
print("Python version")
print (sys.version)
sheet_name = sys.argv[1]
# os.chdir('/Users/david/training/nbis-python/')
# sheet_name = 'SampleSheet-2021_145.csv'


## -------------------------------
##  Params (may be moved to Args)
## -------------------------------
# The Sample_Project, Sample_ID, and Sample_Name columns accept alphanumeric characters, hyphens (-), and underscores (_).
force_Sample_Name = True  # if to force Sample_Name(s) supplied in [Data] column to the same as Sample_ID
fastq_suffix = "_001.fastq.gz" # "Suffix needed to auto-generate fastq file names generated by bcl2fastq. If NULL no bam file names will be genrerated"
bam_suffix = "_Aligned.sortedByCoord.out.bam"  ## "Suffix needed to auto generate bam file names (typically generated by STAR). If NULL no bam file names will be genrerated"
## ADD UNIQUE FASTQ IF MULTIPLE LANES * collapse lanes * Special cases when same sample is distributed over multiple lanes within a single project.
allow_dups_over_lanes = True # If to allow duplicates (within one project) on multiple lanes. Rare on NovaSeq but can be found for S4 with lane divider. One sample may be run on both lane 1/2 or on 3/4.
collapse_lanes = True ## Like allow_dups_over_lanes, affects project specific samplsheets NOT demux sheet.  special cases - when a single (same) sample is present in multiple lanes AND --noLaneSplitting is True in bcl2fastq. Then SampleSheet should be collapsed from Lane to individual sample (fastq R1/R2 files )
## -------------------------------



cwd = os.path.basename(os.getcwd())

sectionDict = {
    '[Header]': {},
    '[Reads]': {},
    '[Settings]': {},
    '[Data]': {}
    }
# print(sectionDict.keys())


## READ THE SAMPLESHEET
## =====================
## use encoding='utf-8-sig' to remove the Byte Order Mark (BOM) from your input (often present in csv DOS files from lab)
with open(sheet_name, 'r', encoding='utf-8-sig') as csvfile:
    allines = csv.reader(csvfile, delimiter=(','), quotechar='"', skipinitialspace=True)

    ## loop through all rows.
    ## Save the different Sheet sections into dictionary
    ## --------------------------------------------------
    myLine = 0

    for row in allines:
        # if myLine==0 and row[0]!='[Header]': Warn if first line is not [Header]
        if myLine==0: firstrow = row # save first row - to get max no of columns/commas
        myLine+=1
        if(row[0] in sectionDict.keys()):
            current_s = row[0] # current section
            # print(current_s)
            s_index = 0
            continue
        elif not row:
            s_index += 1
            continue
        else:
            ## replace very illegal characters
            p = re.compile(r'[ÅåÄäÖö\+]')
            #p = re.compile(r'[\+]')
            i = 0
            for row_i in row:
                row[i] = p.sub('', row_i)
                i+=1
            ## save lines in sectionDict
            sectionDict[current_s][s_index] = row
            s_index += 1


# Read & check some parameters defined in [Header]. Save some params for use below.
# =========================================================================
header_paired=()
header_runfolder=()

for row in sectionDict['[Header]']:
    if sectionDict['[Header]'][row][0] == 'Paired':
        header_paired = sectionDict['[Header]'][row][1]
        if not header_paired in ['True','False','true','false']:
            raise ValueError('[Header] param "Paired" incorrectly specified. Set to "true" or "false"' )

    # For Illumina RunFolder:
    # If not defined, RunFolder to Executiion dir.
    if sectionDict['[Header]'][row][0] == 'RunFolder':
        header_runfolder = sectionDict['[Header]'][row][1]
        if not header_runfolder:
            sectionDict['[Header]'][row][1] = cwd
            header_runfolder = cwd
            # print(sectionDict['[Header]'][row][1])


# [Data] section - generate Pandas Data Frame
# ==========================================

df = pd.DataFrame(sectionDict['[Data]'])
df = df.transpose() # transpose from dict
df.rename(columns=df.iloc[0], inplace=True) # first [Data] row is headers
df = df.iloc[1: , :]


# Force Sanmple_Name to Sample_ID (if option `force_Sample_Name`)
if force_Sample_Name:
    df["Sample_Name"] = df["Sample_ID"]


## Curate [Data] - Check columns
if not all(elem in df.columns.tolist() for elem in ['Sample_Name', 'Sample_ID', 'Sample_Project']):
    raise ValueError('Not all columns of Sample_ID and Sample_Project are present in [Data] section of file' )


## Curate [Data] - Lane - drop Lane Column if all are blank
if "Lane" in df.columns:
    if all(elem == '' for elem in df["Lane"].tolist()): # If all Lane are blank ''
        df = df.drop(['Lane'], axis=1) # remove Lane column
    elif not df["Lane"].tolist(): # if all Lane are blank
        df = df.drop(['Lane'], axis=1) # remove Lane column


## Curate [Data] - Sample_ID, _Name and _Project columns accept alphanumeric characters, hyphens (-), and underscores (_)
## replace illegal characters with underscore
for col in ['Sample_Name', 'Sample_ID', 'Sample_Project']:
    regular_expression = '[^a-zA-Z0-9\-\_]'
    df[col] = df[col].replace(regular_expression, '_', regex=True)
    df[col] = df[col].replace('\\s+', '', regex=True)
    # print(df[col])




## Add .fastq & .bam file names to main DF
# FASTQ files are named by blc2fastq with the following logic:
# **{samplename}\_{S1}\_{L001}\_{R1}\_001.fastq.gz**
# Using the 'noLaneSplitting' flag, L001 will NOT be in fastq name
# Requres that the global 'Paired' parameter is defined in [Header] section
# The first read (R1) is always in column fastq_1. If paired sequencing, R2 will be added in the fastq_2 column
if fastq_suffix:
    # print(header_paired)
    if not header_paired:
        raise ValueError('Adding fastq file names to [Data] section error: "Paired" true or false must be defined in [Header] section!' )
    row_i = 0
    fastq_1 = []
    fastq_2 = []
    for sample_id in df["Sample_ID"].tolist():
        fastq_1.append(f'{sample_id}_S{row_i+1}_R1{fastq_suffix}') # fastq_1.append(f'{sample_id}_S{row_i+1}_L001_R1_{fastq_suffix}')
        fastq_2.append(f'{sample_id}_S{row_i+1}_R2{fastq_suffix}') # fastq_2.append(f'{sample_id}_S{row_i+1}_L001_R2_{fastq_suffix}')
        row_i+=1
    df["fastq_1"] = fastq_1
    if(header_paired in ['true','True']):
        df["fastq_2"] = fastq_2

if bam_suffix:
    row_i = 0
    bam = []
    for sample_id in df["Sample_ID"].tolist():
        bam.append(f'{sample_id}{bam_suffix}')
        row_i+=1
    df["bam"] = bam



## Define the (max) number of columns of sheet to write. May have changed from import
# The first row must have columns (commas) mathcing the [Data] section
n_columns = df.shape[1]


## Split df into multiple frames on Project ID
## This to save project-specific/uniqe sample sheets & initiate project specific nextflow pipelines
# # ==========================================
dfs = dict(tuple(df.groupby('Sample_Project')))
all_projects = set(dfs.keys()) # set with all projects



## Check if any duplicated sample_ids exits.
# # ==========================================
# Duplicates are accepted if same project but different Lanes
# Also, option allow_dups_over_lanes, if false, then follow strict rule of no duplicates, regardless if different Lane or not
#if "Lane" in df.columns:
if not allow_dups_over_lanes:
    sid = df['Sample_ID'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print('Duplicate(s) detected:')
        print(dupes)
        print('')
        raise ValueError('Duplicate sample names detected - not allowed when allow_dups_over_lanes is set to False' )
elif "Lane" not in df.columns:
    sid = df['Sample_ID'].map(str) + '  ' + df['Sample_Project'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print('Duplicate(s) detected:')
        print(dupes)
        print('')
        raise ValueError('Duplicate sample names detected - not allowed if not multiple lanes !!' )
elif len(all_projects)==1:
    sid = df['Lane'].map(str) + '  ' + df['Sample_ID'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print('Duplicate(s) detected:')
        print(dupes)
        print('')
        raise ValueError('Duplicate sample names detected wihtin a lane - not allowed !!' )
elif len(all_projects) >1 :
    sid = df['Sample_ID'].map(str)
    seen = set()
    dupes = [x for x in sid if x in seen or seen.add(x)]
    if dupes:
        print('Duplicate(s) detected:')
        print(dupes)
        print('')
        raise ValueError('Duplicate sample names detected - refrain from using same Sample IDs for projects on one flowcell' )



#  Write Sample Sheets
# =====================================================
# 1. One samplesheet used for Demux with bcl2fastq.
#   - Name: samplesheet-XXX-demux.csv
#   - XXX is the RunFolder. It i assumed the samplesheet is present within the RunFolder and that the script is initiated there (if not other runfolder name is specified in [Header] section)

sheet_out = f'SampleSheet-demux-{header_runfolder}.csv' # the runfolder is added to samplesheet name. defaults to current dir.
fh_out = open(sheet_out,'w', encoding='utf-8')
# create the csv writer
writer = csv.writer(fh_out, lineterminator='\n')
print(f'... writing demux specific samplesheet:  {sheet_out}')

for s in sectionDict.keys():
    if s == '[Header]':
        headerrow = ['']*n_columns
        headerrow[0] = '[Header]'
        writer.writerow(headerrow) # write first row of file as is - max number of comma separators needed for bcl2fastq
        for row in sectionDict[s]: # step through all rows of the [Header] dict list
            row_i
            if sectionDict[s][row][0]=='SharedFlowCell':
                if len(all_projects) > 1:
                    sectionDict[s][row][1] = 'true'
                else: sectionDict[s][row][1] = 'false'
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


#  2. One samplesheet per unique project.
#   NOT for demux - used for Nextflow - if multiple Lanes (and --noLaneSplitting) Needs one row per Sample fastq
#   - Name: samplesheet-ctg-YYYY.csv
#   - When writing these individual samplesheets update metadata (may have gone from 'multiple' to unique)
#        - RunFolder
#        - ProjectId
#        - PoolName
#        - Species
#        - PipelineProfile

for project in all_projects:
    project_out = f'SampleSheet-ctg-rnaseq-{project}.csv'
    print(f'... writing project specific samplesheet:  {project_out}')
    fh_out = open(project_out,'w', encoding='utf-8')
    writer = csv.writer(fh_out, lineterminator='\n')
    for s in sectionDict.keys():
        if s == '[Header]':
            headerrow = ['']*n_columns
            headerrow[0] = '[Header]'
            writer.writerow(headerrow) # write first row of file as is - max number of comma separators needed for bcl2fastq
            ## Step through all rows in the Header dict. Temp save each as current_row. Check and print to file.
            for row in sectionDict[s]:
                current_row = ['']*n_columns
                current_row[0] = sectionDict[s][row][0]
                current_row[1] = sectionDict[s][row][1]
                if current_row[0]=='ProjectId':
                    current_row[1] = project # replace project slot with current project (e.g. from 'multiple' to this project)

                ## Check & replace [Header] parameters
                ## ---------------------------
                # e.g. params that may have been different inbetween projects, from 'multiple' to a unique shared value
                if current_row[0]=='Species':
                    if 'Species' in dfs[project].columns.tolist():
                        if len(dfs[project]['Species'].unique())== 1:
                            current_row[1] = dfs[project]['Species'].tolist()[0]
                if current_row[0]=='PipelineProfile':
                    if 'PipelineProfile' in dfs[project].columns.tolist():
                        if len(dfs[project]['PipelineProfile'].unique())== 1:
                            current_row[1] = dfs[project]['PipelineProfile'].tolist()[0]
                if current_row[0]=='PoolName':
                    if 'Sample_Pool' in dfs[project].columns.tolist():
                        if len(dfs[project]['Sample_Pool'].unique())== 1:
                            current_row[1] = dfs[project]['Sample_Pool'].tolist()[0]
                if current_row[0]=='Assay':
                    if 'Assay' in dfs[project].columns.tolist():
                        if len(dfs[project]['Assay'].unique())== 1:
                            current_row[1] = dfs[project]['Assay'].tolist()[0]
                if current_row[0]=='Strandness':
                    if 'Strandness' in dfs[project].columns.tolist():
                        if len(dfs[project]['Strandness'].unique())== 1:
                            current_row[1] = dfs[project]['Strandness'].tolist()[0]
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

print(' === OK ===')

# close files
f.close()
csvfile.close()
#fh_out.close()
