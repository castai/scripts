# CAST AI Graceful Cordon, Drain, and Delete Script

Lightweight script for safely managing CAST AI nodes. Cordons, drains (respecting PDBs), and optionally deletes nodes.

## Usage

```bash
chmod +x castai-graceful-cdd.sh

# Preview operations
./castai-graceful-cdd.sh --dry-run

# Cordon and drain nodes
./castai-graceful-cdd.sh

# Cordon, drain, and delete nodes
./castai-graceful-cdd.sh --delete
```

## Configuration

Override defaults with environment variables:

```bash
LABEL_SELECTOR="my-label=my-value" MAX_RETRIES=5 ./castai-graceful-cdd.sh
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LABEL_SELECTOR` | `provisioner.cast.ai/managed-by=cast.ai` | Node label selector |
| `DRAIN_TIMEOUT` | `10m` | Drain attempt timeout |
| `MAX_RETRIES` | `3` | Max retry attempts |
| `RETRY_SLEEP` | `30` | Seconds between retries |

## Troubleshooting

**PDB violations**: Check disruption budgets with `kubectl get pdb -A`

**Capacity issues**: Scale cluster or wait - script auto-retries

**Debug**: `kubectl get pods -A -o wide --field-selector spec.nodeName=<node>`
