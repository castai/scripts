import subprocess
import json

NAMESPACE = "test-namespace"

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
                        mapping[deployment_name] = {
                            "configmap": configmap_name,
                            "annotations": configmap_data
                        }
    
    return mapping

def restore_annotations(deployment_name, existing_annotations, new_annotations):
    """Patch the deployment with missing annotations."""
    merged_annotations = existing_annotations.copy()
    merged_annotations.update(new_annotations)  # Merge new annotations without overwriting existing ones

    # Convert annotations to JSON format
    annotation_patch = json.dumps({"metadata": {"annotations": merged_annotations}})

    # Apply patch
    cmd = f"kubectl patch deployment {deployment_name} -n {NAMESPACE} --type=merge -p '{annotation_patch}'"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Successfully updated annotations for {deployment_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update annotations for {deployment_name}: {e}")

if __name__ == "__main__":
    print("🔍 Fetching ConfigMaps and Deployments...")
    configmaps = get_configmaps()
    deployments = get_deployments()

    if not configmaps or not deployments:
        print("❌ Failed to retrieve resources. Check access permissions.")
        exit(1)

    mapping = map_configmaps_to_deployments(deployments, configmaps)

    for deployment_name, data in mapping.items():
        print(f"\n🔄 Checking Deployment: {deployment_name}")
        existing_annotations = deployments["items"][0]["metadata"].get("annotations", {})
        new_annotations = data["annotations"]

        if new_annotations and set(new_annotations.keys()) - set(existing_annotations.keys()):
            print(f"⚡ Updating annotations for {deployment_name}...")
            restore_annotations(deployment_name, existing_annotations, new_annotations)
        else:
            print(f"✅ No missing annotations for {deployment_name}")

    print("\n🎯 Annotation sync complete!")