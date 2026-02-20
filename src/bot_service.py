import telegram
from telegram.request import HTTPXRequest
import asyncio
import logging
import html
from config.config import BOT_TOKEN, GROUP_ID, TOPIC_ID, IV_RHASH

logger = logging.getLogger(__name__)

class BotService:
    def __init__(self):
        # Menggunakan HTTPXRequest untuk performa lebih baik (default di v20+)
        self.bot = telegram.Bot(token=BOT_TOKEN, request=HTTPXRequest())
        self.group_id = GROUP_ID
        self.topic_id = int(TOPIC_ID) if TOPIC_ID else None
        self.iv_rhash = IV_RHASH

    async def send_post(self, post_data):
        """Mengirim berita ke Telegram."""
        title = post_data['title']
        link = post_data['link']
        summary = post_data['summary']
        image_url = post_data['image_url']

        # Escape HTML characters to prevent injection
        escaped_title = html.escape(title)
        escaped_summary = html.escape(summary) if summary else ""
        escaped_link = html.escape(link, quote=True)

        # Tentukan link untuk preview (IV Link jika ada, atau Link asli)
        iv_link = f"https://t.me/iv?url={link}&rhash={self.iv_rhash}" if self.iv_rhash else ""
        target_link = iv_link if iv_link else link
        escaped_target_link = html.escape(target_link, quote=True)
        
        message_text = ""
        
        # 1. Judul dengan Link (mengutamakan IV Link untuk preview jika ada)
        message_text += f"<a href='{escaped_target_link}'><b>{escaped_title}</b></a>\n\n"
        
        # 2. Summary
        if escaped_summary:
             message_text += f"{escaped_summary}\n\n"
             
        # 3. Footer / Source
        message_text += f"<a href='{escaped_link}'>Read More</a>"

        # Kirim pesan
        # Kita gunakan send_message agar Link Preview (IV) muncul dari link pertama di text.
        
        try:
            logger.info(f"Sending: {title}")
            await self.bot.send_message(
                chat_id=self.group_id,
                message_thread_id=self.topic_id,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
