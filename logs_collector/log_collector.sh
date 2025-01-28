#!/bin/bash
set -euo pipefail

# Create temp directory
TMP_DIR=$(mktemp -d -t node-logs)
# trap $(rm -r $TMP_DIR) SIGINT SIGTERM EXIT

DEFAULT_NS="castai-agent"
NAMESPACE="${1:=$DEFAULT_NS}"
DATE=$(date -u +%Y-%m-%dT%H:%M:%S | tr -d ":" | tr -d "-")
CLUSTERNAME=$(kubectl config view --minify -o jsonpath={'.clusters[].name'} | tr -d '[:space:]' | tr -d "-" | tr -d "." | cut -c1-15)
CONTEXT=$(kubectl config current-context)
NODE_COUNT=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}' | wc -w)
echo "Using current context: $CONTEXT"

echo "Deploying node-log-collector-daemonset"
kubectl apply -f https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/node-log-collector-daemonset.yaml
# trap $(kubectl delete -f node-log-collector-daemonset.yaml --now) SIGINT SIGTERM EXIT
sleep 10

POD_COUNT=$(kubectl get -n $NAMESPACE daemonset node-log-collector -o jsonpath='{.status.numberReady}')
while [ "$POD_COUNT" -ne "$NODE_COUNT" ]; do
    echo "Waiting for all daemonset pods to be ready"
    sleep 5
    POD_COUNT=$(kubectl get -n $NAMESPACE daemonset node-log-collector -o jsonpath='{.status.numberReady}')
done

# Get all daemonset pods
unset COLLECTORDS
COLLECTORDS=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=node-log-collector -o jsonpath='{.items[*].metadata.name}')
if [ -z "$COLLECTORDS" ]; then
    echo "Unable to deploy daemonset" 
    exit 1
fi

echo "Collecting node logs"
# Loop through all nodes
for POD in $COLLECTORDS; do
    NODENAME=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.spec.nodeName}')
    kubectl exec -n $NAMESPACE $POD -- chroot /host /bin/bash -c "journalctl -u kubelet" > $TMP_DIR/$NODENAME-kubelet.log
    kubectl exec -n $NAMESPACE $POD -- chroot /host /bin/bash -c "journalctl -u containerd" > $TMP_DIR/$NODENAME-containerd.log
done

# Zip all logs
echo "Zipping all logs"
tar -czf "${DATE}-${CLUSTERNAME}-logs.tar.gz" $TMP_DIR

# Cleanup
kubectl delete -n $NAMESPACE -f https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/node-log-collector-daemonset.yaml --now
