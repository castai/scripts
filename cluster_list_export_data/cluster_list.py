"""
CAST.AI Cluster Report Script

This script interacts with the CAST.AI API to retrieve and analyze information about 
Kubernetes clusters managed by CAST.AI. It collects various metrics and configuration 
details, then generates both Excel and JSON reports.

Features:
- Retrieves cluster information from CAST.AI
- Collects data on:
  - Cluster name
  - Cloud provider
  - If in connected (phase2)
  - Percentage of nodes managed by Cast
  - If unscheduled pods policy is enabled
  - If Evictor is enabled
  - If aggressive mode is enabled
  - If there is scheduled rebalancing
  - Workload autoscaler status
  - Workload Autoscaler status
  - Problematic nodes and pods
  - Workload autoscaler optimized percentage

Requirements:
1. API access token.
2. Ensure all required packages are installed (requests, pandas, termcolor)
3. Run the script: python3 cluster_list.py

Output:
- clusters_info.xlsx: Excel spreadsheet with detailed cluster information
- clusters_info.json: JSON file with structured cluster data

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

access_token = input("Enter API token: ")
# access_token = "2b41a6954edb5abdbf80df7ccb77f13a3802f4544825be18221ef25e7e108480"

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
    

def workloads_summary(cluster_id):
    url = f"https://console.cast.ai/api/v1/workload-autoscaling/clusters/{cluster_id}/workloads-summary"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 400:
            print("workloads_summary. Woop not installed. Received 400 Bad Request - returning 0")
            return 0, 0, 0

        response.raise_for_status()  # Raise exception for other 4xx or 5xx errors
        info = response.json()
        total_count = info.get("totalCount")
        optimized = info.get("optimizedCount")

        if total_count and optimized != 0:
            return total_count, optimized, optimized / total_count
        else:
            return 0, 0, 0

    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return 0, 0, 0
    

def is_managed(cluster_id):
    url = f"https://api.cast.ai/v1/cost-reports/organization/clusters/summary"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        stats = response.json()
        items = stats.get("items", [])
        first_item = items[0]

        for item in items:
            if item.get("clusterId") == cluster_id:
                od_total = item.get("nodeCountOnDemand", 0)
                od_cast = item.get("nodeCountOnDemandCastai", 0)
                spot_total = item.get("nodeCountSpot", 0)
                spot_cast = item.get("nodeCountSpotCastai", 0)

                od_total = int(od_total.replace("'", ""))  # Remove unexpected characters before conversion
                od_cast = int(od_cast.replace("'", ""))  
                spot_total = int(spot_total.replace("'", ""))
                spot_cast = int(spot_cast.replace("'", ""))

                calc_percentage = (od_cast + spot_cast) / (od_total + spot_total)
                return calc_percentage
        return 0

    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return 0


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
            cluster_name = cluster['name']
            cluster_id = cluster['id']
            is_connected = cluster['isPhase2']
            status = cluster['status']
            provider_type = cluster['providerType']
            percentage_managed_by_cast = is_managed(cluster_id)
            enabled, unschedulable_pods, node_downscaler, evictor, aggressiveMode = policy_info(cluster_id)
            total_count, optimized, optimized_percentage = workloads_summary(cluster_id)
            schedule_rebalance = schedule(cluster_id)
            autoscaler = workload_autoscaler(cluster_id)
            # rebalance_plans = rebalance_plan(cluster_id)
            # summary, current = efficiency_report(cluster_id)
            # templates = node_Template(cluster_id)
            # workload_resources, Problematic_pods_nodes = workload(cluster_id)

            cluster_result = {
                "Cluster ID": cluster_id,
                "Cluster Name": cluster_name,
                "Provider Type": provider_type,
                "Provider Type": provider_type,
                "Cluster Status": status,
                "Is Connected": is_connected,
                "Managed By Cast %": percentage_managed_by_cast,
                "Unschedulable Pods Policy": unschedulable_pods,
                "Evictor": evictor,
                "Aggressive Mode": aggressiveMode,
                "schedule Rebalancing": ", ".join(schedule_rebalance) if schedule_rebalance else "No schedules",
                "Workload Autoscaler": autoscaler,
                "Woop Optimized Percentage": optimized_percentage,
                # "Autoscaler": enabled,
                # "Node Deletion Policy": node_downscaler,
                # "Node-Template data": templates,
                # "Workload Resources type and count": workload_resources,
                # "Problematic Nodes and Pods": Problematic_pods_nodes,
                # "Rebalance Plans Status latest 2": rebalance_plans,
                # "Efficiency Summary Last 6 days": summary,
                # "Current Efficiency ": current

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
