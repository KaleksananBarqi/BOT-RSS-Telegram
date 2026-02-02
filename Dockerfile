# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Mencegah Python membuat file .pyc
# PYTHONUNBUFFERED: Memastikan output log langsung muncul (penting untuk Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies sistem jika diperlukan (opsional, tapi seringkali dibutuhkan)
# RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt dan install dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code ke dalam container
COPY . .

# Buat direktori data untuk volume
RUN mkdir -p data

# Jalankan aplikasi
CMD ["python", "run.py"]
