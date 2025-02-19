#!/bin/bash

# Ensure namespace is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <namespace>"
  exit 1
fi

NAMESPACE=$1
BACKUP_DIR="backup/"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Loop through deployments and save their cleaned YAML configuration
for dep in $(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}'); do
  echo "Backing up deployment: $dep"

  # Save the deployment YAML **without status or unwanted metadata fields**
  kubectl get deployment "$dep" -n "$NAMESPACE" -o json | jq 'del(.metadata.creationTimestamp, .metadata.resourceVersion, .metadata.uid, .metadata.generation, .status)' | yq -P > "$BACKUP_DIR/${dep}.yaml"

  echo "Backup saved: $BACKUP_DIR/${dep}.yaml"
done

echo "Backup process complete. Files saved in $BACKUP_DIR/"