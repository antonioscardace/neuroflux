import os
import psutil
import logging
import argparse
import subprocess
import pandas as pd

from tqdm import tqdm

# This script serves as the main entry point for the neuroflux preprocessing pipeline.
# It orchestrates the sequential execution of MRI and PET preprocessing bash scripts across a given dataset.
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the neuroflux preprocessing pipeline.')
    parser.add_argument('--use_gpu',        action='store_true',       help='Enable GPU acceleration for neural network-based steps. If omitted, default is CPU.')
    parser.add_argument('--csv_path',       type=str, required=True,   help='Path to the dataset CSV file.')
    parser.add_argument('--dataset_dir',    type=str, required=True,   help='Base dataset directory containing subjects and derivatives folders.')
    parser.add_argument('--template_path',  type=str, required=True,   help='Path to the reference structural template (e.g. MNI152).')
    parser.add_argument('--atlas_map_path', type=str, required=True,   help='Path to the atlas ROI map (such as Desikan-Killiany).')
    parser.add_argument('--mri_sequence',   type=str, required=True,   choices=['t1', 't2', 'flair'], help='MRI sequence to use.')
    parser.add_argument('--ref_regions',    type=int, default=[8, 47], nargs=2, help='Reference region IDs for SUVR normalization (L, R).')
    parser.add_argument('--n_threads',      type=int, default=psutil.cpu_count(logical=False), help='Number of threads to use for processing.')
    args = parser.parse_args()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MRI_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_mri.sh')
    PET_PREPROC_SCRIPT = os.path.join(BASE_DIR, 'bash', 'preproc_pet.sh')
    REF_REGION_L, REF_REGION_R = str(args.ref_regions[0]), str(args.ref_regions[1])
    DEVICE = 'cuda' if args.use_gpu else 'cpu'
    N_THREADS = str(args.n_threads)

    if not os.path.isfile(args.template_path) or os.path.getsize(args.template_path) <= 0:
        raise ValueError('The template scan is not valid.')
    
    if not os.path.isfile(args.atlas_map_path) or os.path.getsize(args.atlas_map_path) <= 0:
        raise ValueError('The atlas ROI map is not valid.')
    
    if not 0 < args.n_threads <= psutil.cpu_count(logical=True):
        raise ValueError('The number of threads is not valid.')

    template_path = os.path.abspath(args.template_path)
    atlas_map_path = os.path.abspath(args.atlas_map_path)
    dataset_dir = os.path.abspath(args.dataset_dir)
    os.makedirs(os.path.join(dataset_dir, 'derivatives'), exist_ok=True)

    # Read the dataset CSV file and iterate over each subject's visit.
    # For each row, the script constructs the paths for the raw input scans and the corresponding output directories.
    # Finally, it triggers the MRI and PET bash scripts via subprocess.
    # Output directory structure for preprocessed data:
    # - MRI: DATASET_DIR/derivatives/SUBJECT_ID/MRI_IMAGE_UID/...
    # - PET: DATASET_DIR/derivatives/SUBJECT_ID/PET_IMAGE_UID/...
    
    df = pd.read_csv(args.csv_path)
    logging.basicConfig(filename='pipeline_errors.log', level=logging.ERROR, format='%(message)s')

    for index, row in tqdm(df.iterrows(), 'Processing visits', len(df), unit='visit'):

        subject_id = row['subject_id']
        mri_uid = row['mri_image_uid']
        pet_uid = row['pet_image_uid']

        try:
            mri_outdir = os.path.join(dataset_dir, 'derivatives', subject_id, mri_uid)
            pet_outdir = os.path.join(dataset_dir, 'derivatives', subject_id, pet_uid)
            raw_mri_path = os.path.abspath(row['raw_mri_path'])
            raw_pet_path = os.path.abspath(row['raw_pet_path'])
            
            if not os.path.isfile(raw_mri_path) or os.path.getsize(raw_mri_path) <= 0:
                raise ValueError('The sMRI scan is not valid.')

            if not os.path.isfile(raw_pet_path) or os.path.getsize(raw_pet_path) <= 0:
                raise ValueError('The PET scan is not valid.')
            
            os.makedirs(mri_outdir, exist_ok=True)
            os.makedirs(pet_outdir, exist_ok=True)
            
            subprocess.run(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, args=[
                MRI_PREPROC_SCRIPT, N_THREADS,
                raw_mri_path, template_path, atlas_map_path, mri_outdir,
                args.mri_sequence, DEVICE
            ])

            subprocess.run(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, args=[
                PET_PREPROC_SCRIPT, mri_outdir,
                raw_pet_path, template_path, atlas_map_path, pet_outdir,
                REF_REGION_L, REF_REGION_R
            ])

        # If any error occurs during the validation or the subprocess execution,
        # catch the exception and log the error message along with the subject ID.

        except Exception as e:
            tqdm.write('Processing failed: [%s] @ visit [%s, %s]' % (subject_id, mri_uid, pet_uid))
            logging.error('Processing failed: [%s] - %s', subject_id, str(e))