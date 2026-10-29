import os
import psutil
import argparse
import subprocess

# This script serves as the main entry point for the neuroflux preprocessing pipeline.
# It orchestrates the execution of MRI and PET preprocessing bash scripts for a given MRI-PET pair.
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the neuroflux preprocessing pipeline.')
    parser.add_argument('--use_gpu',        action='store_true',       help='Enable GPU acceleration for neural network-based steps. If omitted, default is CPU.')
    parser.add_argument('--verbose',        action='store_true',       help='Enable verbose output for subprocesses.')
    parser.add_argument('--mri_path',       type=str, required=True,   help='Path to the input sMRI scan (NIfTI format).')
    parser.add_argument('--mri_output_dir', type=str, required=True,   help='Directory to save the preprocessed sMRI data.')
    parser.add_argument('--pet_path',       type=str, required=True,   help='Path to the input PET scan (NIfTI format).')
    parser.add_argument('--pet_output_dir', type=str, required=True,   help='Directory to save the preprocessed PET data.')
    parser.add_argument('--template_path',  type=str, required=True,   help='Path to the reference structural template (e.g. MNI152).')
    parser.add_argument('--atlas_map_path', type=str, required=True,   help='Path to the atlas ROI map (such as Desikan-Killiany).')
    parser.add_argument('--mri_sequence',   type=str, required=True,   choices=['t1', 't2', 'flair'], help='MRI sequence to use.')
    parser.add_argument('--ref_regions',    type=int, default=[8, 47], nargs=2, help='Reference region IDs for SUVR normalization (L, R).')
    parser.add_argument('--n_threads',      type=int, default=psutil.cpu_count(logical=False), help='Number of threads to use for processing.')
    args = parser.parse_args()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MRI_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_mri.sh')
    PET_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_pet.sh')
    N_THREADS = str(args.n_threads)
    REF_REGION_L, REF_REGION_R = str(args.ref_regions[0]), str(args.ref_regions[1])

    if not os.path.isfile(args.mri_path) or os.path.getsize(args.mri_path) <= 0:
        raise ValueError('The MRI scan is not valid.')

    if not os.path.isfile(args.template_path) or os.path.getsize(args.template_path) <= 0:
        raise ValueError('The template scan is not valid.')
    
    if not os.path.isfile(args.atlas_map_path) or os.path.getsize(args.atlas_map_path) <= 0:
            raise ValueError('The atlas ROI map is not valid.')

    if not os.path.isfile(args.pet_path) or os.path.getsize(args.pet_path) <= 0:
        raise ValueError('The PET scan is not valid.')

    if not 0 < args.n_threads <= psutil.cpu_count(logical=True):
        raise ValueError('The number of threads is not valid.')

    raw_mri_path = os.path.abspath(args.mri_path)
    raw_pet_path = os.path.abspath(args.pet_path)
    template_path = os.path.abspath(args.template_path)
    atlas_map_path = os.path.abspath(args.atlas_map_path)
    mri_outdir = os.path.abspath(args.mri_output_dir)
    pet_outdir = os.path.abspath(args.pet_output_dir)
    os.makedirs(mri_outdir, exist_ok=True)
    os.makedirs(pet_outdir, exist_ok=True)

    # Runs the MRI preprocessing pipeline.
    # Runs the PET preprocessing pipeline.

    VERBOSE = None if args.verbose else subprocess.DEVNULL
    DEVICE = 'cuda' if args.use_gpu else 'cpu'

    subprocess.run(check=True, stdout=VERBOSE, stderr=VERBOSE, args=[
        MRI_PREPROC_SCRIPT, N_THREADS,
        raw_mri_path, template_path, atlas_map_path, mri_outdir,
        args.mri_sequence, DEVICE
    ])

    subprocess.run(check=True, stdout=VERBOSE, stderr=VERBOSE, args=[
        PET_PREPROC_SCRIPT, mri_outdir,
        raw_pet_path, template_path, atlas_map_path, pet_outdir,
        REF_REGION_L, REF_REGION_R
    ])