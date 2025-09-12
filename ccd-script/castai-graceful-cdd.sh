#!/bin/bash
# castai-graceful-cdd.sh
# Lightweight script to cordon, drain, and optionally delete CAST AI nodes.
# Usage: ./castai-graceful-cdd.sh [--delete] [--dry-run]

set -euo pipefail

# Simple command line argument parsing
DELETE_NODES="false"
DRY_RUN="false"

for arg in "$@"; do
  case $arg in
    --delete)
      DELETE_NODES="true"
      ;;
    --dry-run)
      DRY_RUN="true"
      ;;
    --help|-h)
      echo "Usage: $0 [--delete] [--dry-run]"
      echo "  --delete   Delete node objects after draining"
      echo "  --dry-run  Show what would be done without making changes"
      exit 0
      ;;
  esac
done

# Core settings (can be overridden with environment variables)
LABEL_SELECTOR="${LABEL_SELECTOR:-provisioner.cast.ai/managed-by=cast.ai}"
DRAIN_TIMEOUT="${DRAIN_TIMEOUT:-10m}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_SLEEP="${RETRY_SLEEP:-30}"

# Simple logging
log(){ echo "[$(date +'%H:%M:%S')] $*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

# Check prerequisites
command -v kubectl >/dev/null 2>&1 || die "kubectl not found"
kubectl cluster-info >/dev/null 2>&1 || die "kubectl can't reach cluster"

# Find CAST AI nodes
NODES=$(kubectl get nodes -l "$LABEL_SELECTOR" -o name 2>/dev/null || true)
if [[ -z "${NODES}" ]]; then
  log "No CAST AI nodes found with label: $LABEL_SELECTOR"
  exit 0
fi

log "Found CAST AI nodes:"
echo "$NODES" | sed 's/^/  - /'

if [[ "$DRY_RUN" == "true" ]]; then
  log "DRY RUN MODE - No changes will be made"
fi

# Process each node
for NODE in $NODES; do
  log "Processing $NODE"
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "  Would cordon $NODE"
    log "  Would drain $NODE (respecting PDBs)"
    if [[ "$DELETE_NODES" == "true" ]]; then
      log "  Would delete $NODE"
    fi
    continue
  fi
  
  # Cordon the node
  log "  Cordoning $NODE..."
  kubectl cordon "$NODE"
  
  # Drain with retries
  ATTEMPT=1
  DRAINED=false
  
  while [[ $ATTEMPT -le $MAX_RETRIES ]]; do
    log "  Draining $NODE (attempt $ATTEMPT/$MAX_RETRIES)..."
    
    if kubectl drain "$NODE" \
      --ignore-daemonsets \
      --delete-emptydir-data \
      --grace-period=60 \
      --timeout="$DRAIN_TIMEOUT" \
      --disable-eviction=false >/dev/null 2>&1; then
      
      log "  ✅ Successfully drained $NODE"
      DRAINED=true
      break
    else
      log "  ⚠️  Drain attempt $ATTEMPT failed (likely PDB/capacity issue)"
      
      if [[ $ATTEMPT -lt $MAX_RETRIES ]]; then
        log "  Waiting ${RETRY_SLEEP}s before retry..."
        sleep "$RETRY_SLEEP"
      fi
      ((ATTEMPT++))
    fi
  done
  
  if [[ "$DRAINED" != "true" ]]; then
    log "  ❌ Failed to drain $NODE after $MAX_RETRIES attempts"
    log "  Node remains cordoned. Check PDBs and cluster capacity."
    continue
  fi
  
  # Optional node deletion
  if [[ "$DELETE_NODES" == "true" ]]; then
    log "  Deleting node object $NODE..."
    kubectl delete "$NODE"
    log "  ✅ Deleted $NODE"
  fi
done

log "Completed processing all CAST AI nodes"