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

def dry_run_all(mapping, namespace):
    """Preview all missing annotations without applying them."""
    changes = {}

    print("\n[DRY RUN] The following annotations will be added:\n")
    
    for deployment_name, data in mapping.items():
        existing_annotations = get_existing_annotations(deployment_name, namespace)
        missing_annotations = {k: v for k, v in data["annotations"].items() if k not in existing_annotations}

        if missing_annotations:
            print(f"Deployment: {deployment_name} (namespace: {namespace})")
            for key, value in missing_annotations.items():
                print(f"  - {key}: {value}")
            print()
            changes[deployment_name] = missing_annotations

    if not changes:
        print("No changes needed. All required annotations are already present.")
        return None
    
    return changes

def apply_annotations(changes, namespace):
    """Apply all annotations after user confirmation."""
    for deployment_name, annotations in changes.items():
        annotation_args = " ".join([f'{key}="{value}"' for key, value in annotations.items()])
        cmd = f'kubectl annotate deployment {deployment_name} -n {namespace} {annotation_args}'

        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"Successfully added missing annotations to {deployment_name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to annotate {deployment_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply missing annotations to Kubernetes deployments with full dry-run preview.")
    parser.add_argument("-n", "--namespace", required=True, help="Kubernetes namespace to update deployments in")

    args = parser.parse_args()
    namespace = args.namespace

    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run `get_annotations.py` first.")
        exit(1)

    print("\nLoading saved annotations...")
    with open(INPUT_FILE, "r") as f:
        mapping = json.load(f)

    # Dry-run: Show all changes first
    changes = dry_run_all(mapping, namespace)

    if not changes:
        print("\nNo changes applied. Exiting.")
        exit(0)

    # Ask for confirmation before applying changes
    confirm = input("\nApply these changes? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("\nNo changes applied. Exiting.")
        exit(0)

    # Apply all changes
    apply_annotations(changes, namespace)

    print("\nAnnotation update process complete.")