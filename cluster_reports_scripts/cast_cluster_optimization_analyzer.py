"""
CAST.AI Cluster Report Script

This script interacts with the CAST.AI API to retrieve and analyze information about 
Kubernetes clusters managed by CAST.AI. It collects various metrics and configuration 
details, then generates both Excel and JSON reports.

Features:
- Retrieves cluster information from CAST.AI
- Collects data on:
  - Cluster status
  - Autoscaler configuration
  - Policy information (unschedulable pods, node deletion, evictor settings)
  - Rebalancing plans and schedules
  - Efficiency reports
  - Node template data
  - Workload autoscaler status
  - Workload resource types and counts
  - Problematic nodes and pods
- Generates an Excel report (clusters_info.xlsx)
- Generates a JSON report (clusters_info.json)

Usage:
1. Ensure all required packages are installed (requests, pandas, termcolor)
2. Set the CAST.AI access token in the script
3. Run the script: python cast_cluster_optimization_analyzer.py

Output:
- clusters_info.xlsx: Excel spreadsheet with detailed cluster information
- clusters_info.json: JSON file with structured cluster data

Note: Ensure you have the necessary permissions and a valid access token to use the CAST.AI API.
"""

# Import statements and rest of the script follows...

import requests
import pandas as pd
import datetime
import time
from termcolor import colored
import threading
import os
import json

access_token = "YOUR_CASTAI_API_KEY"

headers = {
    "X-API-Key": access_token,
    "Content-Type": "application/json"
}

def policy_info(cluster_id):
    url = f"https://console.cast.ai/api/v1/kubernetes/clusters/{cluster_id}/policies"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for 4xx or 5xx status codes
        policies = response.json()
        enabled = policies.get("enabled")
        unschedulable_pods = policies.get("unschedulablePods", {}).get("enabled")
        node_downscaler = policies.get("nodeDownscaler", {}).get("enabled")
        evictor = policies.get("nodeDownscaler", {}).get("evictor", {}).get("enabled")
        aggressiveMode = policies.get("nodeDownscaler", {}).get("evictor", {}).get("aggressiveMode")
        return enabled, unschedulable_pods, node_downscaler, evictor, aggressiveMode
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None, None, None, None, None

def rebalance_plan(cluster_id):
    url = f"https://console.cast.ai/api/v1/kubernetes/clusters/{cluster_id}/rebalancing-plans?limit=5&cursor=&includeOperations=false&includeConfigurations=true"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        plans = response.json().get("items", [])
        latest_plans = sorted(plans, key=lambda x: x['createdAt'], reverse=True)[:2]
        plan_data = []
        for plan in latest_plans:
            status = plan.get('status')
            diff = plan.get('configurations', {}).get('diff', {})
            saving_percentage = diff.get('savingsPercentage', 'N/A')
            plan_data.append({'Status': status, 'Saving Percentage': saving_percentage})
        return plan_data
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return []
def schedule(cluster_id):
    url = f"https://console.cast.ai/api/v1/rebalancing-schedules"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        schedule_data = response.json()
        schedule_names = []
        if not schedule_data['schedules']:
            message = "There is no schedule at org level"
        else:
            for schedule in schedule_data['schedules']:
                for job in schedule['jobs']:
                    if job['clusterId'] == cluster_id:
                        schedule_names.append(schedule['name'])
        return schedule_names
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None


def efficiency_report(cluster_id):
    current_date = datetime.datetime.now()
    end_date = current_date - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=5)
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    url = f"https://console.cast.ai/api/v1/cost-reports/clusters/{cluster_id}/efficiency?startTime={start_date_str}&endTime={end_date_str}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        efficiency_data = response.json()
        summary = efficiency_data.get('summary')
        current = efficiency_data.get('current')
        return summary, current
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None, None

def node_Template(cluster_id):
    url = f"https://console.cast.ai/api/v1/kubernetes/external-clusters/{cluster_id}/nodes"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        unique_template_values = set()

        # Initialize an empty dictionary to store node templates and their resources
        node_templates_resources = {}

        # Loop through the items in the JSON data and extract the node template values
        for item in data["items"]:
            template_value = item["labels"].get("scheduling.cast.ai/node-template", "not-managed-by-cast")
            if template_value not in unique_template_values:
                # If the node template value is unique, add it to the set and store its resources
                unique_template_values.add(template_value)
                resources = {
                    "cpuAllocatableMilli": item["resources"]["cpuAllocatableMilli"],
                    "memAllocatableMib": item["resources"]["memAllocatableMib"],
                    "cpuCapacityMilli": item["resources"]["cpuCapacityMilli"],
                    "memCapacityMib": item["resources"]["memCapacityMib"],
                    "cpuRequestsMilli": item["resources"]["cpuRequestsMilli"],
                    "memRequestsMib": item["resources"]["memRequestsMib"]
                }
                # Add the template value and its corresponding resources to the dictionary
                node_templates_resources[template_value] = resources

        # Initialize an empty dictionary to store aggregated resources for each node template
        aggregated_resources = {}

        # Loop through each node template value in the dictionary
        for template_value in unique_template_values:
            # Initialize variables to store aggregated resources
            total_cpu_allocatable = 0
            total_mem_allocatable = 0
            total_cpu_capacity = 0
            total_mem_capacity = 0
            total_cpu_requests = 0
            total_mem_requests = 0

            # Loop through each item in the JSON data
            for item in data["items"]:
                # Check if the item's node template matches the current template value
                if item["labels"].get("scheduling.cast.ai/node-template") == template_value:
                    # If the node template matches, aggregate the resources values
                    total_cpu_allocatable += item["resources"]["cpuAllocatableMilli"]
                    total_mem_allocatable += item["resources"]["memAllocatableMib"]
                    total_cpu_capacity += item["resources"]["cpuCapacityMilli"]
                    total_mem_capacity += item["resources"]["memCapacityMib"]
                    total_cpu_requests += item["resources"]["cpuRequestsMilli"]
                    total_mem_requests += item["resources"]["memRequestsMib"]
            
            if total_cpu_allocatable > 0:
                cpu_over_provisioned_percentage = ((total_cpu_allocatable - total_cpu_requests) / total_cpu_allocatable) * 100
            else:
                cpu_over_provisioned_percentage = 0
            if total_mem_allocatable > 0:
                mem_over_provisioned_percentage = ((total_mem_allocatable - total_mem_requests) / total_mem_allocatable) * 100
            else:
                mem_over_provisioned_percentage = 0

            # Store the aggregated resources for the current node template
            aggregated_resources[template_value] = {
                # "cpuAllocatableMilli": total_cpu_allocatable,
                # "memAllocatableMib": total_mem_allocatable,
                # "cpuCapacityMilli": total_cpu_capacity,
                # "memCapacityMib": total_mem_capacity,
                # "cpuRequestsMilli": total_cpu_requests,
                # "memRequestsMib": total_mem_requests,
                "CPU Over-Provisioned Percentage": cpu_over_provisioned_percentage,
                "Memory Over-Provisioned Percentage": mem_over_provisioned_percentage
            }

    # Print the dictionary of aggregated resources for each node template
        return aggregated_resources
    except requests.exceptions.RequestException as e:
        return "Failed to retrive"



def transform_response(response):
    transformed_response = {}

    for workload in response["workloads"]:
        if workload["status"]["migrationStatus"] != "ready":
            for node in workload["nodes"]:
                node_name = node["name"]
                if node_name not in transformed_response:
                    transformed_response["Nodes"] = {
                        "node_name": node_name,
                        "Migration_status": node["status"]["migrationStatus"],
                        "problamatic_workload": []
                    }
                
                problematic_workload = {
                    "workload": {
                        "name": workload["name"],
                        "issues": workload["issues"]
                    }
                }
                
                transformed_response["Nodes"]["problamatic_workload"].append(problematic_workload)

    # Converting the transformed response to the required JSON structure
    final_output = json.dumps(transformed_response, indent=4)
    return transformed_response

def workload(cluster_id):
    url = f"https://api.cast.ai/v1/kubernetes/clusters/{cluster_id}/workloads"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        workloads_data = response.json()
        resource_counts = {}
        for workload in workloads_data["workloads"]:
            resource_value = workload.get("resource")
            if resource_value:
                resource_counts[resource_value] = resource_counts.get(resource_value, 0) + 1
            
        return resource_counts , transform_response(workloads_data)
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None, None
    
def get_cluster():
    url = f"https://console.cast.ai/api/v1/kubernetes/external-clusters"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        clusters_data = response.json()
        cluster_results = []
        for cluster in clusters_data['items']:
            cluster_id = cluster['id']
            status = cluster['status']
            enabled, unschedulable_pods, node_downscaler, evictor, aggressiveMode = policy_info(cluster_id)
            rebalance_plans = rebalance_plan(cluster_id)
            summary, current = efficiency_report(cluster_id)
            schedule_rebalance = schedule(cluster_id)
            templates = node_Template(cluster_id)
            autoscaler = workload_autoscaler(cluster_id)
            workload_resources, Problematic_pods_nodes = workload(cluster_id)

            cluster_result = {
                "Cluster ID": cluster_id,
                "Cluster Status": status,
                "Autoscaler": enabled,
                "Unschedulable Pods Policy": unschedulable_pods,
                "Node Deletion Policy": node_downscaler,
                "Evictor": evictor,
                "Aggressive Mode": aggressiveMode,
                "Node-Template data": templates,
                "Workload Autoscaler": autoscaler,
                "Workload Resources type and count": workload_resources,
                "Problematic Nodes and Pods": Problematic_pods_nodes,
                "schedule Rebalancing": ", ".join(schedule_rebalance) if schedule_rebalance else "No schedules",
                "Rebalance Plans Status latest 2": rebalance_plans,
                "Efficiency Summary Last 6 days": summary,
                "Current Efficiency ": current

            }
            cluster_results.append(cluster_result)
        return cluster_results
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None
def workload_autoscaler(cluster_id):
    url = f"https://api.cast.ai/v1/workload-autoscaling/clusters/{cluster_id}/components/workload-autoscaler"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None

def blink():
    while True:
        print(colored('Processing...', 'yellow', attrs=['blink', 'bold']))
        time.sleep(1)

def main():
    file_name = "clusters_info.xlsx"
    if os.path.exists(file_name):
        os.remove(file_name)
        print("File '{}' removed successfully.".format(file_name))
    else:
        print("No file named '{}' found in the current directory.".format(file_name))
    file_name1 = "clusters_info.json"
    if os.path.exists(file_name1):
        os.remove(file_name1)
        print("File '{}' removed successfully.".format(file_name1))
    else:
        print("No file named '{}' found in the current directory.".format(file_name1))
    # Start blinking thread
    blink_thread = threading.Thread(target=blink)
    blink_thread.daemon = True
    blink_thread.start()


    clusters_info = get_cluster()
    if clusters_info is not None:
        df = pd.DataFrame(clusters_info)
        excel_file = "clusters_info.xlsx"
        df.to_excel(excel_file, index=False)
        print(f"An Excel file named '{excel_file}' has been generated.")

        # Convert Excel to JSON

        with open('clusters_info.json', 'w') as f:
            json.dump(clusters_info, f, indent=4)
        print(f"A JSON file named clusters_info.json has been generated.")
    else:
        print("Failed to retrieve cluster information.")

if __name__ == "__main__":
    main()
