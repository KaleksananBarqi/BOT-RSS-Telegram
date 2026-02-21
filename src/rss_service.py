import aiosqlite
import feedparser
import json
import os
import ssl
import urllib.request
import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from config.config import USER_AGENT

MAX_FEED_SIZE = 10 * 1024 * 1024  # 10MB limit for RSS feed responses



logger = logging.getLogger(__name__)

class RSSService:
    def __init__(self, db_file='data/bot.db', json_history_file='data/history.json'):
        self.db_file = db_file
        self.json_history_file = json_history_file
        self.session = None
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.conn = None

    async def initialize(self):
        """Async initialization - must be called after construction."""
        self.conn = await aiosqlite.connect(self.db_file)
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("PRAGMA synchronous=NORMAL;")
        await self._create_tables()
        await self._migrate_json_to_db()

    async def _create_tables(self):
        """Create database tables."""
        try:
            await self.conn.execute('''CREATE TABLE IF NOT EXISTS history
                         (id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            await self.conn.execute('''CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at)''')
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def _migrate_json_to_db(self):
        """Migrasi data dari JSON lama ke SQLite jika ada."""
        if not os.path.exists(self.json_history_file):
            return

        try:
            cursor = await self.conn.cursor()
            await cursor.execute("SELECT count(*) FROM history")
            count = (await cursor.fetchone())[0]

            if count == 0:
                logger.info("Migrating history from JSON to SQLite...")
                try:
                    with open(self.json_history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if isinstance(history, list):
                            for item in history:
                                await cursor.execute("INSERT OR IGNORE INTO history (id) VALUES (?)", (str(item),))
                            await self.conn.commit()
                            logger.info(f"Migration complete. Imported {len(history)} items.")
                        else:
                            logger.warning("JSON history format invalid, skipping migration.")
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to read JSON history for migration: {e}")
            await cursor.close()
        except Exception as e:
            logger.error(f"Migration check failed: {e}")

    async def is_new(self, entry_id):
        """Mengecek apakah berita ini baru."""
        try:
            cursor = await self.conn.cursor()
            await cursor.execute("SELECT 1 FROM history WHERE id = ?", (entry_id,))
            result = await cursor.fetchone()
            await cursor.close()
            return result is None
        except Exception as e:
            logger.error(f"Database error in is_new: {e}")
            return False

    async def filter_new_identifiers(self, identifiers):
        """Mengecek daftar identifier mana yang baru (belum ada di database)."""
        if not identifiers:
            return []

        try:
            chunk_size = 900
            existing_ids = set()

            unique_identifiers = list(dict.fromkeys(identifiers))

            cursor = await self.conn.cursor()
            for i in range(0, len(unique_identifiers), chunk_size):
                chunk = unique_identifiers[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                await cursor.execute(f"SELECT id FROM history WHERE id IN ({placeholders})", chunk)
                rows = await cursor.fetchall()
                for row in rows:
                    existing_ids.add(row[0])
            await cursor.close()

            return [i for i in identifiers if i not in existing_ids]
        except Exception as e:
            logger.error(f"Database error in filter_new_identifiers: {e}")
            return identifiers

    async def get_new_entries(self, entries):
        """Memfilter list of entries dan mengembalikan hanya yang baru."""
        if not entries:
            return []

        entries_list = list(entries)

        identifiers = [entry.get('id', entry.get('link')) for entry in entries_list]

        new_ids = set(await self.filter_new_identifiers(identifiers))

        return [entry for entry in entries_list if entry.get('id', entry.get('link')) in new_ids]

    async def mark_as_read(self, entry_id):
        """Menandai berita sebagai sudah dibaca/dikirim."""
        try:
            await self.conn.execute("INSERT OR IGNORE INTO history (id) VALUES (?)", (entry_id,))
            await self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def extract_image(self, entry, soup=None):
        """Mencoba mengekstrak gambar dari entry RSS."""
        # 1. Cek Media Content (biasa di RSS modern)
        if 'media_content' in entry:
            for media in entry.media_content:
                if (media.get('type', '').startswith('image') or media.get('medium') == 'image'):
                    if media.get('url'):
                        return media['url']
        
        # 2. Cek Media Thumbnail
        if 'media_thumbnail' in entry and entry.media_thumbnail:
            if entry.media_thumbnail[0].get('url'):
                return entry.media_thumbnail[0]['url']

        # 3. Cek Enclosures
        if 'enclosures' in entry:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    if enclosure.get('url'):
                        return enclosure['url']

        # 4. Parsing HTML Description/Summary
        if soup is None:
            content = entry.get('summary', '') or entry.get('description', '')
            if content:
                soup = BeautifulSoup(content, 'html.parser')

        if soup:
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
            await self.conn.close()

    def _fetch_feed_blocking(self, url, timeout=30):
        """Helper blocking untuk mengambil feed dengan timeout."""
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = b""
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                content += chunk
                if len(content) > MAX_FEED_SIZE:
                    raise ValueError(f"Response too large ({len(content)} bytes)")
            return content

    async def _read_response_with_limit(self, response):
        """Read response content with size limit to prevent DoS via unbounded reads."""
        content = b""
        while True:
            chunk = await response.read(8192)
            if not chunk:
                break
            content += chunk
            if len(content) > MAX_FEED_SIZE:
                raise ValueError(f"Response too large ({len(content)} bytes)")
        return content

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
                    content = await self._read_response_with_limit(response)
                    loop = asyncio.get_running_loop()
                    feed = await loop.run_in_executor(None, feedparser.parse, content)
                elif response.status in [403, 429]:
                    logger.warning(f"Warning: Access denied (HTTP {response.status}). Site might be blocking bots.")
                    return []
                else:
                    logger.warning(f"Warning: Failed to fetch feed (HTTP {response.status})")
                    return []

        except (aiohttp.ClientConnectorSSLError, aiohttp.ServerFingerprintMismatch) as e:
            logger.error(f"SSL Verification failed for {url}: {e}")
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
        raw_summary = entry.get('summary', '') or entry.get('description', '')
        soup = BeautifulSoup(raw_summary, 'html.parser') if raw_summary else None

        image_url = self.extract_image(entry, soup=soup)

        if soup:
            text = soup.get_text()
            clean_summary = text[:300] + "..." if len(text) > 300 else text
        else:
            clean_summary = ''

        return {
            'id': entry.get('id', entry.get('link')),
            'title': entry.get('title', 'No Title'),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'summary': clean_summary,
            'image_url': image_url
        }
