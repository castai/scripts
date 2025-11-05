#!/bin/bash
set -euo pipefail

# === Usage ===
# This script installs/upgrades CAST AI agent and controllers.
#
# Usage:
#   ./reconnect_castai.sh
#   # OR with explicit cluster name:
#   CLUSTER_NAME=my-cluster ./reconnect_castai.sh
#
# The script will:
#   1. Auto-detect cluster name from kubectl context (if CLUSTER_NAME not provided)
#   2. Ensure castai-agent is installed/upgraded with metadataStore.enabled=true and provider=anywhere
#   3. Wait for ConfigMap to be created and get ClusterID
#   4. Install/upgrade all CAST AI controllers
#
# Environment variables:
#   CASTAI_API_TOKEN - Required: API token for CAST AI
#   CREDENTIALS_SCRIPT_API_TOKEN - Required: Token for getting controller credentials
#   CLUSTER_NAME - Required: Cluster name (auto-detected from kubectl context if not provided)
#   CASTAI_API_URL - Optional: API URL (defaults to https://api.cast.ai)
#   CASTAI_ORGANIZATION_ID - Optional: Organization ID for pod-mutator
#   CLEAN_OLD_RELEASES - Optional: Set to "true" to remove old non-agent helm releases

# === Constants ===
readonly CASTAI_API_URL="${CASTAI_API_URL:-https://api.cast.ai}"
readonly REPOSITORY="${REPOSITORY:-us-docker.pkg.dev/castai-hub/library}"
readonly CONFIG_MAP_NAME="castai-agent-metadata"
readonly CLUSTER_ID_JSON_PATH='{.data.CLUSTER_ID}'
readonly NAMESPACE="castai-agent"
readonly HELM_REPO="castai-helm"
readonly HELM_REPO_URL="https://castai.github.io/helm-charts"
readonly METRICS_SERVER_URL="https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
readonly CONFIG_MAP_TIMEOUT=300
readonly ROLLOUT_TIMEOUT=300
readonly HELM_MIN_VERSION_MAJOR=3
readonly HELM_MIN_VERSION_MINOR=14

# === Configuration ===
CLEAN_OLD_RELEASES="${CLEAN_OLD_RELEASES:-false}"

# === Helper Functions ===
log() {
  echo -e "█ $*"
}

ok() {
  echo -e "✓ $*"
}

error() {
  echo "Error: $*" >&2
  exit 1
}

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "Missing dependency: $1"
  fi
}

# === Validation Functions ===
validate_requirements() {
  [ -n "${CASTAI_API_TOKEN:-}" ] || error "CASTAI_API_TOKEN is required"
  [ -n "${CREDENTIALS_SCRIPT_API_TOKEN:-}" ] || error "CREDENTIALS_SCRIPT_API_TOKEN is required"
  
  need kubectl
  need helm
  need jq
}

check_helm_version() {
  local helm_version
  local helm_major
  local helm_minor
  
  helm_version=$(helm version --template "{{.Version}}" | sed 's/^v//')
  helm_major="${helm_version%%.*}"
  helm_minor=$(echo "${helm_version}" | cut -d. -f2)
  
  if [ "${helm_major}" -lt "${HELM_MIN_VERSION_MAJOR}" ] || \
     ([ "${helm_major}" -eq "${HELM_MIN_VERSION_MAJOR}" ] && \
      [ "${helm_minor}" -lt "${HELM_MIN_VERSION_MINOR}" ]); then
    error "Helm >= ${HELM_MIN_VERSION_MAJOR}.${HELM_MIN_VERSION_MINOR}.0 required, found ${helm_version}"
  fi
}

detect_cluster_name() {
  # Check if CLUSTER_NAME is already set (from environment or previous detection)
  if [ -n "${CLUSTER_NAME:-}" ]; then
    ok "Using cluster name: ${CLUSTER_NAME}"
    return 0
  fi
  
  log "CLUSTER_NAME not provided, detecting from kubectl context"
  local detected_name
  detected_name=$(kubectl config view --minify -o jsonpath='{.clusters[0].name}' 2>/dev/null || echo "")
  
  if [ -z "${detected_name}" ]; then
    detected_name=$(kubectl config current-context 2>/dev/null || echo "")
  fi
  
  if [ -z "${detected_name}" ]; then
    error "CLUSTER_NAME is required and could not be auto-detected from kubectl context. " \
          "Please set CLUSTER_NAME environment variable or ensure kubectl context is configured"
  fi
  
  # Set the global variable
  export CLUSTER_NAME="${detected_name}"
  ok "Auto-detected cluster name: ${CLUSTER_NAME}"
}

# === Setup Functions ===
setup_metrics_server() {
  if kubectl get --raw /apis/metrics.k8s.io >/dev/null 2>&1; then
    return 0
  fi
  
  log "Installing Kubernetes metrics-server"
  kubectl apply -f "${METRICS_SERVER_URL}" >/dev/null
  ok "metrics-server installed"
  
  log "Waiting for Kubernetes metrics-server to be ready"
  local insecure_tls_handled=0
  local internal_networking_handled=0
  
  while ! kubectl -n kube-system wait \
    "--for=condition=Ready" \
    pod -l k8s-app=metrics-server \
    --timeout=5s >/dev/null 2>&1; do
    
    if [ "${insecure_tls_handled}" = "0" ] && \
       kubectl -n kube-system logs -l k8s-app=metrics-server 2>&1 | grep -q 'cannot validate certificate'; then
      log "Enabling self-signed certificate support in Kubernetes metrics-server"
      kubectl -n kube-system patch deployment metrics-server --type json \
        -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]' \
        >/dev/null
      log "Waiting for Kubernetes metrics-server to be ready after changes"
      insecure_tls_handled=1
    elif [ "${internal_networking_handled}" = "0" ] && \
         kubectl -n kube-system logs -l k8s-app=metrics-server 2>&1 | grep -q 'dial tcp'; then
      log "Enabling InternalIP as an address preference in Kubernetes metrics-server"
      kubectl -n kube-system patch deployment metrics-server --type json \
        -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-preferred-address-types=InternalIP,Hostname,InternalDNS,ExternalDNS,ExternalIP"}]' \
        >/dev/null
      log "Waiting for Kubernetes metrics-server to be ready after changes"
      internal_networking_handled=1
    fi
    
    sleep 5
  done
  
  ok "Kubernetes metrics-server is ready"
}

setup_helm_repo() {
  log "Ensuring castai helm repo"
  helm repo add "${HELM_REPO}" "${HELM_REPO_URL}" >/dev/null 2>&1 || true
  helm repo update "${HELM_REPO}" >/dev/null 2>&1 || true
  ok "Helm repo ready"
}

wait_for_configmap() {
  local timeout="${CONFIG_MAP_TIMEOUT}"
  local elapsed=0
  
  log "Waiting for castai-agent-metadata ConfigMap"
  
  while ! kubectl -n "${NAMESPACE}" get configmap "${CONFIG_MAP_NAME}" >/dev/null 2>&1 && \
        [ "${elapsed}" -lt "${timeout}" ]; do
    sleep 5
    elapsed=$((elapsed + 5))
  done
  
  if ! kubectl -n "${NAMESPACE}" get configmap "${CONFIG_MAP_NAME}" >/dev/null 2>&1; then
    error "ConfigMap was not created. Check agent pod logs."
  fi
  
  kubectl -n "${NAMESPACE}" wait \
    --timeout=5m \
    --for "jsonpath=${CLUSTER_ID_JSON_PATH}" \
    "configmap/${CONFIG_MAP_NAME}" >/dev/null
}

get_cluster_id() {
  local cluster_id
  cluster_id=$(kubectl -n "${NAMESPACE}" get configmap "${CONFIG_MAP_NAME}" \
    -o "jsonpath=${CLUSTER_ID_JSON_PATH}")
  
  if [ -z "${cluster_id}" ]; then
    error "Failed to get CLUSTER_ID from ConfigMap"
  fi
  
  echo "${cluster_id}"
}

# === Agent Functions ===
upgrade_agent() {
  log "Upgrading agent to enable metadataStore and set provider=anywhere"
  helm upgrade castai-agent "${HELM_REPO}/castai-agent" -n "${NAMESPACE}" \
    --set "metadataStore.enabled=true" \
    --set "provider=anywhere" \
    --set "additionalEnv.ANYWHERE_CLUSTER_NAME=${CLUSTER_NAME}" \
    --reuse-values >/dev/null
  ok "Agent upgraded"
}

install_agent() {
  log "Installing castai-agent with cast anywhere settings"
  helm upgrade -i castai-agent "${HELM_REPO}/castai-agent" -n "${NAMESPACE}" \
    --set "apiKey=${CASTAI_API_TOKEN}" \
    --set "apiURL=${CASTAI_API_URL}" \
    --set "metadataStore.enabled=true" \
    --set "provider=anywhere" \
    --set "replicaCount=2" \
    --set "createNamespace=false" \
    --set "additionalEnv.ANYWHERE_CLUSTER_NAME=${CLUSTER_NAME}" \
    --create-namespace >/dev/null
  ok "Agent installed"
}

ensure_agent() {
  log "Ensuring castai-agent is configured with metadataStore and provider=anywhere"
  
  if helm -n "${NAMESPACE}" status castai-agent >/dev/null 2>&1; then
    log "Found existing castai-agent, upgrading to cast anywhere mode"
    upgrade_agent
  else
    install_agent
  fi
}

# === Controller Functions ===
get_controllers_api_key() {
  local cred_resp
  local api_key
  
  log "Requesting fresh credentials for ClusterID ${CASTAI_CLUSTER_ID}"
  cred_resp=$(curl -fsS --retry 5 --retry-all-errors -X GET \
    -H 'Accept: application/json' \
    -H "X-API-Key: ${CREDENTIALS_SCRIPT_API_TOKEN}" \
    "${CASTAI_API_URL}/v1/kubernetes/external-clusters/${CASTAI_CLUSTER_ID}/credentials-script")
  
  if [ "$(echo "${cred_resp}" | jq -r .message)" != "null" ]; then
    error "Credentials error: ${cred_resp}"
  fi
  
  api_key=$(echo "${cred_resp}" | jq -r .script)
  if [ -z "${api_key}" ] || [ "${api_key}" = "null" ]; then
    error "Empty controllers API key in response"
  fi
  
  echo "${api_key}"
}

install_controllers() {
  local controllers_api_key="$1"
  
  log "Installing/Upgrading castai-cluster-controller"
  helm upgrade -i cluster-controller "${HELM_REPO}/castai-cluster-controller" -n "${NAMESPACE}" \
    --set "castai.apiKey=${controllers_api_key}" \
    --set "castai.apiURL=${CASTAI_API_URL}" \
    --set "castai.clusterID=${CASTAI_CLUSTER_ID}" \
    --set enableTopologySpreadConstraints=true \
    --reset-then-reuse-values >/dev/null
  ok "cluster-controller ready"
  
  log "Installing/Upgrading castai-evictor (replicaCount=0)"
  helm upgrade -i castai-evictor "${HELM_REPO}/castai-evictor" -n "${NAMESPACE}" \
    --set replicaCount=0 \
    --set "image.repository=${REPOSITORY}/evictor" >/dev/null
  ok "evictor configured"
  
  log "Installing/Upgrading castai-pod-mutator"
  helm upgrade -i pod-mutator "${HELM_REPO}/castai-pod-mutator" -n "${NAMESPACE}" \
    --set "castai.apiKey=${controllers_api_key}" \
    --set "castai.apiUrl=${CASTAI_API_URL}" \
    --set "castai.clusterID=${CASTAI_CLUSTER_ID}" \
    --set "castai.organizationID=${CASTAI_ORGANIZATION_ID:-}" \
    --set enableTopologySpreadConstraints=true \
    --reset-then-reuse-values >/dev/null
  ok "pod-mutator ready"
  
  log "Installing/Upgrading castai-workload-autoscaler"
  helm upgrade -i castai-workload-autoscaler "${HELM_REPO}/castai-workload-autoscaler" -n "${NAMESPACE}" \
    --set "castai.apiKey=${controllers_api_key}" \
    --set "castai.apiURL=${CASTAI_API_URL}" \
    --set "castai.clusterID=${CASTAI_CLUSTER_ID}" \
    --reset-then-reuse-values >/dev/null
  ok "workload-autoscaler ready"
}

test_workload_autoscaler() {
  log "Testing castai-workload-autoscaler"
  kubectl -n "${NAMESPACE}" rollout status deploy/castai-workload-autoscaler \
    --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || true
  
  test_logs() {
    echo "Test of castai-workload-autoscaler has failed. " >&2
    echo "Please go to https://docs.cast.ai/docs/workload-autoscaling-overview#failed-helm-test-hooks to investigate." >&2
    echo "" >&2
    kubectl logs -n "${NAMESPACE}" pod/test-castai-workload-autoscaler-verification 2>/dev/null || true
  }
  
  trap test_logs INT TERM ERR
  helm test castai-workload-autoscaler -n "${NAMESPACE}" >/dev/null 2>&1 || true
  trap - INT TERM ERR
}

restart_components() {
  log "Restarting castai-agent and controllers"
  
  # Restart agent (try deployment first, then statefulset)
  kubectl -n "${NAMESPACE}" rollout restart deployment/castai-agent >/dev/null 2>&1 || \
    kubectl -n "${NAMESPACE}" rollout restart statefulset/castai-agent >/dev/null 2>&1 || true
  
  # Restart controllers
  kubectl -n "${NAMESPACE}" rollout restart deployment/cluster-controller >/dev/null 2>&1 || true
  kubectl -n "${NAMESPACE}" rollout restart deployment/castai-pod-mutator >/dev/null 2>&1 || true
  kubectl -n "${NAMESPACE}" rollout restart deployment/castai-workload-autoscaler >/dev/null 2>&1 || true
  
  # Restart evictor only if running (replicaCount > 0)
  if kubectl -n "${NAMESPACE}" get deployment castai-evictor >/dev/null 2>&1; then
    local replicas
    replicas=$(kubectl -n "${NAMESPACE}" get deployment castai-evictor \
      -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    
    if [ "${replicas}" != "0" ] && [ -n "${replicas}" ]; then
      kubectl -n "${NAMESPACE}" rollout restart deployment/castai-evictor >/dev/null 2>&1 || true
    fi
  fi
  
  log "Waiting for restarts to complete"
  kubectl -n "${NAMESPACE}" rollout status deployment/castai-agent \
    --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || \
    kubectl -n "${NAMESPACE}" rollout status statefulset/castai-agent \
      --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || true
  
  kubectl -n "${NAMESPACE}" rollout status deployment/cluster-controller \
    --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || true
  
  kubectl -n "${NAMESPACE}" rollout status deployment/castai-pod-mutator \
    --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || true
  
  kubectl -n "${NAMESPACE}" rollout status deployment/castai-workload-autoscaler \
    --timeout="${ROLLOUT_TIMEOUT}s" >/dev/null 2>&1 || true
}

cleanup_old_releases() {
  if [ "${CLEAN_OLD_RELEASES}" != "true" ]; then
    return 0
  fi
  
  log "Cleaning old non-agent releases (cluster-controller, evictor, pod-mutator, workload-autoscaler)"
  local release
  for release in cluster-controller castai-evictor pod-mutator castai-workload-autoscaler; do
    if helm -n "${NAMESPACE}" status "${release}" >/dev/null 2>&1; then
      helm -n "${NAMESPACE}" uninstall "${release}" >/dev/null 2>&1 || true
    fi
  done
  ok "Old releases cleaned"
}

# === Main Execution ===
main() {
  validate_requirements
  check_helm_version
  setup_metrics_server
  setup_helm_repo
  detect_cluster_name
  
  ensure_agent
  wait_for_configmap
  
  CASTAI_CLUSTER_ID=$(get_cluster_id)
  ok "Found ClusterID: ${CASTAI_CLUSTER_ID}"
  
  cleanup_old_releases
  
  CASTAI_CONTROLLERS_API_KEY=$(get_controllers_api_key)
  ok "Got controllers API key"
  
  install_controllers "${CASTAI_CONTROLLERS_API_KEY}"
  test_workload_autoscaler
  restart_components
  
  ok "Finished"
}

main "$@"
