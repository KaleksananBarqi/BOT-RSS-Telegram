import time
import os
import shutil
from src.rss_service import RSSService

def run_benchmark(label="Current Implementation", count=1000):
    # Setup clean db
    if os.path.exists("data/bot_bench.db"):
        os.remove("data/bot_bench.db")
    
    service = RSSService(db_file="data/bot_bench.db", json_history_file="data/bot_bench_history.json")
    
    start_time = time.time()
    for i in range(count):
        entry_id = f"entry_bench_{i}"
        # Simulate check
        is_new = service.is_new(entry_id)
        # Simulate mark as read
        if is_new:
            service.mark_as_read(entry_id)
            
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"--- Benchmark: {label} ---")
    print(f"Items: {count}")
    print(f"Total Time: {duration:.4f} seconds")
    print(f"Avg Time per Item: {(duration/count)*1000:.2f} ms")
    print("-" * 30)

if __name__ == "__main__":
    run_benchmark(count=500)
