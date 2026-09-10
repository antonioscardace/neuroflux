#!/usr/bin/env python3

import argparse
import numpy as np
import nibabel as nib

# This function normalizes a PET scan using a reference region to compute SUVR.
# It divides the PET values by the mean uptake across reference labels 8 (Left Cerebellum Cortex) and 47 (Right Cerebellum Cortex).
# It checks for shape mismatches, missing reference labels, and invalid reference mean values.
# It saves the normalized SUVR scan to the specified output path.
# Author: Antonio Scardace

def normalize_suvr(scan_path: str, segm_path: str, out_path: str) -> None:

    scan = nib.load(scan_path)
    scan_data = scan.get_fdata()
    mask_data = nib.load(segm_path).get_fdata().astype(int)
    if scan_data.shape != mask_data.shape:
        raise ValueError('Shape mismatch: PET', scan_data.shape, 'vs Mask', mask_data.shape)

    ref_mask = np.isin(mask_data, [8, 47])
    if not np.any(ref_mask):
        raise ValueError('Reference labels [8, 47] not found in mask.')
        
    ref_mean = scan_data[ref_mask].mean()
    if ref_mean == 0 or np.isnan(ref_mean):
        raise ValueError('Reference region mean is zero or NaN, cannot divide.')
        
    suvr_vol = scan_data / ref_mean
    scan.header.set_data_dtype(np.float32)
    normalized_scan = nib.Nifti1Image(suvr_vol.astype(np.float32), scan.affine, scan.header)
    nib.save(normalized_scan, out_path)

# CLI for SUVR normalization of a PET scan.
# It requires an input PET scan (NIfTI), a segmentation mask with the reference region (NIfTI), and an output path (NIfTI).
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',   type=str, required=True)
    parser.add_argument('--segm_path',   type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    args = parser.parse_args()
    
    normalize_suvr(args.scan_path, args.segm_path, args.output_path)