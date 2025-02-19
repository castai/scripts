import subprocess
import json
import os
import argparse

INPUT_FILE = "annotations.json"

def run_command(cmd):
    """Executes a shell command and returns output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        result.check_returncode()
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing {cmd}: {e}")
        return None

def get_existing_annotations(deployment_name, namespace):
    """Fetch current annotations for a given deployment."""
    cmd = f'kubectl get deployment {deployment_name} -n {namespace} -o json'
    output = run_command(cmd)
    
    if output:
        try:
            deployment = json.loads(output)
            return deployment["metadata"].get("annotations", {})
        except json.JSONDecodeError:
            print(f"Error parsing JSON for deployment {deployment_name}.")
            return {}
    return {}

def apply_annotations(deployment_name, annotations, namespace):
    """Apply missing annotations using kubectl annotate."""
    existing_annotations = get_existing_annotations(deployment_name, namespace)
    missing_annotations = {k: v for k, v in annotations.items() if k not in existing_annotations}

    if not missing_annotations:
        print(f"Skipping {deployment_name}: All annotations already present.")
        return

    for key, value in missing_annotations.items():
        print(f"Annotating {deployment_name}: {key} -> (Value Hidden for Length)")

        cmd = f'kubectl annotate deployment {deployment_name} -n {namespace} {key}="{value}" --overwrite'
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"Successfully added annotation {key} to {deployment_name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to annotate {deployment_name} with {key}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply missing annotations to Kubernetes deployments.")
    parser.add_argument("-n", "--namespace", required=True, help="Kubernetes namespace to update deployments in")

    args = parser.parse_args()
    namespace = args.namespace

    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run `get_annotations.py` first.")
        exit(1)

    print("Loading saved annotations...")
    with open(INPUT_FILE, "r") as f:
        mapping = json.load(f)

    for deployment_name, data in mapping.items():
        print(f"Processing {deployment_name} in namespace {namespace}...")
        apply_annotations(deployment_name, data["annotations"], namespace)

    print("Annotation restoration complete!")