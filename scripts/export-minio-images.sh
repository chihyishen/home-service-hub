#!/usr/bin/env bash
# One-shot export of MinIO inventory-items into infra/inventory-images.
# MinIO's on-disk XL layout is not raw files; this uses the S3 API via minio/mc.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${INVENTORY_IMAGE_EXPORT_DIR:-$ROOT/infra/inventory-images}"
ENDPOINT="${MINIO_ENDPOINT:-http://127.0.0.1:9000}"
BUCKET="${MINIO_BUCKET_NAME:-inventory-items}"

if [[ -z "${MINIO_ROOT_USER:-}" || -z "${MINIO_ROOT_PASSWORD:-}" ]]; then
  echo "Set MINIO_ROOT_USER and MINIO_ROOT_PASSWORD (the old MinIO credentials)." >&2
  exit 1
fi

mkdir -p "$DEST"

docker run --rm --network host \
  -e MC_HOST_old="${ENDPOINT/http:\/\//http://${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}@}" \
  -v "$DEST:/export" \
  minio/mc:latest \
  cp --recursive "old/${BUCKET}/" /export/

echo "Exported $BUCKET to $DEST"
ls -1 "$DEST" | wc -l | awk '{print $1 " objects"}'
