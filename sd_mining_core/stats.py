import os
import json
import time
import asyncio
import aiohttp
from pathlib import Path

class SDMinerStats:
    def __init__(self, stats_file="stats/sd-miner-stats.json", api_url="http://45.146.242.71:5678/submit-stats"):
        self.stats_file = stats_file
        self.stats_dir = os.path.dirname(stats_file)
        self.api_url = api_url
        self.auth_key = "Lra1jXb1W!0~"
        self._ensure_stats_dir_exists()
        
    def _ensure_stats_dir_exists(self):
        """Ensure the statistics directory exists."""
        Path(self.stats_dir).mkdir(parents=True, exist_ok=True)
    
    async def load_stats(self):
        """Load statistics from the JSON file."""
        try:
            if os.path.exists(self.stats_file):
                async with asyncio.Lock():
                    with open(self.stats_file, 'r') as f:
                        return json.load(f)
            # Initialize with empty stats and current timestamp
            return [{"model_stats": {}, "last_pushed": time.time()}]
        except Exception as e:
            print(f"Error loading stats: {e}")
            return [{"model_stats": {}, "last_pushed": time.time()}]
    
    async def save_stats(self, stats):
        """Save statistics to the JSON file."""
        try:
            async with asyncio.Lock():
                with open(self.stats_file, 'w') as f:
                    json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    async def reset_stats(self):
        """Reset the stats after successful push."""
        empty_stats = [{"model_stats": {}, "last_pushed": time.time()}]
        await self.save_stats(empty_stats)
        return empty_stats
    
    async def update_model_stats(self, model_id, successful=True):
        """
        Update statistics for a specific model.
        
        Args:
            model_id (str): The ID of the model to update
            successful (bool): Whether the job was successful
        """
        stats = await self.load_stats()
        
        # Get the first entry in the stats array
        stats_entry = stats[0]
        model_stats = stats_entry["model_stats"]
        
        # Update or create model statistics
        if model_id not in model_stats:
            model_stats[model_id] = {"total_jobs": 0, "successful_jobs": 0}
        
        model_stats[model_id]["total_jobs"] += 1
        if successful:
            model_stats[model_id]["successful_jobs"] += 1
        
        # Check if it's time to push stats to API (if last push was at least 1 minute ago)
        current_time = time.time()
        last_pushed_time = stats_entry.get("last_pushed", 0)
        time_since_last_push = current_time - last_pushed_time
        
        should_push = time_since_last_push >= 60  # 60 seconds = 1 minute
        
        # Save the updated stats first
        await self.save_stats(stats)
        
        if should_push and model_stats:  # Only push if there's actual data
            stats_entry["last_pushed"] = current_time
            push_successful = await self.push_to_api(stats)
            
            if push_successful:
                # Reset stats after successful push
                stats = await self.reset_stats()
        
        return stats
    
    async def push_to_api(self, stats):
        """Push updated stats to the API."""
        if not self.auth_key:
            print("Error: AUTH_KEY is missing. Cannot push stats.")
            return False

        headers = {"Authorization": f"Bearer {self.auth_key}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=stats, headers=headers) as response:
                    if response.status == 200:
                        print("Stats successfully pushed to API.")
                        return True
                    else:
                        print(f"Failed to push stats. Status: {response.status}, Response: {await response.text()}")
                        return False
            except Exception as e:
                print(f"Error pushing stats to API: {e}")
                return False