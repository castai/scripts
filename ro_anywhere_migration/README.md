# CAST AI Migration Script: Read-Only to Cast Anywhere

This script helps you migrate your CAST AI setup from read-only mode to "cast anywhere" mode. It upgrades your existing agent and installs all necessary controllers.

## Prerequisites

Before running this script, ensure you have:

1. **kubectl** installed and configured with access to your cluster
2. **helm** version 3.14.0 or higher installed
3. **jq** installed (JSON processor)
4. **CAST AI API tokens**:
   - `CASTAI_API_TOKEN` - Your CAST AI API token (used for agent registration and API operations)
   - `CREDENTIALS_SCRIPT_API_TOKEN` - Token for fetching controller credentials (used to get controller-specific API key)

## Quick Start

### Migrate from Read-Only to Cast Anywhere

**Option 1: Auto-detect Cluster Name**

```bash
./reconnect_castai.sh
```

The script will automatically detect your cluster name from your kubectl context.

**Option 2: Specify Cluster Name**

```bash
CLUSTER_NAME=my-cluster-name ./reconnect_castai.sh
```

**Before Running:**
- Ensure you have an existing castai-agent installed (read-only mode)
- Export required environment variables:
  ```bash
  export CASTAI_API_TOKEN="your-api-token"
  export CREDENTIALS_SCRIPT_API_TOKEN="your-credentials-token"
  ```

**Note:** 
- Both tokens are required. They serve different purposes:
  - `CASTAI_API_TOKEN` is used by the agent and for API operations
  - `CREDENTIALS_SCRIPT_API_TOKEN` is used to fetch controller-specific credentials
- If the agent doesn't exist, the script will install it fresh with cast anywhere configuration

## What the Script Does

This migration script performs the following steps:

1. **Checks dependencies** - Verifies kubectl, helm, and jq are installed
2. **Installs metrics-server** - If not already present in your cluster
3. **Migrates agent** - Upgrades your existing read-only castai-agent to cast anywhere mode:
   - Enables `metadataStore.enabled=true` (creates ConfigMap with ClusterID)
   - Sets `provider=anywhere` (enables cast anywhere mode)
   - Cleans up any duplicate read-only cluster entries from CAST AI
4. **Waits for registration** - Waits for the agent to register and create the ConfigMap
5. **Installs controllers** - Installs/upgrades all CAST AI controllers:
   - cluster-controller
   - castai-evictor (with replicaCount=0)
   - pod-mutator
   - castai-workload-autoscaler
6. **Restarts components** - Restarts agent and controllers to ensure they pick up the new configuration

## Environment Variables

### Required

| Variable | Description | Usage |
|----------|-------------|-------|
| `CASTAI_API_TOKEN` | Your CAST AI API token | Used by the agent for registration and for API operations (querying/deleting clusters) |
| `CREDENTIALS_SCRIPT_API_TOKEN` | Token for fetching controller credentials | Used to call the credentials-script endpoint to get controller-specific API keys |

**Note:** Both tokens are required. In some cases, they may be the same token, but the script requires both to be set as they serve different purposes in the workflow.

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `CLUSTER_NAME` | Cluster name in CAST AI | Auto-detected from kubectl context |
| `CASTAI_API_URL` | CAST AI API endpoint | `https://api.cast.ai` |
| `CASTAI_ORGANIZATION_ID` | Organization ID for pod-mutator | Not set |
| `CLEAN_OLD_RELEASES` | Remove old non-agent helm releases | `false` |

## Example Usage

### Basic Migration (Auto-detect Cluster Name)

```bash
export CASTAI_API_TOKEN="your-api-token"
export CREDENTIALS_SCRIPT_API_TOKEN="your-credentials-token"
./reconnect_castai.sh
```

The script will automatically detect your cluster name from your kubectl context.

### Migration with Custom Cluster Name

```bash
export CASTAI_API_TOKEN="your-api-token"
export CREDENTIALS_SCRIPT_API_TOKEN="your-credentials-token"
export CLUSTER_NAME="production-cluster"
./reconnect_castai.sh
```

### Clean Old Releases Before Migration

```bash
export CASTAI_API_TOKEN="your-api-token"
export CREDENTIALS_SCRIPT_API_TOKEN="your-credentials-token"
export CLEAN_OLD_RELEASES="true"
./reconnect_castai.sh
```

## Migration Process

When you run this script, it will:

1. **Detect existing agent** - Finds your existing castai-agent deployment
2. **Clean up duplicates** - Removes any duplicate read-only cluster entries in CAST AI (if found)
3. **Upgrade agent** - Updates your agent configuration:
   - Enables metadataStore to create ConfigMap
   - Changes provider from read-only to "anywhere"
   - Sets cluster name for registration
4. **Wait for registration** - Agent registers with CAST AI and creates ConfigMap with ClusterID
5. **Install controllers** - Installs/upgrades all CAST AI controllers with the new ClusterID
6. **Restart components** - Restarts all components to ensure they use the new configuration

**Note:** Your agent pod will continue running during the upgrade. The migration is non-disruptive.

## Manual Cluster Cleanup

If you need to disconnect or clean up your cluster manually, you can use the CAST AI disconnect API. For details, see the [CAST AI API documentation](https://docs.cast.ai/reference/externalclusterapi_disconnectcluster).

**Note:** This is not part of the migration script workflow. The script focuses solely on migrating from read-only to cast anywhere mode.

## Troubleshooting

### ConfigMap Not Created

If the script fails with "ConfigMap was not created", check:

1. Agent pod logs:
   ```bash
   kubectl -n castai-agent logs -l app=castai-agent
   ```

2. Agent pod status:
   ```bash
   kubectl -n castai-agent get pods
   ```

### Cluster Name Not Detected

If cluster name auto-detection fails:

1. Check your kubectl context:
   ```bash
   kubectl config current-context
   ```

2. Provide cluster name explicitly:
   ```bash
   CLUSTER_NAME=your-cluster-name ./reconnect_castai.sh
   ```

### Verify Installation

After running the script, verify the installation:

```bash
# Check agent status
helm -n castai-agent status castai-agent

# Check ConfigMap
kubectl -n castai-agent get configmap castai-agent-metadata

# Get Cluster ID
kubectl -n castai-agent get configmap castai-agent-metadata -o jsonpath='{.data.CLUSTER_ID}'

# Check all CAST AI components
helm -n castai-agent list
```

## Notes
- The script uses `--reuse-values` when upgrading to preserve existing settings
- The script creates the `castai-agent` namespace if it doesn't exist
- All components are installed in the `castai-agent` namespace

## Support

For issues or questions:
1. Check the agent pod logs
2. Review the CAST AI documentation
3. Contact CAST AI support

