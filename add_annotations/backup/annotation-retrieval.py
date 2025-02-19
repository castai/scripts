import json

# Input JSON file
input_file = "snapshot-retrieval/snapshot.json"
output_file = "kubectl_annotations.sh"

# Define annotation keys of interest
required_annotations = {
    "com.fico.dmp/component-descriptor",
    "com.fico.dmp/idle-config-annotation",
    "com.fico.dmp/engine-descriptor",
}

def extract_annotations(file_path):
    kubectl_commands = set()  # Store unique commands
    found_resources = {"deployment": 0, "statefulset": 0}
    processed_workloads = {}  # Store workload details for validation

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)  # Load JSON snapshot

        def scan_for_workloads(obj):
            """
            Recursively scans JSON structure for Kubernetes workloads.
            Extracts metadata, annotations, and ensures uniqueness.
            """
            if isinstance(obj, dict):
                if "metadata" in obj and "name" in obj["metadata"]:
                    kind = obj.get("kind", "").lower()  # Direct kind (e.g., Deployment, StatefulSet)
                    metadata = obj["metadata"]
                    annotations = metadata.get("annotations", {})
                    namespace = metadata.get("namespace", "default")
                    name = metadata["name"]

                    # Print detected workload before filtering
                    print(f"🔍 Processing workload: {kind if kind else 'UNKNOWN'} -> {name} (namespace: {namespace})")

                    # If no "kind", check "ownerReferences" for correct type
                    if not kind and "ownerReferences" in metadata:
                        for owner in metadata["ownerReferences"]:
                            if owner.get("kind", "").lower() in {"deployment", "statefulset"}:
                                kind = owner["kind"].lower()
                                print(f"Found StatefulSet via ownerReferences: {name}")
                                break  # Stop once we find the relevant owner kind

                    if kind in {"deployment", "statefulset"}:
                        found_resources[kind] += 1  # Count workloads

                        print(f"Detected {kind}: {name} in {namespace}")

                        # Print all annotations before filtering
                        print(f"🛠 Checking annotations for {kind}: {name} in {namespace}")
                        print(f"   Available Annotations: {annotations}")

                        # Extract relevant annotations if they exist
                        filtered_annotations = {
                            key: value for key, value in annotations.items() if key in required_annotations
                        }

                        if filtered_annotations:
                            print(f"✅ Found {kind} with Annotations: {name} in {namespace}")
                            print(f"   - Extracted Annotations: {filtered_annotations}")  # Debugging line
                            
                            annotation_str = " ".join(f'"{k}={v}"' for k, v in filtered_annotations.items())
                            kubectl_cmd = f'kubectl annotate {kind} {name} -n {namespace} {annotation_str} --overwrite'

                            # Deduplication: Ensure unique annotations per workload
                            if kubectl_cmd not in kubectl_commands:
                                kubectl_commands.add(kubectl_cmd)

                                # Store processed workloads for validation report
                                processed_workloads[f"{kind}/{name}/{namespace}"] = filtered_annotations

                # Recursively search nested dictionaries
                for key, value in obj.items():
                    scan_for_workloads(value)

            elif isinstance(obj, list):
                for item in obj:
                    scan_for_workloads(item)

        # Start scanning the entire JSON structure
        scan_for_workloads(data)

        # Force printing of final numbers even if no workloads found
        print("\n==== SUMMARY ====")
        print(f"🔍 Found Deployments: {found_resources['deployment']} (Expected: 4641)")
        print(f"🔍 Found StatefulSets: {found_resources['statefulset']} (Expected: 401)")
        print(f"✅ Unique Annotations to Apply: {len(kubectl_commands)}\n")

        # If no workloads found, print warning
        if found_resources["deployment"] < 4641 or found_resources["statefulset"] < 401:
            print("⚠️ WARNING: Some workloads may be missing. Check JSON structure.")

        # Validation report: Show extracted workloads
        print("\n==== VALIDATION REPORT ====")
        for workload, annotations in processed_workloads.items():
            print(f"📌 {workload}")
            for key, value in annotations.items():
                print(f"   - {key}: {value}")

    return kubectl_commands

# Extract and generate kubectl commands
commands = extract_annotations(input_file)

if not commands:
    print("\n⚠️ No matching annotations found!")

# Save commands to a shell script
with open(output_file, "w", encoding="utf-8") as f_out:
    f_out.write("#!/bin/bash\n\n")
    f_out.write("\n".join(commands))

print(f"\n📌 Generated kubectl annotation script: {output_file}\n")