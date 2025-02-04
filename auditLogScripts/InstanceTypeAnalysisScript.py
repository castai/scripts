"""
CAST.ai Instance Type Analysis Script
===================================

This script analyzes instance type usage in CAST.ai-managed Kubernetes clusters over time.
It fetches audit data for a specific cluster and generates detailed reports of instance
type frequencies on a daily basis.

Functionality:
-------------
- Fetches data from CAST.ai API for a specified date range (33-66 days ago)
- Tracks instance types used for node additions in the cluster
- Generates an Excel report with:
    * Summary sheet showing all dates and instance types in a matrix format
    * Individual sheets for each date with detailed breakdowns
    * Total calculations for each sheet

Prerequisites:
-------------
- Python 3.x
- Required packages: requests, pandas, openpyxl
- Valid CAST.ai API key
- Cluster ID for the target cluster

Configuration:
-------------
1. Set your API_KEY (CAST.ai API key)
2. Modify the cluster ID in gke_clusters filter if needed 
  

Usage:
------
1. Install required packages:
   pip install requests pandas openpyxl

2. Run the script:
   python script_name.py

Output:
-------
- Creates 'dkb_instancechoice_by_date.xlsx' with multiple sheets
- Prints status messages during execution
- Shows total number of dates with data

Error Handling:
-------------
- Prints error messages for failed API requests
- Skips dates with no data
- Continues execution even if some requests fail


"""

import requests
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

API_KEY = 'Api_key'
BASE_URL = "https://api.cast.ai/v1/audit"
CLUSTERS_URL = "https://api.cast.ai/v1/kubernetes/external-clusters"

def get_range_50_to_80_days_ago():
    today = datetime.utcnow()
    start_date = today - timedelta(days=66)
    end_date = today - timedelta(days=33)
    date_ranges = []
    
    current_date = start_date
    while current_date < end_date:
        next_date = current_date + timedelta(days=1)
        date_ranges.append((current_date, next_date))
        current_date = next_date
        
    return date_ranges

def fetch_data_for_date_range(cluster_id, start_date, end_date):
    url = f"{BASE_URL}?clusterId={cluster_id}&fromDate={start_date.isoformat()}Z&toDate={end_date.isoformat()}Z&operation=nodeAdded"
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        print(f"Failed to fetch data for {start_date} to {end_date}: {response.status_code}")
        return []

def fetch_all_clusters():
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    response = requests.get(CLUSTERS_URL, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        print(f"Failed to fetch clusters: {response.status_code}")
        return []

def main():
    clusters = fetch_all_clusters()
    gke_clusters = [cluster for cluster in clusters if cluster.get("id") == "cluster_id"]
    
    # Dictionary to store date-wise instance type frequencies
    date_wise_frequency = {}
    
    date_ranges = get_range_50_to_80_days_ago()
    
    for cluster in gke_clusters:
        cluster_id = cluster.get("id")
        for start_date, end_date in date_ranges:
            # Create a key for this date range
            date_key = start_date.strftime('%Y-%m-%d')
            
            # Initialize frequency dictionary for this date
            instance_type_frequency = defaultdict(int)
            
            clusters_data = fetch_data_for_date_range(cluster_id, start_date, end_date)
            for cluster_data in clusters_data:
                instance_type = cluster_data.get("event", {}).get("node", {}).get("labels", {}).get("beta.kubernetes.io/instance-type")
                if instance_type:
                    instance_type_frequency[instance_type] += 1
            
            # Store the frequency data for this date
            if instance_type_frequency:  # Only store if there's data
                date_wise_frequency[date_key] = dict(instance_type_frequency)
    
    # Create separate sheets for each date and a summary sheet
    with pd.ExcelWriter('dkb_instancechoice_by_date.xlsx') as writer:
        # Create summary DataFrame
        all_instance_types = set()
        for freq_dict in date_wise_frequency.values():
            all_instance_types.update(freq_dict.keys())
        
        summary_data = []
        for date, freq_dict in date_wise_frequency.items():
            row_data = {'Date': date}
            row_data.update({instance_type: freq_dict.get(instance_type, 0) for instance_type in all_instance_types})
            summary_data.append(row_data)
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.sort_values('Date', inplace=True)
            
            # Add total row
            total_row = {'Date': 'Total'}
            for col in summary_df.columns:
                if col != 'Date':
                    total_row[col] = summary_df[col].sum()
            summary_df = pd.concat([summary_df, pd.DataFrame([total_row])], ignore_index=True)
            
            # Save summary sheet
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Create individual sheets for each date
            for date, freq_dict in date_wise_frequency.items():
                df = pd.DataFrame(list(freq_dict.items()), columns=['Instance Type', 'Frequency'])
                total_row = pd.DataFrame([['Total', df['Frequency'].sum()]], columns=['Instance Type', 'Frequency'])
                df = pd.concat([df, total_row], ignore_index=True)
                df.to_excel(writer, sheet_name=f'Date_{date}', index=False)
        
        print("Data has been written to instancechoice_by_date.xlsx")
        print(f"Number of dates with data: {len(date_wise_frequency)}")

if __name__ == "__main__":
    main()
