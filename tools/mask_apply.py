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
    scan_data = scan.get_fdata(dtype=np.float32)
    mask_img = nib.load(mask_path)
    mask = mask_img.get_fdata() > 0

    if scan.shape != mask_img.shape or not np.allclose(scan.affine, mask_img.affine, atol=1e-3):
        raise ValueError('Scan and mask are not in the same grid.')

    labels, n = ndimage.label(mask & (scan_data != 0))
    if n > 0:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        mask = labels == (np.argmax(sizes) + 1)

    mask = ndimage.binary_fill_holes(mask)
    out = nib.Nifti1Image((scan_data * mask).astype(np.float32), scan.affine)
    nib.save(out, out_path)

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