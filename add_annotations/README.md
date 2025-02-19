# Kubernetes Annotation Restoration and Backup Tools

This repository provides tools for:
- **Restoring missing annotations** on Kubernetes Deployments
- **Backing up and rolling back Deployments** to a stable state



---

## **Scripts Overview**

### **Annotation Management Scripts**
These scripts are used to **fetch, map, and restore missing annotations** from ConfigMaps to Kubernetes Deployments.

- **`get-annotations.py`**  
  - Fetches all ConfigMaps and Deployments within a specified namespace.
  - Extracts specific annotations from ConfigMaps:
    - `com.fico.dmp/component-descriptor`
    - `com.fico.dmp/engine-descriptor`
    - `com.fico.dmp/idle-config-annotation`
  - Maps these annotations to Deployments if they reference a ConfigMap (`envFrom.configMapRef`).
  - Saves the results to `annotations_output.json`.

- **`apply-annotations.py`**  
  - Reads `annotations_output.json`.
  - Applies missing annotations to the corresponding Deployments using `kubectl annotate`.
  - Ensures existing annotations are not re-applied unnecessarily.
  - Supports a **dry-run mode** that previews changes before applying.
  - Tracks **deployment revision history** and forces a new revision if necessary.

---
## Usage

1. **Fetch and Map Missing Annotations:**  
   Run the first script to get :
   ```bash
   ./get-annotations.py -n <namespace>

2. **Add Missing Annotations:**  
   Run the second script to get :
   ```bash
   ./apply-annotations.py -n <namespace>