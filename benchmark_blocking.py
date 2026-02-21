import asyncio
import time
import os
import sqlite3
import random
import sys
sys.path.append(os.getcwd())
from src.rss_service import RSSService

async def perform_work(service):
    print("Starting work (async bulk)...")
    ids = [f"item_{i}" for i in range(5000)]

    # Only bulk check
    await service.filter_new_identifiers(ids)
    print("Work finished.")

async def monitor_loop(stop_event, delays):
    while not stop_event.is_set():
        start = time.perf_counter()
        try:
            await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            break
        end = time.perf_counter()
        delay = (end - start - 0.01) * 1000
        if delay > 0:
            delays.append(delay)

async def main():
    db_file = "data/benchmark_blocking.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("CREATE TABLE history (id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    data = [(f"item_{i}",) for i in range(10000)]
    c.executemany("INSERT INTO history (id) VALUES (?)", data)
    conn.commit()
    conn.close()

    service = RSSService(db_file=db_file)
    await service.init()

    print("\n--- Benchmark: Event Loop Blocking (Async Bulk Only) ---")

    delays = []
    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_loop(stop_event, delays))

    await asyncio.sleep(0.1)

    start_time = time.perf_counter()
    await perform_work(service)
    end_time = time.perf_counter()

    stop_event.set()
    await monitor_task

    work_time = end_time - start_time
    max_delay = max(delays) if delays else 0

    print(f"Total Work Time: {work_time:.4f}s")
    print(f"Max Event Loop Delay (Jitter): {max_delay:.2f}ms")

    await service.close()
    if os.path.exists(db_file):
        os.remove(db_file)
    if os.path.exists(db_file + "-wal"):
        os.remove(db_file + "-wal")
    if os.path.exists(db_file + "-shm"):
        os.remove(db_file + "-shm")

if __name__ == "__main__":
    asyncio.run(main())
