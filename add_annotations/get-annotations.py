import subprocess
import json

NAMESPACE = "test-namespace"
OUTPUT_FILE = "annotations.json"

def run_command(cmd):
    """Executes a shell command and returns JSON output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        result.check_returncode()
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {cmd}: {e}")
        return None

def get_configmaps():
    """Fetch all ConfigMaps in the namespace."""
    cmd = f'kubectl get configmap -n {NAMESPACE} -o json'
    return run_command(cmd)

def get_deployments():
    """Fetch all Deployments in the namespace."""
    cmd = f'kubectl get deployment -n {NAMESPACE} -o json'
    return run_command(cmd)

def map_configmaps_to_deployments(deployments, configmaps):
    """Find deployments referencing configmaps and extract annotations."""
    mapping = {}

    for deployment in deployments.get("items", []):
        deployment_name = deployment["metadata"]["name"]
        annotations = deployment["metadata"].get("annotations", {})

        # Check if Deployment references a ConfigMap
        for container in deployment["spec"]["template"]["spec"]["containers"]:
            env_from = container.get("envFrom", [])
            for env_ref in env_from:
                if "configMapRef" in env_ref:
                    configmap_name = env_ref["configMapRef"]["name"]

                    # Extract ConfigMap data
                    configmap_data = next((cm["data"] for cm in configmaps["items"] if cm["metadata"]["name"] == configmap_name), {})

                    if configmap_data:
                        missing_annotations = {k: v for k, v in configmap_data.items() if k not in annotations}
                        
                        if missing_annotations:
                            mapping[deployment_name] = {
                                "configmap": configmap_name,
                                "missing_annotations": missing_annotations
                            }

    return mapping

def save_mapping(mapping):
    """Save the mapping of missing annotations to a JSON file."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=4)
    print(f"Mappings saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    print("🔍 Fetching ConfigMaps and Deployments...")
    configmaps = get_configmaps()
    deployments = get_deployments()

    if not configmaps or not deployments:
        print("Failed to retrieve resources. Check access permissions.")
        exit(1)

    mapping = map_configmaps_to_deployments(deployments, configmaps)

    if mapping:
        print("Missing annotations found! Saving for later application...")
        save_mapping(mapping)
    else:
        print("No missing annotations detected. Nothing to apply.")

    print("Fetch and validation complete!")