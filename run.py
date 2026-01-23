import asyncio
import sys
import os

# Tambahkan direktori saat ini ke sys.path agar modul src dan config bisa ditemukan
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
