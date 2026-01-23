import telegram
from telegram.request import HTTPXRequest
import asyncio
from config.config import BOT_TOKEN, GROUP_ID, TOPIC_ID, IV_RHASH


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

        # Format Pesan
        # Fitur Instant View:
        # Jika rhash ada, kita buat link IV: https://t.me/iv?url=<url>&rhash=<rhash>
        # Link ini bisa disembunyikan dalam karakter invisible atau zero-width space agar trigger preview
        
        iv_link = ""
        if self.iv_rhash:
            iv_link = f"https://t.me/iv?url={link}&rhash={self.iv_rhash}"
        else:
            # Jika tidak ada rhash khusus, telegram biasanya attempt native IV untuk domain populer,
            # atau kita cuma berharap preview biasa.
            pass

        # Strategi Preview:
        # Kita ingin Gambar Headline (dari image_url) ATAU Instant View.
        # Jika ada Image URL dan kita kirim sebagai Photo, IV mungkin tidak muncul di caption (tergantung client).
        # Biasanya: Kirim sebagai Message dengan Link Preview enabled.
        # Agar gambar custom muncul di preview link:
        # 1. Web page punya og:image yang benar -> Telegram otomatis ambil.
        # 2. Kita inject hidden link ke gambar di awal pesan? (Telegram pakai first link for preview)
        
        message_text = ""
        
        # Prioritas tampilan:
        # Jika user ingin "Kirim berita dengan gambar headline/thumbnail" (Spec #5)
        # Dan "HARUS pakai fitur instant view" (Spec #7)
        
        # Masalah: Kirim Foto (send_photo) tidak memicu Instant View pada captionnya klik.
        # Instant View muncul dari Link Preview.
        # Jadi kita harus kirim TEXT message yang mengandung Link.
        
        # Trik:
        # <a href="IV_LINK_OR_REAL_LINK"> </a> (Zero width space or Image character)
        # Telegram akan merender preview dari link pertama di pesan.
        
        preview_link = iv_link if iv_link else link
        
        # Menyusun HTML
        # Kita taruh link preview di paling atas, invisible atau membungkus judul
        # Cara paling bersih: <a href="LINK"><b>JUDUL</b></a>
        
        if iv_link:
            message_text += f"<a href='{iv_link}'><b>{title}</b></a>\n\n"
        else:
            message_text += f"<a href='{link}'><b>{title}</b></a>\n\n"
            
        message_text += f"{summary}\n"
        message_text += f"<a href='{link}'>Baca Selengkapnya</a>"

        # Jika kita ingin memaksa gambar thumbnail spesifik muncul di link preview (jika IV gagal/tidak ada),
        # susah dikontrol sepenuhnya dari bot API kecuali website target mendukungnya.
        # Tapi spec #5 bilang "kirim berita dengan gambar".
        # Opsi A: Kirim send_photo. Konsekuensi: IV button mungkin gak muncul di bawah foto, tapi link di caption tetap bisa IV jika diklik.
        # Opsi B: Kirim text dengan link preview. Telegram akan ambil gambar dari Link (og:image).
        
        # Asumsi: User ingin IV adalah prioritas utama (Spec #7 HARUS).
        # Instant View RENDER di client Telegram berbasis Link Preview.
        # Jadi send_message adalah jalan terbaik.
        
        try:
            print(f"Sending: {title}")
            await self.bot.send_message(
                chat_id=self.group_id,
                message_thread_id=self.topic_id,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return True
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
