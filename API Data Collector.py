import os
import time
import requests
import pandas as pd
from pathlib import Path

def log_execution_time(message):
    """Log execution time to a file."""
    from datetime import datetime
    log_file = r"./collector_execution_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - {message}\n")

class OSRSDataCollector:
    mappings = None

    def __init__(self):
        """Initialize the OSRS Grand Exchange data collector."""
        self.base_url = "https://prices.runescape.wiki/api/v1/osrs"
        self.headers = {
            "User-Agent": "OSRS GE Data Collector - Personal Project - isthisisthisyes@gmail.com"
        }
        
        self.output_5m = r"./historical_5m_data"
        self.output_1h = r"./historical_1h_data"
        # Create directories if they don't exist
        os.makedirs(self.output_5m, exist_ok=True)
        os.makedirs(self.output_1h, exist_ok=True)
    
    def load_items(self, file_path):
        """Load item names from the provided text file."""
        items = []
        with open(file_path, 'r') as f:
            for line in f:
                if ':' in line:
                    item_name = line.split(':', 1)[0].strip()
                    items.append(item_name)
        return items
    
    def get_all_item_mappings(self):
        if(self.mappings == None):
            print("Fetching item ID mappings from the Wiki API")
            url = f"{self.base_url}/mapping"

            time.sleep(1)
            response = requests.get(url, headers=self.headers)
            time.sleep(1)
            
            if response.status_code != 200:
                print(f"Error fetching item mappings: {response.status_code}")
                return {}
            
            self.mappings = response.json()
        return {item['name'].lower(): item['id'] for item in self.mappings}
    
    def fetch_timeseries(self, item_id, timestep):
        """Fetch timeseries data for an item."""
        url = f"{self.base_url}/timeseries"
        params = {
            "id": item_id,
            "timestep": timestep
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code != 200:
                print(f"Error fetching {timestep} data for item ID {item_id}: {response.status_code}")
                return None
            
            data = response.json()
            return data
        except Exception as e:
            print(f"Exception when fetching {timestep} data for item ID {item_id}: {e}")
            return None
    
    def process_and_save_data(self, item_name, item_id, data, timestep):
        """Process and save data to CSV, handling duplicates."""
        if timestep == "5m":
            output_dir = self.output_5m
        else:
            output_dir = self.output_1h
        
        if 'data' not in data or not data['data']:
            print(f"No {timestep} data available for {item_name}")
            return
        
        df_new = pd.DataFrame(data['data'])
        
        df_new.rename(columns={
            't': 'timestamp',
            'p': 'price',
            'v': 'volume'
        }, inplace=True)
        
        df_new['timestamp'] = df_new['timestamp'].astype(int)
        
        df_new['datetime'] = pd.to_datetime(df_new['timestamp'], unit='s')
        df_new['item_name'] = item_name
        df_new['item_id'] = item_id
        
        safe_name = item_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        file_path = Path(f"{output_dir}/{safe_name}.csv")
        
        if file_path.exists() and os.path.getsize(file_path) > 0:
            try:
                df_existing = pd.read_csv(file_path, dtype={'timestamp': int})
                
                existing_timestamps = set(df_existing['timestamp'])
                new_timestamps = set(df_new['timestamp'])
                unique_new = new_timestamps - existing_timestamps
                
                if unique_new:
                    df_to_add = df_new[df_new['timestamp'].isin(unique_new)]
                    
                    df_combined = pd.concat([df_existing, df_to_add])
                    df_combined.sort_values('timestamp', inplace=True)
                    
                    df_combined.to_csv(file_path, index=False)
                    print(f"Updated {timestep} data for {item_name}: {len(df_to_add)} new, {len(df_combined)} total")
                else:
                    print(f"No new {timestep} data for {item_name}")
            except Exception as e:
                print(f"Error processing existing file for {item_name}: {e}")
                print(f"Creating new file instead")
                df_new.to_csv(file_path, index=False)
                print(f"Saved {timestep} data for {item_name}: {len(df_new)} points")
        else:
            df_new.to_csv(file_path, index=False)
            print(f"Saved {timestep} data for {item_name}: {len(df_new)} points")
    
    def collect_data(self, items_file):
        """Main method to collect data for all items."""
        items = self.load_items(items_file)
        print(f"Loaded {len(items)} items from {items_file}")
        
        print("Fetching item ID mappings...")
        id_map = self.get_all_item_mappings()
        print(f"Fetched mappings for {len(id_map)} items")
        
        for i, item_name in enumerate(items):
            print(f"Processing item {i+1}/{len(items)}: {item_name}")
            
            item_id = id_map.get(item_name.lower())
            if item_id is None:
                print(f"Item '{item_name}' not found in mappings, skipping")
                continue
            
            data_5m = self.fetch_timeseries(item_id, "5m")
            if data_5m:
                self.process_and_save_data(item_name, item_id, data_5m, "5m")
            
            time.sleep(2)
            
            data_1h = self.fetch_timeseries(item_id, "1h")
            if data_1h:
                self.process_and_save_data(item_name, item_id, data_1h, "1h")
            
            time.sleep(2)
        
        print("Data collection completed!")


def main():
    log_execution_time("Script execution STARTED")

    """Main entry point for the script."""
    items_file = r"./worthwhile_items.txt"
    
    collector = OSRSDataCollector()
    collector.collect_data(items_file)

    log_execution_time("Script execution COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()