# Kubernetes Annotation Restoration Tools

This repository contains two Python scripts that work together to detect and restore missing annotations on Kubernetes Deployments using data from referenced ConfigMaps.

## Scripts Overview

- **get_annotations.py**  
  Fetches all ConfigMaps and Deployments in a given namespace, then maps which deployments are missing annotations defined in their referenced ConfigMap (via `envFrom.configMapRef`). The resulting mapping is saved as `annotations.json`.

- **apply_annotations.py**  
  Reads the generated `annotations.json` and applies the missing annotations to the corresponding Deployments using `kubectl annotate` (with double quotes for annotation values).

## Prerequisites

- Python 3.x  
- `kubectl` installed and configured for your cluster  
- Access to the target namespace (default: `test-namespace`)

## Usage

1. **Fetch and Map Missing Annotations:**  
   Run the first script to get :
   ```bash
   ./get_annotations.py


2. **Add Missing Annotations:**  
   Run the first script to get :
   ```bash
   ./apply_annotations.py