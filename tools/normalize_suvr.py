#!/usr/bin/env python3

import argparse
import numpy as np
import nibabel as nib

# This function normalizes a PET scan using a reference region to compute SUVR.
# It divides the PET values by the mean uptake across reference labels 8 (Left Cerebellum Cortex) and 47 (Right Cerebellum Cortex).
# It checks for shape mismatches, missing reference labels, and invalid reference mean values.
# It saves the normalized SUVR scan to the specified output path.
# Author: Antonio Scardace

def normalize_suvr(scan_path: str, segm_path: str, out_path: str, ref_regions: list=[8, 47]) -> None:

    scan, segm = nib.load(scan_path), nib.load(segm_path)
    if scan.shape != segm.shape or not np.allclose(scan.affine, segm.affine, atol=1e-3):
        raise ValueError(f'Grid mismatch: PET {scan.shape} vs segmentation {segm.shape}')

    data = scan.get_fdata(dtype=np.float32)
    labels = np.rint(segm.get_fdata()).astype(np.int32)

    ref_mask = np.isin(labels, ref_regions) & np.isfinite(data) & (data != 0)
    if not ref_mask.any():
        raise ValueError(f'No valid voxels found for reference labels {ref_regions}.')

    ref_mean = float(data[ref_mask].mean())
    if not np.isfinite(ref_mean) or ref_mean <= 0:
        raise ValueError(f'Invalid reference mean: {ref_mean}')

    out = nib.Nifti1Image((data / ref_mean).astype(np.float32), scan.affine, scan.header)
    out.set_data_dtype(np.float32)
    nib.save(out, out_path)

# CLI for SUVR normalization of a PET scan.
# It requires an input PET scan (NIfTI), a segmentation mask with the reference region (NIfTI), and an output path (NIfTI).
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',   type=str, required=True)
    parser.add_argument('--segm_path',   type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    parser.add_argument('--ref_regions',  type=int, nargs=2, default=[8, 47])
    args = parser.parse_args()
    
    normalize_suvr(args.scan_path, args.segm_path, args.output_path, args.ref_regions)