# 📰 Telegram RSS News Bot

**Bot Telegram Canggih untuk Agregasi Berita Otomatis**

Bot berbasis Python yang kuat, cepat, dan efisien untuk memantau feed RSS, memfilter berita terbaru, dan mengirimkannya ke komunitas Telegram Anda dengan format yang rapi dan menarik.

---

## ✨ Fitur Unggulan

Bot ini telah diperbarui dengan teknologi terbaru untuk memastikan kinerja maksimal:

*   🚀 **High-Performance Async I/O**: Dibangun menggunakan `aiohttp` untuk melakukan *fetching* data dari banyak sumber RSS secara asinkron (paralel), membuat bot sangat responsif dan cepat.
*   💾 **Robust SQLite Persistence**: Menggunakan database **SQLite** (`data/bot.db`) untuk menyimpan riwayat berita. Ini memastikan data tetap aman, mencegah duplikasi berita, dan mampu menangani ribuan *entry* tanpa masalah performa.
*   🐳 **Docker Ready**: Siap dijalankan di mana saja dengan dukungan penuh **Docker** dan **Docker Compose**. Deployment menjadi semudah satu perintah CLI.
*   ⏰ **Absolute Hourly Scheduling**: Sistem penjadwalan presisi yang memastikan bot berjalan pada jam-jam yang tepat (misal: 14:00, 15:00) sesuai interval yang Anda tentukan.
*   🧹 **Smart Age Filtering**: Secara cerdas menyaring berita yang sudah "basi" (berdasarkan konfigurasi `MAX_NEWS_AGE_HOURS`) saat bot pertama kali dinyalakan.
*   🖼️ **Rich Media Support**: Mengirimkan berita lengkap dengan **Judul Tebal**, Ringkasan, dan **Gambar** (jika tersedia).
*   ⚡ **Instant View & Topic Aware**: Mendukung fitur Instant View Telegram dan pengiriman pesan ke **Topik** spesifik dalam Supergroup.
*   🛡️ **Anti-Blocking**: Header HTTP kustom untuk meniru perilaku browser asli, meminimalkan risiko blokir dari penyedia feed.

---

## 📂 Struktur Proyek

```bash
BOT RSS TELEGRAM/
├── config/
│   └── config.py        # Pusat konfigurasi (URL RSS, Interval, Token)
├── data/
│   ├── bot.db           # Database SQLite (Menyimpan riwayat berita terkirim)
│   └── history.json     # (Legacy) File migrasi riwayat lama
├── src/
│   ├── main.py          # Logika utama orkestrasi bot
│   ├── rss_service.py   # Service untuk fetching, parsing, dan filtering RSS
│   └── bot_service.py   # Service untuk interaksi dengan API Telegram
├── Dockerfile           # Konfigurasi image Docker
├── docker-compose.yml   # Konfigurasi orkestrasi container
├── .env                 # (Anda buat sendiri) File kredensial rahasia
└── requirements.txt     # Daftar dependensi Python
```

---

## 🛠️ Prasyarat

Sebelum memulai, pastikan Anda memiliki:

1.  **Bot Token**: Chat dengan [@BotFather](https://t.me/BotFather) untuk membuat bot baru.
2.  **Group/Channel ID**: ID tempat bot akan mengirim pesan.
3.  **Python 3.8+** (untuk instalasi manual) ATAU **Docker** (untuk instalasi container).

---

## 🚀 Panduan Instalasi & Penggunaan

### Opsi 1: Menggunakan Docker (Sangat Disarankan) 🐳

Cara termudah dan terbersih untuk menjalankan bot.

1.  **Clone Repository**
    ```bash
    git clone <repository-url>
    cd "BOT RSS TELEGRAM"
    ```

2.  **Konfigurasi Environment**
    Buat file `.env` dari contoh di bawah ini:
    ```bash
    # Buat file .env
    echo "BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" >> .env
    echo "GROUP_ID=-1001234567890" >> .env
    echo "TOPIC_ID=" >> .env # Kosongkan jika tidak menggunakan topik
    ```

3.  **Jalankan Bot**
    ```bash
    docker-compose up -d
    ```
    Bot akan berjalan di background dan otomatis restart jika server reboot.

4.  **Lihat Logs**
    ```bash
    docker-compose logs -f
    ```

### Opsi 2: Instalasi Manual (Python) 🐍

1.  **Clone Repository**
    ```bash
    git clone <repository-url>
    cd "BOT RSS TELEGRAM"
    ```

2.  **Buat Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # venv\Scripts\activate   # Windows
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Environment**
    Buat file `.env` di root folder:
    ```ini
    BOT_TOKEN=token_bot_anda
    GROUP_ID=-100xxxxxxxx
    TOPIC_ID=  # Isi angka ID topik jika perlu, atau biarkan kosong
    ```

5.  **Jalankan Bot**
    ```bash
    python run.py
    ```

---

## ⚙️ Konfigurasi Lanjutan

Anda dapat mengubah perilaku bot melalui file `config/config.py`:

| Variabel | Deskripsi | Default |
| :--- | :--- | :--- |
| `RSS_URLS` | Daftar URL feed RSS yang akan dipantau. | `[...]` |
| `CHECK_INTERVAL_HOURS` | Seberapa sering bot mengecek berita (dalam jam). | `1` |
| `DELAY_BETWEEN_POSTS` | Jeda waktu (detik) antar pesan agar tidak terkena rate limit. | `5` |
| `MAX_NEWS_AGE_HOURS` | Batas umur berita. Berita lebih tua dari ini akan diabaikan. | `24` |
| `IV_RHASH` | Hash template Instant View (opsional). | `None` |

---

## 🤝 Kontribusi

Ingin menambahkan fitur baru?
1.  Fork repository ini.
2.  Buat branch fitur Anda (`git checkout -b fitur-keren`).
3.  Commit perubahan Anda (`git commit -m 'Menambahkan fitur keren'`).
4.  Push ke branch (`git push origin fitur-keren`).
5.  Buat Pull Request.

Happy Coding! 🚀
