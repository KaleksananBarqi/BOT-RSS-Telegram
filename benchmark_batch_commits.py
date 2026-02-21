import time
import os
import shutil
import asyncio
from src.rss_service import RSSService

DB_FILE = "data/benchmark_db.db"

def setup_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    service = RSSService(db_file=DB_FILE, json_history_file="data/dummy.json")
    return service

async def benchmark_individual_commit(count=1000):
    service = setup_db()
    start_time = time.time()

    for i in range(count):
        entry_id = f"entry_individual_{i}"
        service.mark_as_read(entry_id, commit=True)

    end_time = time.time()
    await service.close()
    return end_time - start_time

async def benchmark_batched_commit(count=1000, batch_size=10):
    service = setup_db()
    start_time = time.time()

    for i in range(count):
        entry_id = f"entry_batch_{i}"
        # Commit only if batch size reached
        should_commit = ((i + 1) % batch_size == 0)
        service.mark_as_read(entry_id, commit=should_commit)

    # Final commit just in case
    service.commit()
    end_time = time.time()
    await service.close()
    return end_time - start_time

async def main():
    count = 1000
    print(f"Running benchmark with {count} items...")

    time_individual = await benchmark_individual_commit(count)
    print(f"Individual Commits: {time_individual:.4f}s")

    time_batch = await benchmark_batched_commit(count, batch_size=10)
    print(f"Batched Commits (Batch size=10): {time_batch:.4f}s")

    improvement = (time_individual - time_batch) / time_individual * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
