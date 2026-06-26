#!/usr/bin/env bash
# dagger_deploy.sh — drive the Dagger pipeline + (optional) cloud deploy.
# Stub: real implementation per references/shipping.md#una--dagger.
set -euo pipefail
MODULE_PATH="${MODULE_PATH:-./dagger}"
dagger -m "$MODULE_PATH" call bootstrap --source=.
dagger -m "$MODULE_PATH" call test --source=.
case "${DEPLOY_TARGET:-}" in
  cloud-run)  gcloud run deploy "${SERVICE_NAME:?SERVICE_NAME required}" --source=. ;;
  modal)      modal deploy "${MODAL_APP:?MODAL_APP required}" ;;
  lambda-labs) echo "ssh + docker compose deploy: implement when an SSH target is wired" ;;
  "")         echo "no DEPLOY_TARGET set — built images only" ;;
  *)          echo "unknown DEPLOY_TARGET: $DEPLOY_TARGET" >&2; exit 2 ;;
esac
