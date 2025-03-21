# Requirements
- kubectl
- Current-context set correctly to target cluster

# Usage

Only castai component pods log
```bash
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/main/logs_collector/collect-logs.sh | bash
```

With node logs, where nodes names are defined in the argument/s
```bash
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/main/logs_collector/collect-logs.sh | bash -s -- <nodeName> <nodeName>
```

The script will collect all of the logs in the castai-agent namespace. And if nodenames are passed as an args, the script will create a debugger pod, for each node specified. Then the kubelet and containerd logs of the nodes will be collected via those debugger pods.

```
tar -xvf <archived_file_name>
```
