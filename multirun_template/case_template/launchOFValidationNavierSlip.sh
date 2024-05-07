#!/bin/bash

##--------------------------------------------------------------------------------------
## Actual comments should start with '##'.
## Comments starting with '#SBATCH' are interpreted by the scheduler.
##--------------------------------------------------------------------------------------

## Name of the job
#SBATCH -J OpenFOAM_Validation_NavierSlip_isolated_bubble_triperio

## Study number (mandatory)
#SBATCH --wckey XFQ33001

## Job duration HH:MM:SS (highly recommended)
#SBATCH -t 10:00:00

## Disk partition where the job should be executed
##    debug  (Max:   4 hours, 2 nodes =  72 cores)
##    normal (Max:  48 hours, 8 nodes = 288 cores)
##    long   (Max: 120 hours, 4 nodes = 144 cores)
#SBATCH -p standard
#SBATCH -q normal

## Number of nodes
#SBATCH --nodes=4

## Number of cores (there are 36 cores per node)
## This MUST be less or equal to 'Number of nodes' x 36
#SBATCH -n 144

## Send an email to the user when the job finishes
#SBATCH --mail-type=BEGIN,END

## Exclusive attribution of the nodes (nobody else can compute on the same nodes)
## This is useful when the requested number of cores is equal to 'Number of nodes' x 36
##SBATCH --exclusive

##--------------------------------------------------------------------------------------

# Source environment
. $HOME/.bashrc
. $WORK/OpenFOAM/OpenFOAM-plus/etc/bashrc_Icc

cd $PWD
# Get list of nodes
HOSTLIST="./slurm-${SLURM_JOBID}.hostlist"
scontrol show hostname $SLURM_NODELIST > $HOSTLIST

# Set number of processors in system/decomposeParDict
sed -i "s/^numberOfSubdomains.*;$/numberOfSubdomains ${SLURM_NTASKS};/" $PWD/system/decomposeParDict

# run
# ./GenerateMesh
./PrepareCase
./AllrunParallel

# TODO: setup in flight postProcessing
# Post process
# file_path="postProcessing/forces/0/force.dat"
# csv_file="output_forces.csv"
# # Get the last line of the file
# last_line=$(tail -n 1 "$slip_dir/$file_path")
# # Append to CSV
# echo "$alpha $slip $last_line" >> "$csv_file"