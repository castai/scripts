## What does it do
Collect logs from all pods in the castai-agent namespace. And optionally, if node names are added as arguments. On the specified nodes, the script will collect
- kubelet logs
- containerd logs
- ipamd logs (if eks)

## Requirements
- kubectl
- Current-context set correctly to target cluster
- Current-context namespace, where `hostPath` container capability is allowed (if node logs will be collected - optional).

## Usage

Only castai component pods log
```bash
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/main/logs_collector/collect-logs.sh | bash
```

With node logs, where nodes names are defined in the argument/s
```bash
curl https://raw.githubusercontent.com/castai/scripts/refs/heads/main/logs_collector/collect-logs.sh | bash -s -- <nodeName> <nodeName>
```

>NOTE: The pod used for collecting node logs will be created on the current namespace of the context.

Share the tar file created by the script to CASTAI support team.