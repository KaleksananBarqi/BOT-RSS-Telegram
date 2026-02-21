import feedparser
import json
import os
import ssl
import urllib.request
import aiohttp
import asyncio
import logging
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from config.config import USER_AGENT


# Workaround for SSL issues on some systems
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

class RSSService:
    def __init__(self, db_file='data/bot.db', json_history_file='data/history.json'):
        self.db_file = db_file
        self.json_history_file = json_history_file
        self.session = None
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_db()
        self._migrate_json_to_db()

    def _init_db(self):
        """Inisialisasi database SQLite."""
        try:
            c = self.conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS history
                         (id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Optional: Index on created_at if we want to prune later
            c.execute('''CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at)''')
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _migrate_json_to_db(self):
        """Migrasi data dari JSON lama ke SQLite jika ada."""
        if os.path.exists(self.json_history_file):
            c = self.conn.cursor()

            # Cek apakah DB masih kosong (hanya migrasi jika kosong/baru)
            try:
                c.execute("SELECT count(*) FROM history")
                count = c.fetchone()[0]

                if count == 0:
                    logger.info("Migrating history from JSON to SQLite...")
                    try:
                        with open(self.json_history_file, 'r') as f:
                            history = json.load(f)
                            if isinstance(history, list):
                                for item in history:
                                    c.execute("INSERT OR IGNORE INTO history (id) VALUES (?)", (str(item),))
                                self.conn.commit()
                                logger.info(f"Migration complete. Imported {len(history)} items.")
                            else:
                                logger.warning("JSON history format invalid, skipping migration.")
                    except (json.JSONDecodeError, IOError) as e:
                        logger.error(f"Failed to read JSON history for migration: {e}")
            except Exception as e:
                logger.error(f"Migration check failed: {e}")

    def is_new(self, entry_id):
        """Mengecek apakah berita ini baru."""
        try:
            c = self.conn.cursor()
            c.execute("SELECT 1 FROM history WHERE id = ?", (entry_id,))
            return c.fetchone() is None
        except Exception as e:
            logger.error(f"Database error in is_new: {e}")
            return False

    def filter_new_identifiers(self, identifiers):
        """Mengecek daftar identifier mana yang baru (belum ada di database)."""
        if not identifiers:
            return []

        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()

            # Chunking to avoid SQLite variable limit (default 999)
            chunk_size = 900
            existing_ids = set()

            # Remove duplicates from input list to optimize query
            unique_identifiers = list(dict.fromkeys(identifiers))

            for i in range(0, len(unique_identifiers), chunk_size):
                chunk = unique_identifiers[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                c.execute(f"SELECT id FROM history WHERE id IN ({placeholders})", chunk)
                for row in c.fetchall():
                    existing_ids.add(row[0])

            conn.close()

            # Return identifiers that are not in existing_ids, preserving original order if possible
            return [i for i in identifiers if i not in existing_ids]
        except Exception as e:
            logger.error(f"Database error in filter_new_identifiers: {e}")
            return identifiers

    def get_new_entries(self, entries):
        """Memfilter list of entries dan mengembalikan hanya yang baru."""
        if not entries:
            return []

        # Kita butuh list agar bisa diiterasi berulang atau diakses indexnya
        entries_list = list(entries)

        # Map entries to their identifiers
        # Gunakan list identifier untuk bulk check
        identifiers = [entry.get('id', entry.get('link')) for entry in entries_list]

        new_ids = set(self.filter_new_identifiers(identifiers))

        # Return entries yang identifiernya ada di new_ids, tetap menjaga order input
        return [entry for entry in entries_list if entry.get('id', entry.get('link')) in new_ids]

    def mark_as_read(self, entry_id):
        """Menandai berita sebagai sudah dibaca/dikirim."""
        try:
            c = self.conn.cursor()
            c.execute("INSERT OR IGNORE INTO history (id) VALUES (?)", (entry_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

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

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def _fetch_feed_blocking(self, url, timeout=30):
        """Helper blocking untuk mengambil feed dengan timeout."""
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()

    async def fetch_feed(self, url):
        """Mengambil dan memparsing data RSS dengan aiohttp + headers."""
        logger.info(f"Fetching feed from: {url}")
        
        # Headers untuk meniru browser asli
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Encoding': 'gzip, deflate'
        }

        feed = None
        try:
            session = await self._get_session()
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    content = await response.read()
                    loop = asyncio.get_event_loop()
                    feed = await loop.run_in_executor(None, feedparser.parse, content)
                elif response.status in [403, 429]:
                    logger.warning(f"Warning: Access denied (HTTP {response.status}). Site might be blocking bots.")
                    return []
                else:
                    logger.warning(f"Warning: Failed to fetch feed (HTTP {response.status})")
                    return []

        except Exception as e:
            logger.error(f"Error fetching feed via aiohttp: {e}")
            # Fallback ke urllib dengan timeout jika gagal total (blocking, run in executor)
            try:
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(None, self._fetch_feed_blocking, url)
                feed = await loop.run_in_executor(None, feedparser.parse, content)
            except Exception as e2:
                logger.error(f"Fallback failed: {e2}")
                return []

        if feed and feed.bozo:
             logger.warning(f"Warning: Error parsing feed: {feed.bozo_exception}")

        return feed.entries if feed else []

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
