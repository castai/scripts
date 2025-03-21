# Requirements
- kubectl
- Current-context set correctly to target cluster

# Usage

```
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/feature/log_collector/logs_collector/castai-logs.sh | bash
```

The script will collect all of the logs in the castai-agent namespace. And if nodenames are passed as an args, the script will create a debugger pod. Then the kubelet and containerd logs of the nodes will be collected via those debugger pods.

```
tar -xvf <archived_file_name>
```
