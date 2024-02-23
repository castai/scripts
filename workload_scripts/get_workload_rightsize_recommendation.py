#This script interacts with the CAST AI API to retrieve workload efficiency data for a specified cluster within a time range, updating a JSON file with workload information and recommendations for right-sizing. It processes each workload, updates the JSON file
import requests
import json
import time
import os


cluster_id = 'REPlACE_YOUR_CLUSTER_ID'
start_time = '2024-02-21T18:30:00.000Z'
end_time = '2024-02-29T18:30:00.000Z'
api_key = 'REPlACE_YOUR_API_KEY'
output_file_name = "give_file_name.json'



def create_workload_list_file(filename):
    if os.path.exists(filename):
        print(f"The file '{filename}' already exists, so using the existing file.")
    else:
        print(f"The file '{filename}' does not exist, creating a new file.")
        url = f'https://api.cast.ai/v1/cost-reports/clusters/{cluster_id}/workload-efficiency'
        params = {
            'startTime': start_time,
            'endTime': end_time,
            'stepSeconds': '86400',
            'filter.labelsOperator': 'OR',
            'sort.order': 'ASC'
        }
        headers = {
            'accept': 'application/json',
            'X-API-Key': api_key
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            items_data = [{'workloadName': item['workloadName'],
                           'workloadType': item['workloadType'],
                           'namespace': item['namespace'],
                           'rightsizingRetrievalDone': False} for item in data['items']]
            with open(output_file_name, 'w') as f:
                json.dump(items_data, f, indent=2)
        else:
            print(f"Request failed with status code {response.status_code}")

def update_item(item):
    if not item['rightsizingRetrievalDone']:
        url = f'https://api.cast.ai/v1/cost-reports/clusters/{cluster_id}/namespaces/{item["namespace"]}/{item["workloadType"]}/{item["workloadName"]}/efficiency'
        params = {
            'startTime': start_time,
            'endTime': end_time,
            'stepSeconds': 86400,
            'includeCurrent': True,
            'includeHistory': False
        }
        headers = {
            'accept': 'application/json',
            'X-API-Key': api_key
        }
        response = requests.get(url, params=params, headers=headers)
        item['rightsizingRetrievalDone'] = True
        item['response'] = response.json()
        with open(output_file_name, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"Updated item: {item['workloadName']} - {item['namespace']}")



create_workload_list_file(output_file_name)

with open(output_file_name, 'r') as file:
    data = json.load(file)

count = 0 
for item in data:
    update_item(item)
    count += 1
    if count > 100:
        time.sleep(10)
        print("Slept for 10 seconds after processing 100 workloads.")
        count = 0

print("Done.")
