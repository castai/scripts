import subprocess
import json
import os

NAMESPACE = "test-namespace"
INPUT_FILE = "annotations.json"

def run_command(cmd):
    """Executes a shell command and returns output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        result.check_returncode()
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing {cmd}: {e}")
        return None

def get_deployments():
    """Fetch all Deployments in the namespace."""
    cmd = f'kubectl get deployment -n {NAMESPACE} -o json'
    output = run_command(cmd)
    return json.loads(output) if output else None

def apply_annotations(deployment_name, missing_annotations):
    """Apply missing annotations using kubectl annotate."""
    for key, value in missing_annotations.items():
        print(f"🔄 Annotating {deployment_name}: {key} -> (Value Hidden for Length)")
        
        # Use double quotes for the annotation value
        cmd = f'kubectl annotate deployment {deployment_name} -n {NAMESPACE} {key}="{value}" --overwrite'
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ Successfully added annotation {key} to {deployment_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to annotate {deployment_name} with {key}: {e}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found. Run `get_annotations.py` first.")
        exit(1)

    print("🔍 Loading saved annotations...")
    with open(INPUT_FILE, "r") as f:
        mapping = json.load(f)

    deployments = get_deployments()
    existing_deployments = {d["metadata"]["name"] for d in deployments.get("items", [])}

    for deployment_name, data in mapping.items():
        if deployment_name not in existing_deployments:
            print(f"⚠️ Skipping {deployment_name}: Deployment no longer exists.")
            continue

        print(f"\n🔄 Applying annotations to {deployment_name}...")
        apply_annotations(deployment_name, data["missing_annotations"])

    print("\n🎯 Annotation restoration complete!")