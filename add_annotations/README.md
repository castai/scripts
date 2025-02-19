# Kubernetes Annotation Restoration and Backup Tools

## **Scripts Overview**
This repository consists of:
1. **Backup and Rollback Scripts** - Ensuring deployments are safely backed up and recoverable.
2. **Annotation Management Scripts** - Ensuring critical metadata is correctly applied to deployments.

## **Backup and Rollback Scripts**

### **Backup All Deployments (`backup.sh`)**
- Saves all Deployments as YAML files in the `backup/` directory.
- **Cleans metadata** (`status`, `resourceVersion`, `uid`, etc.) **before saving** to avoid conflicts during restoration.

### **Rollback All Deployments (`rollback.sh`)**
- Ensures a **clean rollback** without modification issues.

### **Usage**
```bash
./backup.sh <namespace>
```

```bash
./rollback.sh <namespace>
```
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
   ```

2. **Add Missing Annotations:**  
   Run the second script to get :
   ```bash
   ./apply-annotations.py -n <namespace>
   ```