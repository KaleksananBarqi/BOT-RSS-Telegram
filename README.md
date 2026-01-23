# Telegram RSS News Bot

Bot Telegram canggih berbasis Python yang secara otomatis mengambil berita dari berbagai feed RSS, memfilternya secara cerdas, dan mengirimkannya ke Grup atau Topik Telegram dengan format yang kaya.

## Fitur Utama

- **Multi-Source RSS Support**: Memantau dan mengambil berita dari banyak URL RSS sekaligus.
- **Absolute Hourly Scheduling**: Bot beroperasi pada jadwal jam yang presisi (misalnya tepat pukul 14:00, 15:00) sesuai interval yang dikonfigurasi, memastikan keteraturan pengiriman.
- **Smart Age Filtering**: Secara otomatis menyaring berita yang terlalu lama (berdasarkan `MAX_NEWS_AGE_HOURS`) untuk mencegah spam berita lawas saat bot baru dinyalakan atau direstart.
- **Duplicate Prevention**: Menyimpan riwayat berita yang telah dikirim di `data/history.json` untuk memastikan tidak ada berita ganda.
- **Rich Media & Formatting**: Mengirim pesan dengan judul tebal, ringkasan, dan gambar, serta tautan *Read More*.
- **Instant View Support**: Mendukung fitur Instant View Telegram (melalui template `IV_RHASH`) untuk pengalaman membaca cepat.
- **Topic-Aware**: Dapat dikonfigurasi untuk mengirim berita ke topik spesifik dalam grup (supergroup) atau ke chat utama.
- **Resilient Fetching**: Dilengkapi dengan header HTTP menyerupai browser dan penanganan SSL kustom untuk menghindari pemblokiran oleh penyedia feed (seperti Cloudflare).

## Struktur Proyek

```bash
BOT RSS TELEGRAM/
├── config/
│   └── config.py        # Pusat konfigurasi (URL RSS, Interval, Token)
├── data/
│   └── history.json     # Penyimpanan lokal riwayat berita yang terkirim
├── src/
│   ├── bot_service.py   # Layanan interaksi dengan API Telegram
│   ├── rss_service.py   # Layanan fetching, parsing, dan filtering RSS
│   └── main.py          # Logika utama, loop penjadwalan, dan orkestrasi
├── .env                 # File environment untuk kredensial rahasia
├── run.py               # Script entry point untuk menjalankan bot
└── requirements.txt     # Daftar pustaka Python yang dibutuhkan
```

## Prasyarat

Sebelum memulai, pastikan Anda memiliki:

1.  **Python 3.8** atau lebih baru.
2.  **Akun Telegram** dan **Bot Token** (dapatkan dari [@BotFather](https://t.me/BotFather)).
3.  **ID Grup** tempat bot akan mengirim berita (dan **Topic ID** jika dikirim ke topik tertentu).

## Instalasi

1.  **Clone Repository**
    ```bash
    git clone <repository-url>
    cd "BOT RSS TELEGRAM"
    ```

2.  **Setting Virtual Environment** (Disarankan)
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Environment**
    Buat file `.env` di direktori root dan isi dengan kredensial Anda:
    ```ini
    BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    GROUP_ID=-1001234567890
    TOPIC_ID=123  # Opsional, hapus atau biarkan kosong jika tidak pakai topik
    ```

## Konfigurasi

Semua pengaturan perilaku bot dapat diubah di `config/config.py`:

- **RSS_URLS**: Daftar link feed RSS yang ingin dipantau.
- **CHECK_INTERVAL_HOURS**: Interval pengecekan dalam jam (misal: `1` untuk setiap jam).
- **DELAY_BETWEEN_POSTS**: Jeda waktu (detik) antar pengiriman pesan untuk menghindari rate limit.
- **MAX_NEWS_AGE_HOURS**: Batas usia berita dalam jam. Berita yang lebih tua dari ini akan diabaikan.
- **IV_RHASH**: Hash untuk template Instant View (jika Anda memilikinya).

## Menjalankan Bot

Jalankan bot menggunakan perintah:

```bash
python run.py
```

Bot akan mulai memantau feed, mengirimkan berita baru, dan kemudian tidur (sleep) hingga jadwal jam berikutnya tiba. Tekan `Ctrl+C` untuk menghentikan bot.

## Kontribusi

Kontribusi dipersilakan! Silakan buat *issue* atau *pull request* jika Anda menemukan bug atau ingin menambahkan fitur baru.
