#!/bin/bash
# Usage: ./exporter.sh
set -euo pipefail

DRY_RUN=true
ORG_API_KEY=${ORG_API_KEY:-""}
ORG_ID="<ORGANIZATION_ID>"
CLUSTERID_MUTATION_SRC="<CLUSTERID_OF_POD_MUTATION_SOURCE>"
CLUSTERID_MUTATION_DEST=("<CLUSTERID_OF_POD_MUTATION_DESTINATION_01>" "<CLUSTERID_OF_POD_MUTATION_DESTINATION_02>")


if [ -z "$ORG_API_KEY" ]; then
    echo "Environment variable 'ORG_API_KEY' not set."
    exit 1
fi
if [ -z "$ORG_ID" ]; then
    echo "'ORG_ID' not set."
    exit 1
fi
if [ -z "$CLUSTERID_MUTATION_SRC" ]; then
    echo "'CLUSTERID_MUTATION_SRC' not set."
    exit 1
fi


# Get all pod mutation from source
MUTATION_LIST=$(curl --request GET \
     --url https://api.cast.ai/patching-engine/v1beta/organizations/$ORG_ID/clusters/$CLUSTERID_MUTATION_SRC/pod-mutations \
     --header "X-API-Key: $ORG_API_KEY" \
     --header "accept: application/json")
MUTATION_LIST=$(echo "$MUTATION_LIST" | jq 'del(.items[].id)' | jq 'del(.items[].createTime)' | jq 'del(.items[].updateTime)' | jq 'del(.items[].clusterId)' | jq 'del(.items[].organizationId)')


for CLUSTERID in "${CLUSTERID_MUTATION_DEST[@]}"; do
    for item in $(echo "$MUTATION_LIST" | jq -c '.items[]'); do
        if $DRY_RUN; then
            echo "DRY_RUN"
            echo "Applying pod mutation to cluster $CLUSTERID"
            echo "$item" | jq -c '.'
        else
            echo "Applying pod mutation to cluster $CLUSTERID"
            curl --request POST \
            --url https://api.cast.ai/patching-engine/v1beta/organizations/%7B${ORG_ID}%7D/clusters/%7B${CLUSTERID}%7D/pod-mutations \
            --header "X-API-Key: $ORG_API_KEY" \
            --header 'accept: application/json' \
            --header 'content-type: application/json' \
            --data "$item"            
        fi
    done
done
