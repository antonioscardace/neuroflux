#!/bin/bash

echo -e "\n⚙️  Start Preprocessing the sMRI..."
source bash/common.sh

set -euo pipefail
trap 'echo "⚠️  Error in line: $LINENO"; exit 1' ERR

# Preprocess the given sMRI using the following pipeline:
# 1. Bias Field Correction
# 2. Affine Registration
# 3. Skull Stripping
# 4. Intensity Normalization
# 5. Brain Segmentation and ROI Volume Extraction
# 6. 4D Mask Creation

N_WORKERS=$1
RAW_MRI="$2"
TEMPLATE="$3"
ATLAS="$4"
OUTDIR="$5"

VOLUMES_COMMON="-v $OUTDIR:/out -v $RAW_MRI:/input.nii.gz:ro -v $TEMPLATE:/template.nii.gz:ro -v $ATLAS:/atlas.json:ro"
CMD_ANTS="docker run --rm $VOLUMES_COMMON -u $UID_GID antsx/ants:2.6.2"
CMD_FREESURFER="docker run --rm $VOLUMES_COMMON -u $UID_GID freesurfer/freesurfer:7.4.1"
CMD_NEUROFLUX="docker run --rm $VOLUMES_COMMON -u $UID_GID antonioscardace/neuroflux:latest"

# Check whether preprocessing has already been completed for this scan.
# If so, exit successfully to avoid redundant computation.

echo "🔍 [Step 0/6] Checking if preprocessing has already been completed..."
if [ -s "$OUTDIR/$MRI_SEGM_4D" ]; then
    echo "✅ Scan already preprocessed"
    exit 0
fi

# Step 1: Perform Bias Field Correction using ANTs N4BiasFieldCorrection.
# Verify that the operation completed successfully.

echo "🧠 [Step 1/6] Running Bias Field Correction..."
$CMD_ANTS N4BiasFieldCorrection \
    -i /input.nii.gz \
    -o /out/$MRI_CORRECTED \
    -d 3 -s 3 > /dev/null

[ -s "$OUTDIR/$MRI_CORRECTED" ] || { echo "❌ Bias Field Correction failed"; exit 1; }

# Step 2: Perform affine registration using ANTs antsRegistrationSyNQuick.
# Verify that the operation completed successfully.

echo "🧠 [Step 2/6] Running Affine Registration..."
$CMD_ANTS antsRegistrationSyNQuick.sh \
    -f /template.nii.gz \
    -m /out/$MRI_CORRECTED \
    -o /out/$MRI_MAT_PREFIX \
    -d 3 -t a > /dev/null

mv "$OUTDIR/$MRI_WARPED_TEMP" "$OUTDIR/$MRI_WARPED"
[ -s "$OUTDIR/$MRI_WARPED" ] && [ -s "$OUTDIR/$MRI_TO_MNI_MAT" ] || { echo "❌ Affine Registration failed"; exit 1; }

# Step 3: Perform skull stripping using HD-BET.
# Verify that the operation completed successfully.

echo "🧠 [Step 3/6] Running Skull Stripping..."
hd-bet -i "$OUTDIR/$MRI_WARPED" \
    -o "$OUTDIR/$MRI_SKULLSTRIP" \
    -device cpu \
    --save_bet_mask > /dev/null 2>&1

mv "$OUTDIR/$MRI_BRAIN_MASK_TEMP" "$OUTDIR/$MRI_BRAIN_MASK"
[ -s "$OUTDIR/$MRI_SKULLSTRIP" ] && [ -s "$OUTDIR/$MRI_BRAIN_MASK" ] || { echo "❌ Skull Stripping failed"; exit 1; }

# Step 4: Perform intensity normalization using WhiteStripe.
# Verify that the operation completed successfully.

echo "🧠 [Step 4/6] Running Intensity Normalization..."
ws-normalize -mo t1 \
    -m "$OUTDIR/$MRI_BRAIN_MASK" \
    -o "$OUTDIR/$MRI_PREPROCESSED" \
    "$OUTDIR/$MRI_SKULLSTRIP"

[ -s "$OUTDIR/$MRI_PREPROCESSED" ] || { echo "❌ Intensity Normalization failed"; exit 1; }

# Step 5: Perform brain segmentation and ROI volume extraction using SynthSeg 2.0 with parcellation.
# Convert the volume output to a tidy format with ROI label IDs.
# Verify that the operations completed successfully.

echo "🧠 [Step 5/6] Running Segmentation and Volume Extraction..."
$CMD_FREESURFER mri_synthseg \
    --i /out/$MRI_PREPROCESSED \
    --o /out/$MRI_SEGM \
    --vol /out/$MRI_SEGM_CSV \
    --parc --cpu --threads $N_WORKERS > /dev/null

$CMD_NEUROFLUX synthseg_tidy \
    --csv_path "/out/$MRI_SEGM_CSV" \
    --atlas_map_path /atlas.json \
    --output_path "/out/$MRI_SEGM_CSV"
    
[ -s "$OUTDIR/$MRI_SEGM" ] && [ -s "$OUTDIR/$MRI_SEGM_CSV" ] || { echo "❌ SynthSeg failed"; exit 1; }

# Step 6: Create a 4D one-hot mask from the SynthSeg segmentation.
# Verify that the operation completed successfully.

echo "🧠 [Step 6/6] Running 4D Mask Creation..."
$CMD_NEUROFLUX synthseg_one_hot \
    --scan_path "/out/$MRI_SEGM" \
    --output_path "/out/$MRI_SEGM_4D"
    
[ -s "$OUTDIR/$MRI_SEGM_4D" ] || { echo "❌ 4D Mask Creation failed"; exit 1; }

# Remove intermediate files.
# Keep only useful preprocessing outputs.

echo "🧹 Cleaning up intermediate files..."
find "$OUTDIR" -maxdepth 1 -type f ! \( \
    -name $MRI_WARPED \
    -o -name $MRI_PREPROCESSED \
    -o -name $MRI_BRAIN_MASK \
    -o -name $MRI_SEGM \
    -o -name $MRI_SEGM_CSV \
    -o -name $MRI_SEGM_4D \
\) -exec rm {} +