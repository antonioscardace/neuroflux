#!/usr/bin/env python3

import argparse
import numpy as np
import nibabel as nib

# This function converts a 3D SynthSeg segmentation into a 4D one-hot encoded mask.
# Each label in the 3D volume is represented as a separate channel in the 4D output.
# Background voxels (label 0) are excluded, and the output is saved as a float32 NIfTI file.
# Author: Antonio Scardace

def synthseg_to_one_hot(scan_path: str, out_path: str) -> None:

    scan = nib.load(scan_path)
    scan_data = scan.get_fdata().astype(np.int32)
    unique_labels = np.unique(scan_data)
    unique_labels = unique_labels[unique_labels != 0]

    shape_3d = scan_data.shape
    shape_4d = shape_3d + (len(unique_labels),)
    scan_data_4d = np.zeros(shape_4d, dtype=np.float32)
    for i, label in enumerate(unique_labels):
        scan_data_4d[..., i] = (scan_data == label).astype(np.float32)

    one_hot_mask = nib.Nifti1Image(scan_data_4d, scan.affine, scan.header)
    one_hot_mask.set_data_dtype(np.float32)
    nib.save(one_hot_mask, out_path)

# CLI for converting a 3D SynthSeg segmentation into a 4D one-hot encoded mask.
# It requires an input 3D segmentation (NIfTI) and an output path (NIfTI).
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',   type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    args = parser.parse_args()
    
    synthseg_to_one_hot(args.scan_path, args.output_path)