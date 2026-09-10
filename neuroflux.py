import os
import psutil
import argparse
import subprocess

# Fully CPU-based preprocessing pipeline for paired sMRI and tau-PET scans.
# Given an sMRI scan and the corresponding tau-PET from the same visit, it generates standardized, analysis-ready derivatives.
# The final outputs include approximately 100 ROIs based on the Desikan–Killiany atlas.
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the neuroflux preprocessing pipeline.')
    parser.add_argument('--verbose',        action='store_true',     help='Enable verbose output for subprocesses.')
    parser.add_argument('--skip_pet',       action='store_true',     help='Skip tau-PET preprocessing and process only the MRI.')
    parser.add_argument('--template_path',  type=str, required=True, help='Path to the reference structural template (e.g. MNI152).')
    parser.add_argument('--atlas_map_path', type=str, required=True, help='Path to the Atlas ROI map (e.g. Desikan-Killiany).')
    parser.add_argument('--mri_path',       type=str, required=True, help='Path to the input sMRI scan (NIfTI format).')
    parser.add_argument('--mri_output_dir', type=str, required=True, help='Directory to save the preprocessed sMRI data.')
    parser.add_argument('--pet_path',       type=str, default='',    help='Path to the input tau-PET scan (NIfTI format).')
    parser.add_argument('--pet_output_dir', type=str, default='',    help='Directory to save the preprocessed tau-PET data.')
    parser.add_argument('--n_threads',      type=int, default=psutil.cpu_count(logical=False), help='Number of threads to use for processing.')
    args = parser.parse_args()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MRI_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_mri.sh')
    PET_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_tau_pet.sh')
    N_THREADS = str(args.n_threads)
    VERBOSE = None if args.verbose else subprocess.DEVNULL

    if not os.path.isfile(args.mri_path) or os.path.getsize(args.mri_path) <= 0:
        raise ValueError('The MRI scan is not valid.')

    if not os.path.isfile(args.template_path) or os.path.getsize(args.template_path) <= 0:
        raise ValueError('The template scan is not valid.')
    
    if not os.path.isfile(args.atlas_map_path) or os.path.getsize(args.atlas_map_path) <= 0:
            raise ValueError('The atlas ROI map is not valid.')

    if not args.skip_pet and (not os.path.isfile(args.pet_path) or os.path.getsize(args.pet_path) <= 0):
        raise ValueError('The PET scan is not valid.')

    if not 0 < args.n_threads <= psutil.cpu_count(logical=True):
        raise ValueError('The number of threads is not valid.')

    raw_mri_path = os.path.abspath(args.mri_path)
    template_path = os.path.abspath(args.template_path)
    atlas_map_path = os.path.abspath(args.atlas_map_path)
    mri_outdir = os.path.abspath(args.mri_output_dir)
    os.makedirs(mri_outdir, exist_ok=True)

    if not args.skip_pet:
        raw_pet_path = os.path.abspath(args.pet_path)
        pet_outdir = os.path.abspath(args.pet_output_dir)
        os.makedirs(pet_outdir, exist_ok=True)

    # Runs the MRI preprocessing pipeline.
    # Runs the tau-PET preprocessing pipeline if not skipped.

    subprocess.run(check=True, stdout=VERBOSE, stderr=VERBOSE, args=[
        MRI_PREPROC_SCRIPT,
        N_THREADS,
        raw_mri_path,
        template_path,
        atlas_map_path,
        mri_outdir
    ])

    if not args.skip_pet:
        subprocess.run(check=True, stdout=VERBOSE, stderr=VERBOSE, args=[
            PET_PREPROC_SCRIPT,
            mri_outdir,
            raw_pet_path,
            template_path,
            atlas_map_path,
            pet_outdir
        ])