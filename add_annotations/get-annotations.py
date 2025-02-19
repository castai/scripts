import subprocess
import json
import argparse

# List of required annotations to search for
REQUIRED_ANNOTATIONS = [
    "com.fico.dmp/component-descriptor",
    "com.fico.dmp/engine-descriptor",
    "com.fico.dmp/idle-config-annotation"
]

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
    except json.JSONDecodeError:
        print(f"Error decoding JSON output from command: {cmd}")
        return None

def get_configmaps(namespace):
    """Fetch all ConfigMaps in the given namespace."""
    cmd = f'kubectl get configmap -n {namespace} -o json'
    return run_command(cmd)

def get_deployments(namespace):
    """Fetch all Deployments in the given namespace."""
    cmd = f'kubectl get deployment -n {namespace} -o json'
    return run_command(cmd)

def map_configmaps_to_deployments(deployments, configmaps):
    """Map ConfigMaps to Deployments based on references and extract specific annotations."""
    mapping = {}

    for deployment in deployments.get("items", []):
        deployment_name = deployment["metadata"]["name"]
        deployment_annotations = deployment["metadata"].get("annotations", {})

        # Find referenced ConfigMaps
        for container in deployment["spec"]["template"]["spec"]["containers"]:
            env_from = container.get("envFrom", [])
            for env_ref in env_from:
                if "configMapRef" in env_ref:
                    configmap_name = env_ref["configMapRef"]["name"]

                    # Find the ConfigMap and check for required annotations in metadata
                    configmap = next(
                        (cm for cm in configmaps.get("items", []) if cm["metadata"]["name"] == configmap_name),
                        None
                    )

                    if configmap and "annotations" in configmap["metadata"]:
                        relevant_annotations = {
                            k: v for k, v in configmap["metadata"]["annotations"].items() if k in REQUIRED_ANNOTATIONS
                        }

                        if relevant_annotations:
                            mapping[deployment_name] = {
                                "configmap": configmap_name,
                                "annotations": relevant_annotations
                            }

    return mapping

def save_mapping(mapping):
    """Save the mapping of annotations to a predefined JSON file."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=4)
    print(f"Mappings saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch annotations from ConfigMaps and map to Deployments.")
    parser.add_argument("-n", "--namespace", default="default", help="Kubernetes namespace to scan (default: 'default')")

    args = parser.parse_args()
    
    print(f"Fetching ConfigMaps and Deployments from namespace: {args.namespace}...")
    configmaps = get_configmaps(args.namespace)
    deployments = get_deployments(args.namespace)

    if not configmaps or not deployments:
        print("Failed to retrieve resources. Check access permissions or if resources exist in the namespace.")
        exit(1)

    mapping = map_configmaps_to_deployments(deployments, configmaps)

    if mapping:
        print("Relevant annotations found! Saving for later application...")
        save_mapping(mapping)
    else:
        print("No relevant annotations detected. Nothing to apply.")

    print(f"Fetch and validation complete! Results stored in {OUTPUT_FILE}")