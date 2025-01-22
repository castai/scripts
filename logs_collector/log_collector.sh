#!/bin/bash
# Only an initial POC boiler plate script to test if we can
# collect kubelet logs by deploying a daemonset and then
# exec into each daemonset pods to collect the journalctl logs output

set -euo pipefail

# Create temp directory
TMP_DIR=$(mktemp -d -t node-logs)
trap cleanup SIGINT SIGTERM EXIT

echo $TMP_DIR

cleanup() {
    rm -rf $TMP_DIR
    exit
}

DATE=$(date -u +%Y-%m-%dT%H:%M:%S)

CONTEXT=$(kubectl config current-context)
echo "Using current context: $CONTEXT"

CLUSTERINFO=$(kubectl cluster-info)
# Deploy daemonset debugger-sh.yaml
echo "Deploying node-log-collector-daemonset"
kubectl apply -f https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/node-log-collector-daemonset.yaml
# kubectl apply -f node-log-collector-daemonset.yaml
sleep 10

# Get all daemonset pods
unset COLLECTORDS
COLLECTORDS=$(kubectl get pods -n castai-agent -l app=nodelog -o jsonpath='{.items[*].metadata.name}')
if [ -z "$COLLECTORDS" ]; then
    echo "Unable to deploy daemonset"
    exit 1
fi

echo "Collecting kubelet logs"
# Loop through all nodes
for POD in $COLLECTORDS; do
    NODENAME=$(kubectl get pod $POD -n castai-agent -o jsonpath='{.spec.nodeName}')
    kubectl exec -n castai-agent $POD -- chroot /host /bin/bash -c "journalctl -u kubelet" > $TMP_DIR/$NODENAME-kubelet.log
done

echo "Collecting containerd logs"
# Loop through all nodes
for POD in $COLLECTORDS; do
    NODENAME=$(kubectl get pod $POD -n castai-agent -o jsonpath='{.spec.nodeName}')
    kubectl exec -n castai-agent $POD -- chroot /host /bin/bash -c "journalctl -u containerd" > $TMP_DIR/$NODENAME-containerd.log
done

# Check logs 
ls -l $TMP_DIR

# Zip all logs
echo "Zipping all logs"
tar -czf "${DATE}node-logs.tar.gz" $TMP_DIR

# Cleanup
echo "Cleaning up"
rm -rf $TMP_DIR

kubectl delete -f https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/node-log-collector-daemonset.yaml --now
# kubectl delete -f node-log-collector-daemonset.yaml --now