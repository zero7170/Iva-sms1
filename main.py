#Copyright @Arslan-MD
#Updates Channel t.me/arslanmd

import logging
import json
import os
import gzip
from datetime import datetime
from urllib.parse import unquote, quote

import requests
import brotli
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8985912413:AAFu6r3RE7U0M3u0Wjr-ICej0pTgI-RtHVQ"
CHAT_ID = 7747270285
SCRAPER_API_KEY = "f8a74b5e01470b6283f21f20263fdc40"

SELECT_DATE, MONITOR_RANGE, MONITOR_NUMBER = range(3)

# ─── IVAS Client ─────────────────────────────────────────────────────────────

class IVASSMSClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.ivasms.com"
        self.logged_in = False
        self.csrf_token = None
        self.cookies_str = ""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def scraper_get(self, url, extra_headers=None):
        """GET عبر ScraperAPI مع الكوكيز"""
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={quote(url)}&keep_headers=true"
        headers = {'Cookie': self.cookies_str}
        if extra_headers:
            headers.update(extra_headers)
        return self.session.get(api_url, headers=headers, timeout=60)

    def scraper_post(self, url, data, extra_headers=None):
        """POST عبر ScraperAPI مع الكوكيز"""
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={quote(url)}&keep_headers=true"
        headers = {
            'Cookie': self.cookies_str,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{self.base_url}/portal/sms/received",
        }
        if extra_headers:
            headers.update(extra_headers)
        return self.session.post(api_url, headers=headers, data=data, timeout=60)

    def load_cookies(self, path="cookies.json"):
        try:
            if os.getenv("COOKIES_JSON"):
                raw = json.loads(os.getenv("COOKIES_JSON"))
            else:
                with open(path) as f:
                    raw = json.load(f)
            if isinstance(raw, dict):
                return raw
            elif isinstance(raw, list):
                return {c['name']: c['value'] for c in raw if 'name' in c}
        except Exception as e:
            logger.error(f"Cookie error: {e}")
        return None

    def login(self, path="cookies.json"):
        cookies = self.load_cookies(path)
        if not cookies:
            print("[-] No cookies found")
            return False

        # بناء cookie string
        self.cookies_str = "; ".join([f"{k}={unquote(v)}" for k, v in cookies.items()])
        print(f"[*] Cookies loaded: {list(cookies.keys())}")

        try:
            r = self.scraper_get(f"{self.base_url}/portal/sms/received")
            print(f"[*] Login status: {r.status_code}")
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                token = soup.find('input', {'name': '_token'})
                if token:
                    self.csrf_token = token['value']
                    self.logged_in = True
                    print("[+] Login successful!")
                    return True
                print("[-] CSRF not found")
                print(r.text[:500])
            else:
                print(r.text[:500])
        except Exception as e:
            print(f"[-] Login error: {e}")
        return False

    def get_ranges(self, from_date, to_date=""):
        if not self.logged_in:
            return None
        try:
            r = self.scraper_post(
                f"{self.base_url}/portal/sms/received/getsms",
                data={'from': from_date, 'to': to_date, '_token': self.csrf_token}
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                ranges = []
                for item in soup.select("div.item"):
                    col = item.select_one(".col-sm-4")
                    onclick = col.get('onclick', '') if col else ''
                    range_id = onclick.split("'")[1] if "'" in onclick else ''
                    count_el = item.select_one(".col-3:nth-child(2) p")
                    ranges.append({
                        'name': col.text.strip() if col else '',
                        'range_id': range_id,
                        'count': count_el.text.strip() if count_el else '0',
                    })
                return ranges
        except Exception as e:
            logger.error(f"get_ranges error: {e}")
        return None

    def get_numbers(self, range_id, from_date, to_date=""):
        if not self.logged_in:
            return None
        try:
            r = self.scraper_post(
                f"{self.base_url}/portal/sms/received/getsms/number",
                data={'_token': self.csrf_token, 'start': from_date, 'end': to_date, 'range': range_id}
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                numbers = []
                for item in soup.select("div.card.card-body"):
                    col = item.select_one(".col-sm-4")
                    onclick = col.get('onclick', '') if col else ''
                    parts = onclick.split("'")
                    num_id = parts[3] if len(parts) > 3 else ''
                    count_el = item.select_one(".col-3:nth-child(2) p")
                    numbers.append({
                        'phone': col.text.strip() if col else '',
                        'num_id': num_id,
                        'count': count_el.text.strip() if count_el else '0',
                    })
                return numbers
        except Exception as e:
            logger.error(f"get_numbers error: {e}")
        return None

    def get_otp(self, phone, range_id, from_date, to_date=""):
        if not self.logged_in:
            return None
        try:
            r = self.scraper_post(
                f"{self.base_url}/portal/sms/received/getsms/number/sms",
                data={'_token': self.csrf_token, 'start': from_date, 'end': to_date, 'Number': phone, 'Range': range_id}
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                msg = soup.select_one(".col-9.col-sm-6 p")
                return msg.text.strip() if msg else None
        except Exception as e:
            logger.error(f"get_otp error: {e}")
        return None


client = IVASSMSClient()

# ─── Bot Handlers ─────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 عرض الأرقام", callback_data="show_numbers")],
        [InlineKeyboardButton("👁 مراقبة رقم", callback_data="monitor")],
        [InlineKeyboardButton("🔄 تحديث الكوكيز", callback_data="reload_cookies")],
    ]
    await update.message.reply_text(
        "🤖 *بوت IVAS SMS*\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in ("show_numbers", "monitor"):
        ctx.user_data['action'] = data
        await query.edit_message_text("📅 أرسل التاريخ بصيغة DD/MM/YYYY\nمثال: 07/06/2026")
        return SELECT_DATE

    elif data == "reload_cookies":
        if client.login():
            await query.edit_message_text("✅ تم تحديث الكوكيز بنجاح!")
        else:
            await query.edit_message_text("❌ فشل تحديث الكوكيز!")

    elif data.startswith("range_"):
        range_id = data[6:]
        from_date = ctx.user_data.get('from_date', '')
        await query.edit_message_text(f"⏳ جاري جلب الأرقام...")
        numbers = client.get_numbers(range_id, from_date)
        if not numbers:
            await query.edit_message_text("❌ لا توجد أرقام.")
            return ConversationHandler.END
        ctx.user_data['range_id'] = range_id
        keyboard = [
            [InlineKeyboardButton(f"📱 {n['phone']} ({n['count']} SMS)", callback_data=f"num_{n['phone']}")]
            for n in numbers
        ]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
        await query.edit_message_text(
            "📱 *الأرقام المتاحة:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MONITOR_NUMBER

    elif data.startswith("num_"):
        phone = data[4:]
        range_id = ctx.user_data.get('range_id', '')
        from_date = ctx.user_data.get('from_date', '')
        action = ctx.user_data.get('action', 'show_numbers')
        await query.edit_message_text(f"⏳ جاري جلب OTP للرقم {phone}...")
        otp = client.get_otp(phone, range_id, from_date)
        if otp:
            await query.edit_message_text(
                f"✅ *OTP للرقم* `{phone}`:\n\n`{otp}`",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"❌ لا يوجد OTP للرقم {phone}.")

        if action == "monitor":
            await ctx.bot.send_message(
                CHAT_ID,
                f"👁 بدأت مراقبة الرقم `{phone}` كل 30 ثانية...",
                parse_mode='Markdown'
            )
            ctx.job_queue.run_repeating(
                monitor_job,
                interval=30,
                first=30,
                data={'phone': phone, 'range_id': range_id, 'from_date': from_date, 'last_otp': otp},
                name=f"monitor_{phone}"
            )
        return ConversationHandler.END

    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("📋 عرض الأرقام", callback_data="show_numbers")],
            [InlineKeyboardButton("👁 مراقبة رقم", callback_data="monitor")],
            [InlineKeyboardButton("🔄 تحديث الكوكيز", callback_data="reload_cookies")],
        ]
        await query.edit_message_text(
            "🤖 *بوت IVAS SMS*\n\nاختر من القائمة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def receive_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    try:
        datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        await update.message.reply_text("❌ صيغة خاطئة. استخدم DD/MM/YYYY")
        return SELECT_DATE

    ctx.user_data['from_date'] = date_str
    await update.message.reply_text(f"⏳ جاري جلب البيانات ليوم {date_str}...")
    ranges = client.get_ranges(date_str)

    if not ranges:
        await update.message.reply_text("❌ لا توجد بيانات أو فشل الاتصال.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f"🌍 {r['name']} ({r['count']} SMS)", callback_data=f"range_{r['range_id']}")]
        for r in ranges
    ]
    await update.message.reply_text(
        f"📋 *النطاقات المتاحة ليوم {date_str}:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MONITOR_RANGE

async def monitor_job(ctx: ContextTypes.DEFAULT_TYPE):
    job = ctx.job
    data = job.data
    phone = data['phone']
    range_id = data['range_id']
    from_date = data['from_date']
    last_otp = data['last_otp']

    otp = client.get_otp(phone, range_id, from_date)
    if otp and otp != last_otp:
        data['last_otp'] = otp
        await ctx.bot.send_message(
            CHAT_ID,
            f"🔔 *OTP جديد للرقم* `{phone}`!\n\n`{otp}`",
            parse_mode='Markdown'
        )

async def stop_monitor(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    removed = []
    for job in ctx.job_queue.jobs():
        if job.name and job.name.startswith("monitor_"):
            job.schedule_removal()
            removed.append(job.name.replace("monitor_", ""))
    if removed:
        await update.message.reply_text(f"✅ تم إيقاف مراقبة: {', '.join(removed)}")
    else:
        await update.message.reply_text("❌ لا توجد مراقبة نشطة.")

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("[*] Starting IVAS SMS Bot...")
    if not client.login():
        print("[-] Failed to login. Check cookies.json")
        return
    print("[+] Bot started successfully!")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^(show_numbers|monitor)$")],
        states={
            SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
            MONITOR_RANGE: [CallbackQueryHandler(button_handler, pattern="^range_")],
            MONITOR_NUMBER: [CallbackQueryHandler(button_handler, pattern="^num_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_monitor))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("[+] Bot is running!")
    app.run_polling()

if __name__ == '__main__':
    main()
                                  
