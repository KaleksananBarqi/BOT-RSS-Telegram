import os
import sys
from dotenv import load_dotenv

# ==========================================
# USER CONFIGURATION (EDIT BAGIAN INI)
# ==========================================

# Daftar URL Feed RSS Berita
# Masukkan dalam format list (kurung siku) dipisahkan koma
RSS_URLS = [
    'https://www.antaranews.com/rss/terkini.xml',
    # 'https://www.cnnindonesia.com/nasional/rss',
]

# Jeda waktu antar pesan (detik)
# Agar tidak terkena flood limit Telegram
DELAY_BETWEEN_POSTS = 5

# Interval pengecekan feed RSS (detik)
# Contoh: 300 berarti setiap 5 menit bot akan mengecek berita baru
CHECK_INTERVAL = 300

# Instant View RHASH (Opsional)
# Dapatkan dari https://instantview.telegram.org/
# Kosongkan jika tidak punya tempalte khusus (Bot akan coba native preview atau hidden link)
IV_RHASH = ''

# ==========================================
# SYSTEM CONFIGURATION (JANGAN DIEDIT)
# ==========================================

# Load environment variables from .env file
load_dotenv()

def get_env_variable(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        print(f"Error: Variable '{name}' is missing in .env file.")
        sys.exit(1)
    return value

# Bot Credentials (dari .env)
# Pastikan file .env sudah diisi dengan token dan ID grup yang benar
BOT_TOKEN = get_env_variable("BOT_TOKEN", required=True)
GROUP_ID = get_env_variable("GROUP_ID", required=True)
TOPIC_ID = get_env_variable("TOPIC_ID") # Optional

print("Configuration loaded successfully.")
