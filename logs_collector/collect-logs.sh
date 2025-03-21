#!/bin/bash
set -euo pipefail

# Create temp directory
TMP_DIR="$PWD/castai-logs"
mkdir -p "$TMP_DIR"
# trap $(rm -r $TMP_DIR) SIGINT SIGTERM EXIT

DEFAULT_NS="castai-agent"
# NAMESPACE="${1:-$DEFAULT_NS}"
DATE=$(date -u +%Y-%m-%dT%H:%M:%S | tr -d ":" | tr -d "-")
CLUSTERNAME=$(kubectl config view --minify -o jsonpath={'.clusters[].name'} | tr -d '[:space:]' | tr -d "-" | tr -d "." | cut -c1-15)
CONTEXT=$(kubectl config current-context)
NODE_COUNT=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}' | wc -w)
echo "Using current context: $CONTEXT"
NODE_LIST=()

for ARG in "$@"; do
    NODE_LIST+=("$ARG")
done

# Get castai components logs
CPODS=$(kubectl get pods -n castai-agent | grep "castai" | awk '{print $1}')
for POD in $CPODS; do
    echo "Collecting logs for pod: $POD"
    kubectl logs -n castai-agent $POD > $TMP_DIR/$POD.log
done

# If node names are provided, collect node logs
if [ ${#NODE_LIST[@]} -gt 0 ]; then
    echo "Deploy debug pod"
    for NODE in "${NODE_LIST[@]}"; do
        kubectl debug node/$NODE --image ubuntu -- /bin/bash -c 'while true; do sleep 30; done;'
    done
    sleep 10

    # Get all debug pods
    DPODS=$(kubectl get pods -n castai-agent | grep "node-debugger" | awk '{print $1}')

    for POD in $DPODS; do
        NODENAME=$(kubectl get pod $POD -n castai-agent -o jsonpath='{.spec.nodeName}')
        echo "Collecting logs for node: $NODENAME"
        kubectl exec -n castai-agent $POD -- chroot /host /bin/bash -c "journalctl -u kubelet" > $TMP_DIR/$NODENAME-kubelet.log
        kubectl exec -n castai-agent $POD -- chroot /host /bin/bash -c "journalctl -u containerd" > $TMP_DIR/$NODENAME-containerd.log
        sleep 5
        kubectl delete pod $POD -n castai-agent
    done
fi

# Zip all logs
echo "Zipping all logs"
tar -czf "${DATE}-${CLUSTERNAME}-logs.tar.gz" $TMP_DIR

rm -r $TMP_DIR

