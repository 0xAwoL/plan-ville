import json
import os
from datetime import datetime
from typing import List, Dict, Any

class CheckpointManager:
    def __init__(self, checkpoint_file: str = "checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.current_batch = 0
        self.processed_points = set()
        self.load_checkpoint()
    
    def load_checkpoint(self):
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self.current_batch = data.get('current_batch', 0)
                    self.processed_points = set(tuple(point) for point in data.get('processed_points', []))
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
                self.current_batch = 0
                self.processed_points = set()
    
    def save_checkpoint(self, batch_index: int, processed_points: List[Dict[str, float]]):
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump({
                    'current_batch': batch_index,
                    'processed_points': [list(point.values()) for point in processed_points],
                    'timestamp': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
    
    def is_point_processed(self, point: Dict[str, float]) -> bool:
        return tuple(point.values()) in self.processed_points
    
    def mark_point_processed(self, point: Dict[str, float]):
        self.processed_points.add(tuple(point.values())) 