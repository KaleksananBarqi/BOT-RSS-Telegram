import feedparser
import json
import os
import ssl
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone


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
            json.dump(self.history, f, indent=4)

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

    def filter_entries_by_age(self, entries, max_hours):
        """Memfilter berita berdasarkan umur (jam)."""
        if not max_hours:
            return entries
            
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_hours)
        valid_entries = []
        
        for entry in entries:
            # published_parsed is a struct_time in UTC (from feedparser)
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    # Convert struct_time to aware datetime (UTC)
                    entry_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if entry_time >= cutoff_time:
                        valid_entries.append(entry)
                except Exception:
                    # Jika gagal parsing tanggal, anggap valid agar tidak hilang
                    valid_entries.append(entry)
            else:
                # Jika tidak ada tanggal, anggap valid
                valid_entries.append(entry)
                
        return valid_entries

    def fetch_feed(self, url):
        """Mengambil dan memparsing data RSS dengan requests + headers."""
        print(f"Fetching feed from: {url}")
        
        # Headers untuk meniru browser asli
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Encoding': 'gzip, deflate'
        }

        try:
            # Gunakan requests untuk mengambil konten raw
            import requests # Lazy import to avoid top-level dependency if not used elsewhere often
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
            elif response.status_code in [403, 429]:
                print(f"Warning: Access denied (HTTP {response.status_code}). Site might be blocking bots.")
                return []
            else:
                print(f"Warning: Failed to fetch feed (HTTP {response.status_code})")
                return []

        except Exception as e:
            print(f"Error fetching feed via requests: {e}")
            # Fallback ke feedparser standard jika requests gagal total
            feed = feedparser.parse(url)

        if feed.bozo:
             print(f"Warning: Error parsing feed: {feed.bozo_exception}")

        return feed.entries

    def parse_entry(self, entry):
        """Membersihkan dan memformat data entry."""
        image_url = self.extract_image(entry)
        
        raw_summary = entry.get('summary', '') or entry.get('description', '')
        soup = BeautifulSoup(raw_summary, 'html.parser')
        clean_summary = soup.get_text()[:300] + "..." if len(soup.get_text()) > 300 else soup.get_text()

        return {
            'id': entry.get('id', entry.get('link')),
            'title': entry.get('title', 'No Title'),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'summary': clean_summary,
            'image_url': image_url
        }
