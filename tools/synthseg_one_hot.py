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
    data = np.rint(scan.get_fdata()).astype(np.int32)
    labels = np.unique(data)
    labels = labels[labels != 0]

    out = np.zeros(data.shape + (len(labels),), dtype=np.float32)
    for i, label in enumerate(labels):
        out[..., i] = (data == label)

    header = scan.header.copy()
    header.set_data_shape(out.shape)
    header.set_data_dtype(np.float32)
    nib.save(nib.Nifti1Image(out, scan.affine, header), out_path)

# CLI for converting a 3D SynthSeg segmentation into a 4D one-hot encoded mask.
# It requires an input 3D segmentation (NIfTI) and an output path (NIfTI).
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--scan_path',   type=str, required=True)
    parser.add_argument('--output_path', type=str, required=True)
    args = parser.parse_args()
    
    synthseg_to_one_hot(args.scan_path, args.output_path)