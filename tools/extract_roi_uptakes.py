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

    scan, segm = nib.load(scan_path), nib.load(segm_path)
    if scan.shape != segm.shape or not np.allclose(scan.affine, segm.affine, atol=1e-3):
        raise ValueError('PET and segmentation must share the same grid (shape and affine).')

    pet = scan.get_fdata(dtype=np.float32)
    labels = np.rint(segm.get_fdata()).astype(np.int32)

    valid_mask = np.isfinite(pet)
    valid_pet = pet[valid_mask]
    valid_labels = labels[valid_mask]

    df_voxels = pd.DataFrame({'label_id': valid_labels, 'pet': valid_pet})
    stats = df_voxels.groupby('label_id')['pet'].agg(
        n_voxels='count',
        mean_uptake='mean',
        std_dev_uptake='std',
        total_uptake='sum'
    ).reset_index()

    df_rois = pd.DataFrame(list(roi_name_to_id.items()), columns=['roi_name', 'roi_label_id'])
    res = df_rois.merge(stats, left_on='roi_label_id', right_on='label_id', how='left')
    res['n_voxels'] = res['n_voxels'].fillna(0).astype(int)
    cols = ['roi_label_id', 'roi_name', 'n_voxels', 'mean_uptake', 'std_dev_uptake', 'total_uptake']
    res[cols].to_csv(out_path, index=False, float_format='%.6f')

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