# Kubernetes Annotation Restoration Tools

This repository contains two Python scripts designed to detect and restore missing annotations on Kubernetes Deployments by referencing ConfigMaps.

## Scripts Overview

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

## 🛠 Prerequisites

- **Python 3.x** installed
- **`kubectl`** installed and configured for your cluster
- Sufficient permissions to **view and modify** ConfigMaps and Deployments

## Usage

1. **Fetch and Map Missing Annotations:**  
   Run the first script to get :
   ```bash
   ./get-annotations.py -n <namespace>

2. **Add Missing Annotations:**  
   Run the second script to get :
   ```bash
   ./apply-annotations.py -n <namespace>