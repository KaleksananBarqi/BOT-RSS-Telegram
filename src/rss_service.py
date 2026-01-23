import feedparser
import json
import os
import ssl
from bs4 import BeautifulSoup
from datetime import datetime
import time

# Workaround for SSL issues on some systems
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

class RSSService:
    def __init__(self, history_file='data/history.json'):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self):
        """Memuat riwayat ID berita yang sudah dikirim."""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_history(self):
        """Menyimpan riwayat ke file."""
        # Simpan hanya 1000 entri terakhir agar file tidak terlalu besar
        self.history = self.history[-1000:]
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)

    def is_new(self, entry_id):
        """Mengecek apakah berita ini baru."""
        return entry_id not in self.history

    def mark_as_read(self, entry_id):
        """Menandai berita sebagai sudah dibaca/dikirim."""
        if entry_id not in self.history:
            self.history.append(entry_id)
            self._save_history()

    def extract_image(self, entry):
        """Mencoba mengekstrak gambar dari entry RSS."""
        # 1. Cek Media Content (biasa di RSS modern)
        if 'media_content' in entry:
            for media in entry.media_content:
                if media.get('type', '').startswith('image') or media.get('medium') == 'image':
                    return media['url']
        
        # 2. Cek Media Thumbnail
        if 'media_thumbnail' in entry:
            return entry.media_thumbnail[0]['url']

        # 3. Cek Enclosures
        if 'enclosures' in entry:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    return enclosure['url']

        # 4. Parsing HTML Description/Summary
        content = entry.get('summary', '') or entry.get('description', '')
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            img_tag = soup.find('img')
            if img_tag and img_tag.get('src'):
                return img_tag['src']
        
        return None

    def fetch_feed(self, url):
        """Mengambil dan memparsing data RSS."""
        print(f"Fetching feed from: {url}")
        feed = feedparser.parse(url)
        
        if feed.bozo:
             print(f"Warning: Error parsing feed: {feed.bozo_exception}")

        entries = []
        # Proses dari yang terlama ke terbaru jika ingin urutan kronologis,
        # tapi biasanya RSS sudah urut. Kita ambil apa adanya, nanti main loop yang atur.
        # Biasanya RSS list item pertama adalah yang terbaru.
        # Kitabalik listnya agar kita mengirim dari yang "paling lama yang belum dikirim" ke "terbaru" 
        # saat iterasi di main loop, ATAU main loop handle reverse.
        # Mari kita return raw entries dulu.
        return feed.entries

    def parse_entry(self, entry):
        """Membersihkan dan memformat data entry."""
        image_url = self.extract_image(entry)
        
        # Bersihkan summary dari HTML tags untuk caption yang rapi (opsional)
        # Di sini kita biarkan raw atau simple cleanup
        raw_summary = entry.get('summary', '') or entry.get('description', '')
        soup = BeautifulSoup(raw_summary, 'html.parser')
        clean_summary = soup.get_text()[:300] + "..." if len(soup.get_text()) > 300 else soup.get_text()

        return {
            'id': entry.get('id', entry.get('link')), # Fallback ID ke link jika ID tidak ada
            'title': entry.get('title', 'No Title'),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'summary': clean_summary,
            'image_url': image_url
        }
