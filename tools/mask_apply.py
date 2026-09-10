#!/usr/bin/env python3

import argparse
import numpy as np
import nibabel as nib

from scipy import ndimage

# This function performs skull stripping and mask cleaning on a neuroimaging scan using a brain mask.
# It retains voxels that are non-zero in both the scan and the brain mask, removing the background.
# It applies a binary opening operation to remove small isolated regions and residual noise.
# It saves the cleaned scan to the specified output path.
# Author: Antonio Scardace

def apply_brain_mask(scan_path: str, mask_path: str, out_path: str) -> None:

    scan = nib.load(scan_path)
    scan_data = scan.get_fdata()
    mask_data = nib.load(mask_path).get_fdata()

    voxel_intersection = ((mask_data > 0) & (scan_data > 0)).astype(np.uint8)
    cleaned_mask = ndimage.binary_opening(voxel_intersection, np.ones((3, 3, 3)), 1).astype(np.uint8)
    cleaned_scan_data = (scan_data * cleaned_mask).astype(scan.get_data_dtype())
    cleaned_scan = nib.Nifti1Image(cleaned_scan_data, scan.affine, scan.header)
    nib.save(cleaned_scan, out_path)

# CLI for skull stripping and mask-based cleaning of neuroimaging scans.
# It requires an input scan (NIfTI), a brain mask (NIfTI), and an output path.
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',   type=str, required=True)
    parser.add_argument('--mask_path',   type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    args = parser.parse_args()
    
    apply_brain_mask(args.scan_path, args.mask_path, args.output_path)