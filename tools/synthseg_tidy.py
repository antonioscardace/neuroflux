#!/usr/bin/env python3

import json
import argparse
import pandas as pd

# This function transforms the SynthSeg volume output into a tidy format with ROI IDs.
# It maps ROI names to their corresponding label IDs using the atlas mapping.
# Author: Antonio Scardace

def synthseg_csv_to_tidy(csv_path: str,  out_path: str, roi_name_to_id: dict) -> None:

    df_vol = pd.read_csv(csv_path)
    df_vol = df_vol.drop(columns=['subject'], errors='ignore')
    df_tidy = df_vol.melt(var_name='roi_name', value_name='volume')

    s_rois = pd.Series(roi_name_to_id)
    norm_map_keys = s_rois.index.str.lower().str.replace(' ', '_').str.replace('-', '_')
    roi_lookup = pd.Series(data=s_rois.values, index=norm_map_keys).to_dict()
    match_keys = df_tidy['roi_name'].str.lower().str.replace(' ', '_').str.replace('-', '_')
    
    df_tidy['roi_label_id'] = match_keys.map(roi_lookup)
    df_tidy = df_tidy[['roi_label_id', 'roi_name', 'volume']]
    df_tidy['roi_label_id'] = df_tidy['roi_label_id'].astype('Int64')
    df_tidy.to_csv(out_path, index=False, header=True)
    
# CLI for converting the SynthSeg volumes CSV into a tidy format.
# It requires an input volumes file (CSV), an atlas ROI mapping, and an output path (CSV).
# Author: Antonio Scardace

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--csv_path',       type=str, required=True)
    parser.add_argument('--atlas_map_path', type=str, required=True)
    parser.add_argument('--output_path',    type=str, required=True)
    args = parser.parse_args()

    with open(args.atlas_map_path, 'r') as f:
        roi_name_to_id = json.load(f)
        synthseg_csv_to_tidy(args.csv_path, args.output_path, roi_name_to_id)