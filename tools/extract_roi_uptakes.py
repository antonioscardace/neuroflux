#!/usr/bin/env python3

import json
import argparse
import numpy as np
import pandas as pd
import nibabel as nib

# This function extracts ROI-wise PET features using a SynthSeg segmentation.
# For each ROI, it computes the number of voxels, mean uptake, standard deviation, and total uptake.
# It saves the results to a CSV file.
# Author: Antonio Scardace

def extract_pet_roi_uptake(scan_path: str, segm_path: str, out_path: str, roi_name_to_id: dict[str, int]) -> None:

    pet_vol = nib.load(scan_path).get_fdata()
    mask_vol = nib.load(segm_path).get_fdata().astype(int)
    if pet_vol.shape != mask_vol.shape:
        raise ValueError('PET and mask volumes must have the same shape.')

    df = pd.DataFrame(columns=['roi_label_id', 'roi_name', 'n_voxels', 'mean_uptake', 'std_dev_uptake', 'total_uptake'])
    for roi_name, roi_label_id in roi_name_to_id.items():
        roi_values = pet_vol[mask_vol == roi_label_id]
        mean_val = float(np.mean(roi_values)) if roi_values.size else 0.0
        std_val = float(np.std(roi_values)) if roi_values.size else 0.0
        total_val = float(np.sum(roi_values)) if roi_values.size else 0.0
        df.loc[len(df)] = [roi_label_id, roi_name, int(roi_values.size), mean_val, std_val, total_val]

    df.to_csv(out_path, index=False, float_format='%.6f')

# CLI for extracting ROI-wise PET features from a SynthSeg segmentation.
# It requires an input PET scan (NIfTI), a segmentation mask (NIfTI), an atlas ROI map, and an output path (CSV).
# It also requires the ROI name-to-ID mapping from the atlas configuration file.
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',      type=str, required=True)
    parser.add_argument('--segm_path',      type=str, required=True)
    parser.add_argument('--atlas_map_path', type=str, required=True)
    parser.add_argument('--output_path',    type=str, required=True)
    args = parser.parse_args()

    with open(args.atlas_map_path, 'r') as f:
        roi_name_to_id = json.load(f)
        extract_pet_roi_uptake(args.scan_path, args.segm_path, args.output_path, roi_name_to_id)