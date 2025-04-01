#!/bin/bash
# Usage: ./exporter.sh [--dry-run]
set -euo pipefail

dry_run=false
if [ $1 == "--dry-run" ]; then
    dry_run=true
    shift
fi

ORG_API_KEY=${ORG_API_KEY:-""}
ORG_ID="1f1848fe-ac13-4e04-abc6-0ef2d578a49b"
CLUSTERID_MUTATION_SRC="07bfd0a7-3f6d-4675-8dfb-335aadc979bb"
CLUSTERID_MUTATION_DEST=("60f41cd7-2ae6-4745-8eb3-bbda88db29bc")

if [ -z "$ORG_API_KEY" ]; then
    echo "ORG_API_KEY is not set. Exiting."
    exit 1
fi

get_pod_mutation() {
    $(curl --request GET \
     --url https://api.cast.ai/patching-engine/v1beta/organizations/$ORG_ID/clusters/$CLUSTERID_MUTATION_SRC/pod-mutations \
     --header "X-API-Key: $ORG_API_KEY" \
     --header "accept: application/json")
}

# create_pod_mutation() {
#     curl --request POST \
#      --url https://api.cast.ai/patching-engine/v1beta/organizations/%7Bpod_mutation.organization_id%7D/clusters/%7Bpod_mutation.cluster_id%7D/pod-mutations \
#      --header 'X-API-Key: ' \
#      --header 'accept: application/json' \
#      --header 'content-type: application/json' \
#      --data '
# {
#   "name": "test",
#   "enabled": true
# }
# '
# }

# Get all pod mutation from source
echo "Getting pod mutation from source cluster"
MUTATION_LIST=$(get_pod_mutation)

echo "Iterating over pod mutations"
if [ $dry_run == true ]; then
    for item in $(echo "$MUTATION_LIST" | jq -c '.items[]'); do
        echo "DYRUN: Pod mutation: $item"
    done
fi

if [ $dry_run == false ]; then
    for item in $(echo "$MUTATION_LIST" | jq -c '.items[]'); do
        echo "Pod mutation: $item"
    done
fi


