#!/bin/bash

# Directory containing backed-up deployment YAMLs
BACKUP_DIR="backup"

# Ensure namespace is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <namespace> [deployment]"
  echo " - If only namespace is provided, it restores all deployments from backup."
  echo " - If a deployment name is provided, it restores only that deployment."
  exit 1
fi

NAMESPACE=$1
DEPLOYMENT=$2

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Error: Backup directory '$BACKUP_DIR' does not exist."
  exit 1
fi

rollback_deployment() {
  local deployment_name=$1
  local backup_file="$BACKUP_DIR/${deployment_name}.yaml"

  if [ ! -f "$backup_file" ]; then
    echo "Warning: No backup found for deployment $deployment_name. Skipping."
    return
  fi

  echo "Rolling back deployment: $deployment_name using backup file: $backup_file"

  # Restore the backup using kubectl replace --force to apply it completely
  kubectl replace --force -f "$backup_file" -n "$NAMESPACE"

  if [ $? -eq 0 ]; then
    echo "Successfully restored $deployment_name from backup."
  else
    echo "Failed to restore $deployment_name."
  fi
}

if [ -z "$DEPLOYMENT" ]; then
  echo "Rolling back all deployments in namespace: $NAMESPACE"

  for backup_file in "$BACKUP_DIR"/*.yaml; do
    if [ -f "$backup_file" ]; then
      dep_name=$(basename "$backup_file" .yaml)
      rollback_deployment "$dep_name"
    fi
  done
else
  rollback_deployment "$DEPLOYMENT"
fi

echo "Rollback process complete."