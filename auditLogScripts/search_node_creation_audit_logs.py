# Script: Search for node creation audit logs using a nodename.
# Please update the variables accordingly. After running it,
# you can find labels in the audit log, including "provisioner.cast.ai/node-id."
# You can search audit logs from console using this Castai node ID for other node-related operations.

import requests
import json

url_base = "https://api.cast.ai/v1/audit"  # Base URL for the API
api_key = "XXXXXX-Sample-api-key"  # Your API key
cluster_id = "46d8cc2a-000-000-82aa-b0ff8250ddcb"  # ID of the cluster you are querying
from_date = "2023-11-09T04:00:00.000Z" # Start date for the audit log search (in ISO 8601 format, e.g., "2023-11-09T04:00:00.000Z")
to_date = "2023-11-09T05:00:00.000Z" # End date for the audit log search (in ISO 8601 format, e.g., "2023-11-09T05:00:00.000Z")
node_name_to_search = "ip-10-16-36-50.ec2.internal"  # Name of the node you want to search for

#optional 
page_limit = 200  # Maximum number of results per page
operation = "nodeAdded"  # Type of operation you are interested in
headers = {"accept": "application/json", "X-API-Key": api_key}  # HTTP headers for the API request


all_items = []
current_cursor = None

while True:
    url = f"{url_base}?clusterId={cluster_id}&fromDate={from_date}&toDate={to_date}&page.limit={page_limit}"

    if current_cursor:
        url += f"&page.cursor={current_cursor}"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        items = response_data.get("items", [])
        all_items.extend(items)
        next_cursor = response_data.get("nextCursor")
        if not next_cursor:
            break
        current_cursor = next_cursor
    else:
        print(f"Request failed with status code {response.status_code}")
        print(response.text)
        break

matching_items = []

print("Searching for nodename: ", node_name_to_search)

for item in all_items:
    item_str = json.dumps(item)
    if node_name_to_search in item_str:
        matching_items.append(item)

for matching_item in matching_items:
    print(json.dumps(matching_item, indent=4))