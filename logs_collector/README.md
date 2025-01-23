# Requirements
- kubectl
- Current-context set correctly to target cluster

# Usage

```
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/log_collector.sh | bash
```

This will deploy a daemonset. And would execute on all daemonset pods to collect the `kubelet` and `containerd` logs of the nodes.
Once complete, a tar.gz file will be created, that contains the collected logs.

```
tar -xvf <archived_file_name>
```
