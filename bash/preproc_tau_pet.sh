#!/bin/bash

echo -e "\n⚙️  Start Preprocessing the tau-PET..."
source bash/common.sh

set -euo pipefail
trap 'echo "⚠️  Error in line: $LINENO"; exit 1' ERR

# Preprocess the given PET scan using the following pipeline:
# 1. Motion Correction and Mean Image Calculation (for 4D scans)
# 2. PET-to-sMRI Registration
# 3. Spatial Normalization
# 4. Skull Stripping and Artifact Removal
# 5. Partial Volume Correction (PVC)
# 6. SUVR Normalization
# 7. ROI Feature Extraction

MRI_DIR="$1"
RAW_PET="$2"
TEMPLATE="$3"
ATLAS="$4"
OUTDIR="$5"

VOLUMES_COMMON="-v $OUTDIR:/out -v $MRI_DIR:/mri:ro -v $RAW_PET:/input.nii.gz:ro -v $TEMPLATE:/template.nii.gz:ro -v $ATLAS:/atlas.json:ro"
CMD_ANTS="docker run --rm $VOLUMES_COMMON -u $UID_GID antsx/ants:2.6.2"
CMD_FREESURFER="docker run --rm $VOLUMES_COMMON -u $UID_GID freesurfer/freesurfer:7.4.1"
CMD_NEUROFLUX="docker run --rm $VOLUMES_COMMON -u $UID_GID antonioscardace/neuroflux:latest"
CMD_PVC="docker run --rm $VOLUMES_COMMON -u $UID_GID benthomas1984/petpvc:v1.2.2"

# Check whether preprocessing has already been completed for this scan.
# If so, exit successfully to avoid redundant computation.

echo "🔍 [Step 0/7] Checking if preprocessing has already been completed..."
if [ -s "$OUTDIR/$PET_CSV" ]; then
    echo "✅ Scan already preprocessed"
    exit 0
fi

# Step 1: Perform motion correction and mean image calculation using ANTs antsMotionCorr.
# For 3D scans, the input is directly copied as the static PET image.
# Verify that the operation completed successfully.

echo "🧠 [Step 1/7] Running Motion Correction and Mean Image Calculation..."
NDIMS=$($CMD_ANTS PrintHeader /input.nii.gz | grep "dim\[0\]" | awk '{print $3}' | head -n 1)
[ "$NDIMS" -eq 4 ] && $CMD_ANTS antsMotionCorr -d 3 -o "[/out/$PET_STATIC]" -a /input.nii.gz
[ "$NDIMS" -eq 3 ] && cp "$PET_RAW" "$OUTDIR/$PET_STATIC"
[ -s "$OUTDIR/$PET_STATIC" ] || { echo "❌ Motion Correction failed"; exit 1; }

# Step 2: Perform PET-to-sMRI affine registration using ANTs antsRegistrationSyNQuick.
# Verify that the operation completed successfully.

echo "🧠 [Step 2/7] Running PET to sMRI Registration..."
$CMD_ANTS antsRegistrationSyNQuick.sh \
    -d 3 \
    -f "/mri/$MRI_WARPED" \
    -m "/out/$PET_STATIC" \
    -o "/out/$PET_MAT_PREFIX" \
    -t a -x "/mri/$MRI_BRAIN_MASK" > /dev/null 2>&1

[ -s "$OUTDIR/$PET_TO_MRI_MAT" ] || { echo "❌ PET-MRI registration failed"; exit 1; }

# Step 3: Apply spatial normalization to the template space using ANTs antsApplyTransforms.
# Verify that the operation completed successfully.

echo "🧠 [Step 3/7] Running Spatial Normalization..."
$CMD_ANTS antsApplyTransforms \
    -d 3 \
    --float \
    -n Linear \
    -i "/out/$PET_STATIC" \
    -r "/template.nii.gz" \
    -o "/out/$PET_WARPED" \
    -t "/out/$PET_TO_MRI_MAT" > /dev/null

[ -s "$OUTDIR/$PET_WARPED" ] || { echo "❌ Spatial Normalisation failed"; exit 1; }

# Step 4: Perform skull stripping and artifact removal using the brain mask.
# Verify that the operation completed successfully.

echo "🧠 [Step 4/7] Running Skull Stripping and Artifact Removal..."
$CMD_NEUROFLUX mask_apply \
    --scan_path "/out/$PET_WARPED" \
    --mask_path "/mri/$MRI_BRAIN_MASK" \
    --output_path "/out/$PET_SKULLSTRIP"

[ -s "$OUTDIR/$PET_SKULLSTRIP" ] || { echo "❌ Cleaning failed"; exit 1; }

# Step 5: Perform Partial Volume Correction (PVC) using PETPVC.
# Verify that the operation completed successfully.

echo "🧠 [Step 5/7] Running Partial Volume Correction..."
$CMD_PVC petpvc \
    -i "/out/$PET_SKULLSTRIP" \
    -m "/mri/$MRI_SEGM_4D" \
    -o "/out/$PET_PVC" \
    -x 6.0 -y 6.0 -z 6.0 \
    --pvc IY > /dev/null 2>&1

[ -s "$OUTDIR/$PET_PVC" ] || { echo "❌ PVC failed"; exit 1; }

# Step 6: Normalize the PET scan using SUVR with the reference regions.
# Verify that the operation completed successfully.

echo "🧠 [Step 6/7] Running SUVR Normalization..."
$CMD_NEUROFLUX normalize_suvr \
    --scan_path "/out/$PET_PVC" \
    --segm_path "/mri/$MRI_SEGM" \
    --output_path "/out/$PET_SUVR"

[ -s "$OUTDIR/$PET_SUVR" ] || { echo "❌ SUVR Normalization failed"; exit 1; }

# Step 7: Extract ROI-wise PET uptake features using the SynthSeg segmentation.
# Verify that the operation completed successfully.

echo "🧠 [Step 7/7] Running Feature Extraction..."
$CMD_NEUROFLUX extract_roi_uptakes \
    --scan_path "/out/$PET_SUVR" \
    --segm_path "/mri/$MRI_SEGM" \
    --atlas_map_path "/atlas.json" \
    --output_path "/out/$PET_CSV"
    
[ -s "$OUTDIR/$PET_CSV" ] || { echo "❌ Feature Extraction failed"; exit 1; }

# Remove intermediate files.
# Keep only useful preprocessing outputs.

echo "🧹 Cleaning up intermediate files..."
find "$OUTDIR" -maxdepth 1 -type f ! \( \
    -name $PET_WARPED \
    -o -name $PET_SKULLSTRIP \
    -o -name $PET_PVC \
    -o -name $PET_SUVR \
    -o -name $PET_CSV \
\) -exec rm {} +