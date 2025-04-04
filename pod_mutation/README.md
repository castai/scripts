## Pod mutation scripts

exporter.sh - Copies pod mutation rules from a source cluster to other clusters.

Set the API_KEY environment var
```
export API_KEY=<CASTAI_API_KEY>
```

Set the following variables
```
DRY_RUN=true
ORG_API_KEY=${ORG_API_KEY:-""}
ORG_ID="<ORGANIZATION_ID>"
CLUSTERID_MUTATION_SRC="<CLUSTERID_OF_POD_MUTATION_SOURCE>"
CLUSTERID_MUTATION_DEST=("<CLUSTERID_OF_POD_MUTATION_DESTINATION_01>" "<CLUSTERID_OF_POD_MUTATION_DESTINATION_02>")
```
