import asyncio
import time
import feedparser
import os

# Simulasi konten XML besar (direplikasi agar cukup berat)
xml_item = """
<item>
    <title>Berita Penting ke-{i}</title>
    <link>http://example.com/{i}</link>
    <description>Ini adalah deskripsi panjang untuk item ke-{i}. </description>
    <pubDate>Fri, 20 Feb 2026 00:00:00 +0000</pubDate>
</item>
"""
dummy_xml = f"<rss version='2.0'><channel><title>Test Feed</title>{''.join(xml_item.format(i=i) for i in range(5000))}</channel></rss>"

async def background_task():
    """Tugas ringan yang seharusnya berjalan mulus setiap 10ms."""
    delays = []
    for _ in range(50):
        start = time.perf_counter()
        await asyncio.sleep(0.01)
        end = time.perf_counter()
        delays.append(end - start - 0.01)
    return delays

async def run_parsing(use_executor=False):
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    if use_executor:
        await loop.run_in_executor(None, feedparser.parse, dummy_xml)
    else:
        feedparser.parse(dummy_xml)
    end = time.perf_counter()
    return end - start

async def main():
    print(f"--- Benchmark: Event Loop Blocking Test ---")
    
    # Baseline: Synchronous parsing
    print("\nRunning Baseline (Synchronous Parsing)...")
    bg_task = asyncio.create_task(background_task())
    parse_time = await run_parsing(use_executor=False)
    delays = await bg_task
    
    max_delay = max(delays) * 1000
    avg_delay = (sum(delays) / len(delays)) * 1000
    
    print(f"XML Parse Time: {parse_time:.4f}s")
    print(f"Max Event Loop Delay (Jitter): {max_delay:.2f}ms")
    print(f"Avg Event Loop Delay: {avg_delay:.2f}ms")

    # Optimasi: run_in_executor
    print("\nRunning Optimized (run_in_executor)...")
    bg_task = asyncio.create_task(background_task())
    parse_time = await run_parsing(use_executor=True)
    delays = await bg_task
    
    max_delay_opt = max(delays) * 1000
    avg_delay_opt = (sum(delays) / len(delays)) * 1000
    
    print(f"XML Parse Time: {parse_time:.4f}s")
    print(f"Max Event Loop Delay (Jitter): {max_delay_opt:.2f}ms")
    print(f"Avg Event Loop Delay: {avg_delay_opt:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())
