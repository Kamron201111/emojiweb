"""
sonnet_final.py — Birlashtirilgan bot: "Name Emojis" (newbot_fixed) + "Logo/Text Emojis"
(tgs_make_bot) bitta botda.

/start bosilganda 2 ta bo'lim ko'rsatiladi:
  🔤 Name Emojis      — so'zdan tayyor shablon ustiga yozilgan animatsiyali emoji
  🖼 Logo/Text Emojis — 103 ta tayyor shablondan birini tanlab, ustiga
                        o'zingizning matningizni joylash

FAYL TUZILISHI:
    sonnet_final.py        <- shu fayl (Telegram handlerlari)
    logo_engine.py         <- SVG/Lottie generatsiya "dvigateli" (tgs_make_bot'dan)
    logo_emoji_ids.py      <- Logo/Text shablonlari uchun preview custom_emoji_id lar
    template_engine.py     <- Name emoji render dvigateli (o'zgarishsiz)
    font_render.py         <- Name emoji shrift render (o'zgarishsiz)
    templates_config.py    <- Name emoji shablonlari sozlamalari (o'zgarishsiz)
    templates/*.json       <- Name emoji shablonlari
    templates_tgs/*.json   <- Logo/Text emoji shablonlari (yangilangan JSON'lar)
    fonts/*.ttf             <- Har ikkala bo'lim uchun shriftlar
"""

import asyncio
import json
import logging
import os
import random
import re
import string
import zipfile

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    MessageEntity,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
)

import logo_engine
from logo_emoji_ids import LOGO_TEMPLATE_EMOJI_IDS, LOGO2_TEMPLATE_EMOJI_IDS, LOGO3_TEMPLATE_EMOJI_IDS
from template_engine import render_template, save_as_tgs
from templates_config import EMOJI_IDS, TEMPLATE_ORDER, TEMPLATES

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8770112745:AAEpTDv_ffoXY4jWgf8msgrrfOHsE2lFGXw")
MAX_LEN = 12
PLACEHOLDER = "\U0001F538"


def _random_nick(length: int = 12) -> str:
    """Telegram-style random lowercase nick, e.g. 'wiwheowuwhsj'."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


ADMIN_IDS = [5359957511]  # <-- Telegram user_id
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
LOG_CHAT_ID = -1003921430988  # <-- log kanali ID
ALLOWED_FILE = os.path.join(os.path.dirname(__file__), "allowed_users.json")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
EMOJI_PACK_FILE = os.path.join(os.path.dirname(__file__), "emoji_pack.json")
USER_LANG_FILE = os.path.join(os.path.dirname(__file__), "user_languages.json")
PRICE_FILES = {
    "name": os.path.join(os.path.dirname(__file__), "price_name.json"),
    "logo": os.path.join(os.path.dirname(__file__), "price_logo.json"),
    "logo2": os.path.join(os.path.dirname(__file__), "price_logo2.json"),
    "logo3": os.path.join(os.path.dirname(__file__), "price_logo3.json"),
    "code": os.path.join(os.path.dirname(__file__), "price_code.json"),
    "pf": os.path.join(os.path.dirname(__file__), "price_pf.json"),
}
CREDITS_FILE = os.path.join(os.path.dirname(__file__), "credits.json")
STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")
REFUND_REQUESTS_FILE = os.path.join(os.path.dirname(__file__), "refund_requests.json")
REFERRALS_FILE = os.path.join(os.path.dirname(__file__), "referrals.json")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DEFAULT_PRICE_STARS = 15
DEFAULT_CODE_PRICE_STARS = 5000
DEFAULT_SUPPORT_CONTACT = "@your_support_username"
LOGO_PAGE_SIZE = 10
LOGO_SECTIONS = {
    "logo": {
        "dir": os.path.join(os.path.dirname(__file__), "templates_tgs"),
        "title": "🖼 Logo/Text Emojis",
    },
    "logo2": {
        "dir": os.path.join(os.path.dirname(__file__), "templates_tgs2"),
        "title": "😎 Extra Emojis (Bo'lim 3)",
    },
    "logo3": {
        "dir": os.path.join(os.path.dirname(__file__), "templates_tgs3"),
        "title": "Extra Emojis (Bo'lim 4)",
    }
}
def get_total_logo_templates(kind="logo"):
    d = LOGO_SECTIONS.get(kind, LOGO_SECTIONS["logo"])["dir"]
    if not os.path.isdir(d): return 0
    return len([f for f in os.listdir(d) if f.endswith(".json")])


# ============================================================================
# MULTI-LANGUAGE SYSTEM (Uzbek, Russian, English)
# ============================================================================

def load_user_langs() -> dict:
    if not os.path.exists(USER_LANG_FILE):
        return {}
    try:
        with open(USER_LANG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_user_langs(langs: dict):
    with open(USER_LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(langs, f, ensure_ascii=False, indent=2)


def get_user_lang(user_id: int) -> str | None:
    return load_user_langs().get(str(user_id))


def set_user_lang(user_id: int, lang: str):
    langs = load_user_langs()
    langs[str(user_id)] = lang
    save_user_langs(langs)


TEXTS = {
    "uz": {
        "lang_select_title": "🌐 Tilni tanlang / Выберите язык / Select language:",
        "lang_chosen_msg": "✅ O'zbek tili tanlandi!",
        "start_welcome": "👋 Xush kelibsiz!",
        "choose_section": "Nima yasaymiz? 👇",
        "btn_name": "Name Emojis",
        "btn_logo": "Logo/Text Emojis",
        "btn_logo2": "Extra Emojis (Bo'lim 3)",
        "btn_logo3": "Extra Emojis (Bo'lim 4)",
        "btn_gift": "Yulduz hadya qilish",
        "btn_help": "Yordam",
        "btn_lang": "Tilni o'zgartirish",
        "btn_buy_code": "💻 Bot kodini olish",
        "subscribe_prompt": "Botdan foydalanish uchun avval kanal(lar)ga a'zo bo'ling, so'ng \"Tekshirish\" tugmasini bosing:",
        "btn_sub_channel": "📢 Kanalga o'tish",
        "btn_sub_channel_n": "➕ Obuna bo'lish #{i}",
        "btn_sub_check": "✅ Tekshirish",
        "sub_not_yet": "Hali barcha kanallarga a'zo bo'lmadingiz.",
        "sub_confirmed": "✅ Tasdiqlandi!",
        "help_text": "🆘 Savol yoki muammo bo'lsa {support} ga yozing.\n\n🎁 Do'stingizni taklif qiling! U birinchi emoji/stikerini yasab bo'lgach, sizga 1 ta bepul kredit beriladi (keyingi emojingiz uchun to'lovsiz foydalanasiz).\n\nSizning taklif havolangiz:\n{ref_link}\n\n💳 Hozir sizda {credits} ta bepul kredit bor.",
        "gift_prompt": "🎁 Nechta ⭐ Stars hadya qilmoqchisiz? Sonini yozing (masalan: 100):",
        "gift_invalid": "Iltimos, faqat son yuboring (masalan: 100).",
        "gift_range": "Son {min} dan {max} tagacha bo'lishi kerak. Qaytadan yozing:",
        "gift_invoice_title": "⭐ Yulduz hadya",
        "gift_invoice_desc": "{amount} ⭐ Stars hadya qilish",
        "gift_thanks": "✅ Rahmat! {amount} ⭐ Stars hadyangiz uchun tashakkur 🙏",
        "code_invoice_title": "💻 Bot manba kodi",
        "code_invoice_desc": "Botning to'liq manba kodi (barcha fayllar bilan), {price} ⭐",
        "code_stale_price": "❌ Bu eski taklif edi, narx shu orada {current_price} ⭐ ga o'zgargan — shuning uchun fayl berilmadi.\n\nIltimos {support} ga yozing, yoki pastdagi \"{btn_code}\" tugmasini hozirgi narxda qaytadan bosing.",
        "code_paid_preparing": "✅ To'lov qabul qilindi! Bot kodi tayyorlanmoqda...",
        "code_caption": "💻 Mana botning to'liq manba kodi. O'z BOT_TOKEN, ADMIN_IDS va LOG_CHAT_ID qiymatlaringizni sonnet_final.py ichida to'ldiring.",
        "code_error": "❌ Kodni yuborishda xatolik: {error}\n\nIltimos {support} ga yozing.",
        "name_choose_tpl": "Qaysi birini yasaymiz?",
        "choose_template": "Qaysi birini yasaymiz?",
        "btn_all": "Hammasi",
        "btn_all_templates": "✨ Hammasi",
        "btn_back_main": "⬅️ Bosh menyu",
        "enter_word": "✍️ So'zingizni yozing (maksimum {max_len} ta harf):",
        "invalid_word": "So'z 1 dan {max_len} tagacha harf bo'lishi kerak. Qaytadan yozing:",
        "outer_color_prompt": "1️⃣ TASHQI (chegara) rangini tanlang:",
        "tpl_selected_outer_prompt": "✅ {n}-shablon tanlandi.\n\n1️⃣ TASHQI (chegara) rangini tanlang:",
        "outer_hex_prompt": "Tashqi (chegara) rangini #RRGGBB ko'rinishida yuboring. Masalan: #FF0000",
        "outer_custom_prompt": "Tashqi (chegara) rangini #RRGGBB ko'rinishida yuboring. Masalan: #FF0000",
        "outer_chosen_toast": "Rang: {color}",
        "outer_hex_set": "✅ {hex}\n\n2️⃣ ICHKI fon rangini tanlang:",
        "inner_color_prompt": "2️⃣ ICHKI fon rangini tanlang:",
        "inner_prompt": "2️⃣ ICHKI fon rangini tanlang:",
        "inner_hex_prompt": "Ichki fon rangini #RRGGBB ko'rinishida yuboring. Masalan: #000000",
        "inner_custom_prompt": "Ichki fon rangini #RRGGBB ko'rinishida yuboring. Masalan: #000000",
        "inner_chosen_toast": "Rang: {color}",
        "inner_hex_set": "✅ {hex}\n\n3️⃣ LOGO rangini tanlang:",
        "text_color_prompt": "3️⃣ Yozuv (text) rangini tanlang (asl rangda qolishi uchun — Skip bosing):",
        "text_hex_prompt": "Yozuv rangini #RRGGBB ko'rinishida yuboring. Masalan: #FFFFFF",
        "logo_color_prompt": "3️⃣ LOGO rangini tanlang (logoda 2-3 ta o'z rangi bo'lsa — Skip bosing, asl rangida qoladi):",
        "logo_hex_prompt": "Logo rangini #RRGGBB ko'rinishida yuboring. Masalan: #FFFFFF",
        "logo_custom_prompt": "Logo rangini #RRGGBB ko'rinishida yuboring. Masalan: #FFFFFF",
        "logo_skip_toast": "Logo o'z rangida qoladi",
        "logo_color_toast": "Rang: {color}",
        "skip_text_color": "Yozuv asl rangida qoladi",
        "skip_logo_color": "Logo o'z rangida qoladi",
        "invalid_hex": "Noto'g'ri format. Masalan: #FF0000 ko'rinishida yuboring.",
        "btn_custom_hex": "🎨 O'zim kiritaman (HEX kod)",
        "btn_skip_color": "⏭ Skip — asl rangida qoladi",
        "tpl_selected": "✅ {n}-shablon tanlandi.",
        "tpl_selected_toast": "✅ {n}-shablon tanlandi.",
        "enter_logo_text": "✍️ Endi matn yozing (masalan: Salom):",
        "text_input_prompt": "✍️ Endi matn yozing (masalan: Salom):",
        "logo_hex_set": "✅ {hex}\n\n✍️ Endi matn yozing (masalan: Salom):",
        "enter_logo_text_err": "Iltimos, shunchaki matn yozing (masalan: Salom).",
        "just_text_prompt": "Iltimos, shunchaki matn yozing (masalan: Salom).",
        "logo_render_err": "❌ Matndan logo yasab bo'lmadi: {error}",
        "logo_build_error": "❌ Matndan logo yasab bo'lmadi: {error}",
        "svg_convert_error": "❌ Matndan logo yasab bo'lmadi: {error}",
        "pack_title_prompt": "To'plam nomini yozing (bu Telegram'da ko'rinadigan sarlavha bo'ladi):",
        "pack_title_invalid": "Nom 1 dan {max_len} tagacha belgidan iborat bo'lishi kerak. Qaytadan yozing:",
        "where_to_add": "Qayerga qo'shamiz?",
        "btn_custom_emoji_pack": "💎 Premium custom emoji pack",
        "packtype_emoji": "💎 Premium custom emoji pack",
        "btn_stickers_pack": "🖼 Stickers pack",
        "packtype_sticker": "🖼 Stickers pack",
        "pay_choice_prompt": "Qanday to'laymiz?",
        "how_to_pay": "Qanday to'laymiz?",
        "btn_use_credit": "🎁 Bepul kredit ishlatish ({credits} ta bor)",
        "btn_pay_stars": "⭐ {price} Stars bilan to'lash",
        "no_credit": "Kredit topilmadi.",
        "no_credit_toast": "Kredit topilmadi.",
        "stale_price_pack": "❌ Bu eski taklif edi, narx shu orada o'zgargan — shuning uchun emoji/stiker tayyorlanmadi.\n\nIltimos {support} ga yozing, yoki /start bosib hozirgi narxda qaytadan buyurtma bering.",
        "progress_update": "⏳ Tayyorlanmoqda: {current}/{total} qo'shildi",
        "telegram_limit_wait": "⏳ Telegram cheklovi sababli {seconds}s kutyapmiz ({current}/{total} qo'shildi), keyin davom etamiz...",
        "pack_success": "✅ Tayyor! Mana emojingiz, to'lov uchun rahmat 🙏\n{url}",
        "pack_done_msg": "✅ Tayyor! Mana emojingiz, to'lov uchun rahmat 🙏\n{url}",
        "pack_fail": "❌ To'plamga qo'shib bo'lmadi. Xatolik bo'lsa {support} ga yozing.",
        "pack_failed_msg": "❌ To'plamga qo'shib bo'lmadi. Xatolik bo'lsa {support} ga yozing.",
        "prompt_next": "Yangisini yasash uchun /start bosing.",
        "restart_hint": "Yangisini yasash uchun /start bosing.",
        "referral_reward": "🎉 Siz taklif qilgan do'stingiz birinchi emojisini yasadi!\nSizga 1 ta bepul kredit berildi. Keyingi emojingizni yasaganda ishlatishingiz mumkin.",
        "logo_no_templates": "Bu bo'limda hozircha emoji shablonlari yo'q.",
        "no_templates_in_section": "Bu bo'limda hozircha emoji shablonlari yo'q.",
        "logo_choose_tpl_title": "Qaysi shablonni yasaymiz? ({start}-{end} / {total})",
        "logo_preview_prompt": "Qaysi shablonni yasaymiz? ({start}-{end} / {total})",
        "tpl_n": "{n}-shablon",
        "btn_prev_page": "⬅️ Oldingi",
        "btn_prev": "⬅️ Oldingi",
        "btn_next_page": "Keyingi qatorga o'tish ➡️",
        "btn_next": "Keyingi qatorga o'tish ➡️",
        "btn_custom_templates": "🔢 Shablon raqamini yozish",
        "custom_tpl_prompt": "🔢 Qaysi shablon(lar) kerak? Raqamlarini yozing (1 dan {max_total} tagacha, masalan: 3.8.1 yoki 1, 5, 8):",
        "custom_tpl_invalid": "❌ Noto'g'ri raqam(lar). Qaytadan yozing (1 dan {max_total} tagacha, masalan: 3.8.1):",
        "custom_tpl_selected": "✅ {count} ta shablon tanlandi: {nums}\n\n1️⃣ TASHQI (chegara) rangini tanlang:",
        "pf_choose_where": "Yangi to'plam yaratasizmi yoki emojilarni mavjud to'plamga qo'shasizmi? 👇",
        "pf_btn_new_pack": "✅ Yangi to'plam yaratish",
        "pf_btn_existing_pack": "👤+ Mavjud to'plamga qo'shish",
        "pf_prompt_word": "Nom yozing:\n\n⚠️ Eslatma: Matn qancha uzun bo'lsa, profil foni shunchalik kichik bo'ladi. Maksimal 5 ta harfdan iborat matn ishlatishni tavsiya qilamiz.",
        "pf_prompt_font": "🔤 Shriftni (Font) tanlang:\n\n«{name}» profil foni qaysi shrift dizaynida tayyorlansin?",
        "pf_prompt_pack_title": "To'plam nomini yozing (bu Telegram'da ko'rinadigan sarlavha bo'ladi, masalan: Profile Backgrounds):",
        "pf_prompt_existing_nick": "Mavjud to'plam nikini yozing (masalan: liawlcyimuy):",
        "pf_creating": "⏳ Profil foni yangi shriftda tayyorlanmoqda...",
        "pf_word_invalid": "Nom 1 dan 5 tagacha harf bo'lishi kerak. Qaytadan yozing:",
        "pf_choose_template": "🖼️ Profil foni uchun shablonni tanlang:",
        "pf_btn_default_tpl": "✨ Standart shablon (Toza/002)",
        "pf_btn_choose_tpl": "🖼️ Shablon ko'rish (1-103)",
        "pf_btn_custom_tpl": "🔢 Shablon raqamini yozish",
        "pf_btn_all_tpl": "✨ Barcha shablonlar",
    },
    "ru": {
        "lang_select_title": "🌐 Tilni tanlang / Выберите язык / Select language:",
        "lang_chosen_msg": "✅ Выбран русский язык!",
        "start_welcome": "👋 Добро пожаловать!",
        "choose_section": "Что создаем? 👇",
        "btn_name": "Name Emojis",
        "btn_logo": "Logo/Text Emojis",
        "btn_logo2": "Extra Emojis (Раздел 3)",
        "btn_logo3": "Extra Emojis (Раздел 4)",
        "btn_gift": "Подарить Звезды",
        "btn_help": "Помощь",
        "btn_lang": "Сменить язык",
        "btn_buy_code": "💻 Получить исходный код",
        "subscribe_prompt": "Чтобы использовать бота, сначала подпишитесь на канал(ы), затем нажмите «Проверить»:",
        "btn_sub_channel": "📢 Перейти в канал",
        "btn_sub_channel_n": "➕ Подписаться #{i}",
        "btn_sub_check": "✅ Проверить",
        "sub_not_yet": "Вы еще не подписались на все каналы.",
        "sub_confirmed": "✅ Подтверждено!",
        "help_text": "🆘 По вопросам и проблемам пишите {support}.\n\n🎁 Пригласите друга! Когда он создаст свой первый эмодзи/стикер, вы получите 1 бесплатный кредит (сможете использовать его для следующего эмодзи).\n\nВаша реферальная ссылка:\n{ref_link}\n\n💳 Сейчас у вас {credits} бесплатного(ых) кредита(ов).",
        "gift_prompt": "🎁 Сколько ⭐ Stars вы хотите подарить? Введите число (например: 100):",
        "gift_invalid": "Пожалуйста, отправьте только число (например: 100).",
        "gift_range": "Число должно быть от {min} до {max}. Попробуйте снова:",
        "gift_invoice_title": "⭐ Подарок Stars",
        "gift_invoice_desc": "Подарить {amount} ⭐ Stars",
        "gift_thanks": "✅ Спасибо! Благодарим за подарок в {amount} ⭐ Stars 🙏",
        "code_invoice_title": "💻 Исходный код бота",
        "code_invoice_desc": "Полный исходный код бота (со всеми файлами), {price} ⭐",
        "code_stale_price": "❌ Это предложение устарело, цена изменилась на {current_price} ⭐ — поэтому файл не был отправлен.\n\nПожалуйста, напишите {support} или нажмите кнопку «{btn_code}» снова по актуальной цене.",
        "code_paid_preparing": "✅ Оплата принята! Код бота готовится...",
        "code_caption": "💻 Вот полный исходный код бота. Заполните свои значения BOT_TOKEN, ADMIN_IDS и LOG_CHAT_ID в файле sonnet_final.py.",
        "code_error": "❌ Ошибка отправки кода: {error}\n\nПожалуйста, напишите {support}.",
        "name_choose_tpl": "Какой эмодзи создаем?",
        "choose_template": "Какой эмодзи создаем?",
        "btn_all": "Все",
        "btn_all_templates": "✨ Все",
        "btn_back_main": "⬅️ Главное меню",
        "enter_word": "✍️ Введите ваше слово (максимум {max_len} букв):",
        "invalid_word": "Слово должно быть от 1 до {max_len} букв. Попробуйте снова:",
        "outer_color_prompt": "1️⃣ Выберите ВНЕШНИЙ цвет (границы):",
        "tpl_selected_outer_prompt": "✅ Выбран {n}-й шаблон.\n\n1️⃣ Выберите ВНЕШНИЙ цвет (границы):",
        "outer_hex_prompt": "Отправьте внешний цвет в формате #RRGGBB. Например: #FF0000",
        "outer_custom_prompt": "Отправьте внешний цвет в формате #RRGGBB. Например: #FF0000",
        "outer_chosen_toast": "Цвет: {color}",
        "outer_hex_set": "✅ {hex}\n\n2️⃣ Выберите ВНУТРЕННИЙ цвет фона:",
        "inner_color_prompt": "2️⃣ Выберите ВНУТРЕННИЙ цвет фона:",
        "inner_prompt": "2️⃣ Выберите ВНУТРЕННИЙ цвет фона:",
        "inner_hex_prompt": "Отправьте внутренний цвет фона в формате #RRGGBB. Например: #000000",
        "inner_custom_prompt": "Отправьте внутренний цвет фона в формате #RRGGBB. Например: #000000",
        "inner_chosen_toast": "Цвет: {color}",
        "inner_hex_set": "✅ {hex}\n\n3️⃣ Выберите цвет ЛОГОТИПА:",
        "text_color_prompt": "3️⃣ Выберите цвет текста (чтобы оставить исходный — нажмите Пропустить):",
        "text_hex_prompt": "Отправьте цвет текста в формате #RRGGBB. Например: #FFFFFF",
        "logo_color_prompt": "3️⃣ Выберите цвет ЛОГОТИПА (если у логотипа 2-3 своих цвета — нажмите Пропустить):",
        "logo_hex_prompt": "Отправьте цвет логотипа в формате #RRGGBB. Например: #FFFFFF",
        "logo_custom_prompt": "Отправьте цвет логотипа в формате #RRGGBB. Например: #FFFFFF",
        "logo_skip_toast": "Логотип останется в исходном цвете",
        "logo_color_toast": "Цвет: {color}",
        "skip_text_color": "Текст останется в исходном цвете",
        "skip_logo_color": "Логотип останется в исходном цвете",
        "invalid_hex": "Неверный формат. Например, отправьте: #FF0000",
        "btn_custom_hex": "🎨 Ввести вручную (#HEX)",
        "btn_skip_color": "⏭ Пропустить — оставить исходный цвет",
        "tpl_selected": "✅ Выбран {n}-й шаблон.",
        "tpl_selected_toast": "✅ Выбран {n}-й шаблон.",
        "enter_logo_text": "✍️ Введите текст (например: Привет):",
        "text_input_prompt": "✍️ Введите текст (например: Привет):",
        "logo_hex_set": "✅ {hex}\n\n✍️ Введите текст (например: Привет):",
        "enter_logo_text_err": "Пожалуйста, введите просто текст (например: Привет).",
        "just_text_prompt": "Пожалуйста, введите просто текст (например: Привет).",
        "logo_render_err": "❌ Не удалось создать логотип из текста: {error}",
        "logo_build_error": "❌ Не удалось создать логотип из текста: {error}",
        "svg_convert_error": "❌ Не удалось создать логотип из текста: {error}",
        "pack_title_prompt": "Введите название набора (оно будет отображаться в Telegram):",
        "pack_title_invalid": "Название должно быть от 1 до {max_len} символов. Попробуйте снова:",
        "where_to_add": "Куда добавить?",
        "btn_custom_emoji_pack": "💎 Premium custom emoji pack",
        "packtype_emoji": "💎 Premium custom emoji pack",
        "btn_stickers_pack": "🖼 Stickers pack",
        "packtype_sticker": "🖼 Stickers pack",
        "pay_choice_prompt": "Как оплатим?",
        "how_to_pay": "Как оплатим?",
        "btn_use_credit": "🎁 Использовать бесплатный кредит (есть {credits})",
        "btn_pay_stars": "⭐ Оплатить {price} Stars",
        "no_credit": "Кредит не найден.",
        "no_credit_toast": "Кредит не найден.",
        "stale_price_pack": "❌ Это предложение устарело, цена изменилась — поэтому эмодзи/стикер не был создан.\n\nПожалуйста, напишите {support} или нажмите /start для заказа по текущей цене.",
        "progress_update": "⏳ Подготовка: добавлено {current}/{total}",
        "telegram_limit_wait": "⏳ Из-за лимита Telegram ждем {seconds}сек (добавлено {current}/{total}), затем продолжим...",
        "pack_success": "✅ Готово! Вот ваш эмодзи, спасибо за оплату 🙏\n{url}",
        "pack_done_msg": "✅ Готово! Вот ваш эмодзи, спасибо за оплату 🙏\n{url}",
        "pack_fail": "❌ Не удалось добавить в набор. При ошибке пишите {support}.",
        "pack_failed_msg": "❌ Не удалось добавить в набор. При ошибке пишите {support}.",
        "prompt_next": "Чтобы создать новый, нажмите /start.",
        "restart_hint": "Чтобы создать новый, нажмите /start.",
        "referral_reward": "🎉 Приглашенный вами друг создал свой первый эмодзи!\nВам начислен 1 бесплатный кредит.",
        "logo_no_templates": "В этом разделе пока нет шаблонов эмодзи.",
        "no_templates_in_section": "В этом разделе пока нет шаблонов эмодзи.",
        "logo_choose_tpl_title": "Какой шаблон создаем? ({start}-{end} / {total})",
        "logo_preview_prompt": "Какой шаблон создаем? ({start}-{end} / {total})",
        "tpl_n": "{n}-й шаблон",
        "btn_prev_page": "⬅️ Назад",
        "btn_prev": "⬅️ Назад",
        "btn_next_page": "Вперед ➡️",
        "btn_next": "Вперед ➡️",
        "btn_custom_templates": "🔢 Ввести номера шаблонов",
        "custom_tpl_prompt": "🔢 Какие шаблоны вам нужны? Введите их номера (от 1 до {max_total}, например: 3.8.1 или 1, 5, 8):",
        "custom_tpl_invalid": "❌ Неверный(е) номер(а). Попробуйте снова (от 1 до {max_total}, например: 3.8.1):",
        "custom_tpl_selected": "✅ Выбрано {count} шаблонов: {nums}\n\n1️⃣ Выберите ВНЕШНИЙ цвет (границы):",
        "pf_choose_where": "Создаём новый набор или добавляем эмодзи в существующий? 👇",
        "pf_btn_new_pack": "✅ Создать новый набор",
        "pf_btn_existing_pack": "👤+ Добавить в существующий набор",
        "pf_prompt_word": "Введите текст (имя):\n\n⚠️ Важно: чем длиннее текст, тем меньше он будет на фоне профиля. Рекомендуем максимум 5 букв.",
        "pf_prompt_font": "🔤 Выберите шрифт (Font):\n\nВ каком дизайне шрифта подготовить фон профиля «{name}»?",
        "pf_prompt_pack_title": "Введите название набора (это будет заголовок в Telegram, например: Profile Backgrounds):",
        "pf_prompt_existing_nick": "Введите ник существующего набора (например: liawlcyimuy):",
        "pf_creating": "⏳ Фон профиля подготавливается в новом шрифте...",
        "pf_word_invalid": "Текст должен быть от 1 до 5 букв. Введите снова:",
        "pf_choose_template": "🖼️ Выберите шаблон для фона профиля:",
        "pf_btn_default_tpl": "✨ Стандартный шаблон (Чистый/002)",
        "pf_btn_choose_tpl": "🖼️ Обзор шаблонов (1-103)",
        "pf_btn_custom_tpl": "🔢 Ввести номер шаблона",
        "pf_btn_all_tpl": "✨ Все шаблоны",
    },
    "en": {
        "lang_select_title": "🌐 Tilni tanlang / Выберите язык / Select language:",
        "lang_chosen_msg": "✅ English language selected!",
        "start_welcome": "👋 Welcome!",
        "choose_section": "What would you like to create? 👇",
        "btn_name": "Name Emojis",
        "btn_logo": "Logo/Text Emojis",
        "btn_logo2": "Extra Emojis (Section 3)",
        "btn_logo3": "Extra Emojis (Section 4)",
        "btn_gift": "Gift Stars",
        "btn_help": "Help",
        "btn_lang": "Change Language",
        "btn_buy_code": "💻 Get Bot Source Code",
        "subscribe_prompt": "To use the bot, please subscribe to the channel(s) first, then tap \"Check\":",
        "btn_sub_channel": "📢 Go to Channel",
        "btn_sub_channel_n": "➕ Subscribe #{i}",
        "btn_sub_check": "✅ Check",
        "sub_not_yet": "You haven't subscribed to all channels yet.",
        "sub_confirmed": "✅ Confirmed!",
        "help_text": "🆘 For support or questions contact {support}.\n\n🎁 Invite a friend! Once they create their first emoji/sticker, you will receive 1 free credit (use it free for your next emoji).\n\nYour referral link:\n{ref_link}\n\n💳 You currently have {credits} free credit(s).",
        "gift_prompt": "🎁 How many ⭐ Stars would you like to gift? Enter a number (e.g. 100):",
        "gift_invalid": "Please send digits only (e.g. 100).",
        "gift_range": "Number must be between {min} and {max}. Try again:",
        "gift_invoice_title": "⭐ Stars Gift",
        "gift_invoice_desc": "Gift {amount} ⭐ Stars",
        "gift_thanks": "✅ Thank you! Thanks for your {amount} ⭐ Stars gift 🙏",
        "code_invoice_title": "💻 Bot Source Code",
        "code_invoice_desc": "Full bot source code (with all files), {price} ⭐",
        "code_stale_price": "❌ This is a stale offer, the price changed to {current_price} ⭐ — so the file was not delivered.\n\nPlease contact {support} or press \"{btn_code}\" again at the current price.",
        "code_paid_preparing": "✅ Payment accepted! Preparing bot source code...",
        "code_caption": "💻 Here is the complete bot source code. Fill in your BOT_TOKEN, ADMIN_IDS, and LOG_CHAT_ID in sonnet_final.py.",
        "code_error": "❌ Error sending code: {error}\n\nPlease contact {support}.",
        "name_choose_tpl": "Which emoji template to create?",
        "choose_template": "Which emoji template to create?",
        "btn_all": "All",
        "btn_all_templates": "✨ All",
        "btn_back_main": "⬅️ Main Menu",
        "enter_word": "✍️ Enter your word (maximum {max_len} letters):",
        "invalid_word": "Word must be 1 to {max_len} letters long. Try again:",
        "outer_color_prompt": "1️⃣ Select OUTER border color:",
        "tpl_selected_outer_prompt": "✅ Selected template #{n}.\n\n1️⃣ Select OUTER border color:",
        "outer_hex_prompt": "Send outer color in #RRGGBB format. Example: #FF0000",
        "outer_custom_prompt": "Send outer color in #RRGGBB format. Example: #FF0000",
        "outer_chosen_toast": "Color: {color}",
        "outer_hex_set": "✅ {hex}\n\n2️⃣ Select INNER background color:",
        "inner_color_prompt": "2️⃣ Select INNER background color:",
        "inner_prompt": "2️⃣ Select INNER background color:",
        "inner_hex_prompt": "Send inner color in #RRGGBB format. Example: #000000",
        "inner_custom_prompt": "Send inner color in #RRGGBB format. Example: #000000",
        "inner_chosen_toast": "Color: {color}",
        "inner_hex_set": "✅ {hex}\n\n3️⃣ Select LOGO color:",
        "text_color_prompt": "3️⃣ Select text color (to keep default color — tap Skip):",
        "text_hex_prompt": "Send text color in #RRGGBB format. Example: #FFFFFF",
        "logo_color_prompt": "3️⃣ Select LOGO color (if logo has multi-colors — tap Skip):",
        "logo_hex_prompt": "Send logo color in #RRGGBB format. Example: #FFFFFF",
        "logo_custom_prompt": "Send logo color in #RRGGBB format. Example: #FFFFFF",
        "logo_skip_toast": "Logo will remain in original color",
        "logo_color_toast": "Color: {color}",
        "skip_text_color": "Text will remain in original color",
        "skip_logo_color": "Logo will remain in original color",
        "invalid_hex": "Invalid format. Send like: #FF0000",
        "btn_custom_hex": "🎨 Custom color (#HEX)",
        "btn_skip_color": "⏭ Skip — keep original color",
        "tpl_selected": "✅ Selected template #{n}.",
        "tpl_selected_toast": "✅ Selected template #{n}.",
        "enter_logo_text": "✍️ Enter text (e.g. Hello):",
        "text_input_prompt": "✍️ Enter text (e.g. Hello):",
        "logo_hex_set": "✅ {hex}\n\n✍️ Enter text (e.g. Hello):",
        "enter_logo_text_err": "Please send plain text (e.g. Hello).",
        "just_text_prompt": "Please send plain text (e.g. Hello).",
        "logo_render_err": "❌ Could not render logo from text: {error}",
        "logo_build_error": "❌ Could not render logo from text: {error}",
        "svg_convert_error": "❌ Could not render logo from text: {error}",
        "pack_title_prompt": "Enter pack title (this will be displayed in Telegram):",
        "pack_title_invalid": "Title must be between 1 and {max_len} characters. Try again:",
        "where_to_add": "Where to add?",
        "btn_custom_emoji_pack": "💎 Premium custom emoji pack",
        "packtype_emoji": "💎 Premium custom emoji pack",
        "btn_stickers_pack": "🖼 Stickers pack",
        "packtype_sticker": "🖼 Stickers pack",
        "pay_choice_prompt": "How would you like to pay?",
        "how_to_pay": "How would you like to pay?",
        "btn_use_credit": "🎁 Use free credit ({credits} available)",
        "btn_pay_stars": "⭐ Pay {price} Stars",
        "no_credit": "No credit found.",
        "no_credit_toast": "No credit found.",
        "stale_price_pack": "❌ Stale offer, price has changed — emoji/sticker was not generated.\n\nPlease contact {support} or press /start to re-order at current price.",
        "progress_update": "⏳ Processing: added {current}/{total}",
        "telegram_limit_wait": "⏳ Waiting {seconds}s due to Telegram rate limit ({current}/{total} added)...",
        "pack_success": "✅ Ready! Here is your emoji, thanks for your payment 🙏\n{url}",
        "pack_done_msg": "✅ Ready! Here is your emoji, thanks for your payment 🙏\n{url}",
        "pack_fail": "❌ Could not add to pack. If error occurs contact {support}.",
        "pack_failed_msg": "❌ Could not add to pack. If error occurs contact {support}.",
        "prompt_next": "To create a new one, press /start.",
        "restart_hint": "To create a new one, press /start.",
        "referral_reward": "🎉 Your invited friend created their first emoji!\nYou received 1 free credit.",
        "logo_no_templates": "No emoji templates in this section yet.",
        "no_templates_in_section": "No emoji templates in this section yet.",
        "logo_choose_tpl_title": "Which template to create? ({start}-{end} / {total})",
        "logo_preview_prompt": "Which template to create? ({start}-{end} / {total})",
        "tpl_n": "Template #{n}",
        "btn_prev_page": "⬅️ Previous",
        "btn_prev": "⬅️ Previous",
        "btn_next_page": "Next ➡️",
        "btn_next": "Next ➡️",
        "btn_custom_templates": "🔢 Enter template numbers",
        "custom_tpl_prompt": "🔢 Which template(s) do you need? Enter their numbers (1 to {max_total}, e.g. 3.8.1 or 1, 5, 8):",
        "custom_tpl_invalid": "❌ Invalid number(s). Try again (1 to {max_total}, e.g. 3.8.1):",
        "custom_tpl_selected": "✅ Selected {count} template(s): {nums}\n\n1️⃣ Select OUTER border color:",
        "pf_choose_where": "Create a new pack or add emojis to an existing pack? 👇",
        "pf_btn_new_pack": "✅ Create new pack",
        "pf_btn_existing_pack": "👤+ Add to existing pack",
        "pf_prompt_word": "Enter the text (name):\n\n⚠️ Note: the longer the text, the smaller it will appear on the profile background. Max 5 letters recommended.",
        "pf_prompt_font": "🔤 Choose a font:\n\nWhich font design should be used for the profile background of «{name}»?",
        "pf_prompt_pack_title": "Enter the pack title (shown as Telegram header, e.g. Profile Backgrounds):",
        "pf_prompt_existing_nick": "Enter the existing pack nickname (e.g. liawlcyimuy):",
        "pf_creating": "⏳ Preparing the profile background in the chosen font...",
        "pf_word_invalid": "Text must be between 1 and 5 letters. Enter again:",
        "pf_choose_template": "🖼️ Select a template for profile background:",
        "pf_btn_default_tpl": "✨ Default template (Clean/002)",
        "pf_btn_choose_tpl": "🖼️ Browse templates (1-103)",
        "pf_btn_custom_tpl": "🔢 Enter template numbers",
        "pf_btn_all_tpl": "✨ All templates",
    },
}


def get_text_lang(lang: str, key: str, **kwargs) -> str:
    lang = lang or "uz"
    template = TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))
    if kwargs:
        if "max" in kwargs and "max_len" not in kwargs:
            kwargs["max_len"] = kwargs["max"]
        if "min" in kwargs and "min_amount" not in kwargs:
            kwargs["min_amount"] = kwargs["min"]
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def get_logo_section_title(kind: str, lang: str = "uz") -> str:
    titles = {
        "uz": {
            "logo": "Logo/Text Emojis",
            "logo2": "Extra Emojis (Bo'lim 3)",
            "logo3": "Extra Emojis (Bo'lim 4)",
        },
        "ru": {
            "logo": "Logo/Text Emojis",
            "logo2": "Extra Emojis (Раздел 3)",
            "logo3": "Extra Emojis (Раздел 4)",
        },
        "en": {
            "logo": "Logo/Text Emojis",
            "logo2": "Extra Emojis (Section 3)",
            "logo3": "Extra Emojis (Section 4)",
        },
    }
    return titles.get(lang, titles["uz"]).get(kind, "Emojis")


logging.basicConfig(level=logging.INFO)
router = Router()


# ============================================================================
# Umumiy: pack saqlash, ruxsatlar, foydalanuvchilar, narx, kreditlar, referal,
# majburiy kanallar — ikkala bo'lim (Name / Logo) uchun ham baravar ishlatiladi.
# ============================================================================

def load_packs() -> dict:
    if not os.path.exists(EMOJI_PACK_FILE):
        return {}
    try:
        with open(EMOJI_PACK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_packs(packs: dict):
    with open(EMOJI_PACK_FILE, "w", encoding="utf-8") as f:
        json.dump(packs, f)


def _safe_nick(nick: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", nick)
    return cleaned or "pack"


async def add_stickers_to_pack(
    bot: Bot, sticker_paths: list[str], nick: str, pack_kind: str, progress_message: Message | None = None,
    owner_id: int | None = None, title: str | None = None, lang: str = "uz",
):
    """Create or reuse a sticker set for this nick+kind and add all the
    given stickers to it."""
    from aiogram.types import InputSticker

    sticker_type = "custom_emoji" if pack_kind == "emoji" else "regular"
    owner_id = owner_id or ADMIN_IDS[0]
    packs = load_packs()
    storage_key = f"{pack_kind}:{nick}:{owner_id}"
    name = packs.get(storage_key)
    total = len(sticker_paths)
    last_text = None

    async def update(text: str):
        nonlocal last_text
        if progress_message is None or text == last_text:
            return
        last_text = text
        try:
            await progress_message.edit_text(text)
        except Exception:
            pass

    try:
        me = await bot.get_me()
        if not name:
            name = f"{_safe_nick(nick)}_{owner_id}_by_{me.username}"

        for i, sticker_path in enumerate(sticker_paths):
            item = InputSticker(sticker=FSInputFile(sticker_path), format="animated", emoji_list=["🙂"])
            while True:
                try:
                    if i == 0 and storage_key not in packs:
                        try:
                            await bot.create_new_sticker_set(
                                user_id=owner_id,
                                name=name,
                                title=title or nick,
                                stickers=[item],
                                sticker_type=sticker_type,
                            )
                        except TelegramBadRequest as e:
                            if "already occupied" not in str(e).lower():
                                raise
                            await bot.add_sticker_to_set(user_id=owner_id, name=name, sticker=item)
                        packs[storage_key] = name
                        save_packs(packs)
                    else:
                        await bot.add_sticker_to_set(user_id=owner_id, name=name, sticker=item)
                    break
                except TelegramRetryAfter as e:
                    await update(
                        get_text_lang(lang, "telegram_limit_wait", seconds=e.retry_after, current=i, total=total)
                    )
                    await asyncio.sleep(e.retry_after + 1)
                    continue

            await update(get_text_lang(lang, "progress_update", current=i + 1, total=total))
        return name
    except Exception as e:
        logging.warning(f"pack update failed: {e}")
        return None


def load_allowed() -> set[int]:
    if not os.path.exists(ALLOWED_FILE):
        return set()
    try:
        with open(ALLOWED_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_allowed(ids: set[int]):
    with open(ALLOWED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


def is_free_user(user_id: int) -> bool:
    return is_admin(user_id) or user_id in load_allowed()


def load_users() -> set[int]:
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def save_users(ids: set[int]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


def record_user(user_id: int):
    """Remember that this user has started the bot, so broadcasts can reach them."""
    users = load_users()
    if user_id not in users:
        users.add(user_id)
        save_users(users)


def load_price(kind: str = "name") -> int:
    if kind in PRICE_FILES:
        path = PRICE_FILES[kind]
    elif kind.startswith("logo"):
        path = PRICE_FILES["logo"]
    else:
        path = PRICE_FILES["name"]
    if kind == "code":
        default = DEFAULT_CODE_PRICE_STARS
    elif kind == "pf":
        default = 10
    else:
        default = DEFAULT_PRICE_STARS
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return int(json.load(f).get("stars", default))
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return default


def save_price(kind: str, stars: int):
    if kind in PRICE_FILES:
        path = PRICE_FILES[kind]
    elif kind.startswith("logo"):
        path = PRICE_FILES["logo"]
    else:
        path = PRICE_FILES["name"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"stars": stars}, f)


def price_label(kind: str, lang: str = "uz") -> str:
    labels = {
        "uz": {
            "name": "Name emoji (Bo'lim 1)",
            "logo": "Logo/Text emoji (Bo'lim 2)",
            "logo2": "Extra Emojis (Bo'lim 3)",
            "logo3": "Extra Emojis (Bo'lim 4)",
            "code": "Bot kodi",
            "pf": "Profil foni",
        },
        "ru": {
            "name": "Name emoji (Раздел 1)",
            "logo": "Logo/Text emoji (Раздел 2)",
            "logo2": "Extra Emojis (Раздел 3)",
            "logo3": "Extra Emojis (Раздел 4)",
            "code": "Исходный код бота",
            "pf": "Фон профиля",
        },
        "en": {
            "name": "Name emoji (Section 1)",
            "logo": "Logo/Text emoji (Section 2)",
            "logo2": "Extra Emojis (Section 3)",
            "logo3": "Extra Emojis (Section 4)",
            "code": "Bot source code",
            "pf": "Profile Background",
        },
    }
    return labels.get(lang, labels["uz"]).get(kind, "Emoji")


# ---------- Bot manba kodini sotish uchun toza (sanitized) .zip paket ----------

_CODE_PACKAGE_DIR = os.path.join(os.path.dirname(__file__), "output")
_CODE_PACKAGE_PATH = os.path.join(_CODE_PACKAGE_DIR, "bot_source_code.zip")

# Ishga tushirish paytidagi bu botning o'ziga tegishli maxfiy/runtime
# ma'lumotlari — xaridorga sotilgan nusxada bular BO'LMASLIGI kerak.
_CODE_PACKAGE_EXCLUDE_DIRS = {"__pycache__", "output", "data"}
_CODE_PACKAGE_EXCLUDE_FILES = {
    "users.json", "credits.json", "allowed_users.json", "emoji_pack.json",
    "referrals.json", "settings.json", "stats.json", "refund_requests.json",
    "price_name.json", "price_logo.json", "price_logo2.json", "price_logo3.json", "price_code.json", "price_pf.json",
    "sonnet.lock", "bot.log",
}


def _sanitize_bot_py(content: str) -> str:
    """Sotuvchining haqiqiy BOT_TOKEN/ADMIN_IDS/LOG_CHAT_ID qiymatlarini
    sonnet_final.py nusxasidan olib tashlab, xaridor o'zi to'ldiradigan bo'sh
    joy (placeholder) bilan almashtiradi."""
    content = re.sub(
        r'BOT_TOKEN = os\.environ\.get\("BOT_TOKEN", "[^"]*"\)',
        'BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")',
        content,
    )
    content = re.sub(
        r"ADMIN_IDS\s*=\s*\[.*?\][^\n]*\ndef is_admin\(user_id: int\) -> bool:\s*\n\s*return user_id in ADMIN_IDS",
        'ADMIN_IDS = [0]  # <-- shu yerga o\'zingizning Telegram user_id\'ingizni yozing (bir nechta bo\'lishi mumkin, vergul bilan ajrating)\ndef is_admin(user_id: int) -> bool:\n    return user_id in ADMIN_IDS',
        content,
        flags=re.DOTALL,
    )
    # Legacy support: if old single ADMIN_ID = \d+ line is still found (e.g. older codebases):
    content = re.sub(
        r"ADMIN_ID = \d+[^\n]*",
        "ADMIN_IDS = [0]  # <-- shu yerga o'zingizning Telegram user_id'ingizni yozing",
        content,
    )
    content = re.sub(
        r"LOG_CHAT_ID = -?\d+",
        "LOG_CHAT_ID = 0  # <-- shu yerga o'z log kanalingizning id'sini yozing  # <-- shu yerga o'z log kanalingizning id'sini yozing",
        content,
    )
    return content


def build_code_package() -> str:
    """Botning o'z manba kodidan tozalangan (token/admin/kanal/yordam
    kontakti olib tashlangan) .zip paket yasaydi. Har bir xariddan keyin
    QAYTA yasaladi (fayllar o'zgargan bo'lishi mumkin), lekin bevosita
    umumiy _CODE_PACKAGE_PATH'ga yozmaydi: avval alohida vaqtinchalik
    faylga yozadi, so'ng atomik ravishda almashtiradi. Bu ikkita xarid
    bir vaqtda bo'lganda (yoki eski, hali ochilmagan invoys keyinroq
    to'langanda) bittasi hali yozilayotgan/yarim tugallangan zip fayl
    o'qib yuborilib, xaridorga buzilgan/bo'sh fayl ketishining oldini
    oladi."""
    os.makedirs(_CODE_PACKAGE_DIR, exist_ok=True)
    src_root = os.path.dirname(__file__)

    tmp_path = f"{_CODE_PACKAGE_PATH}.{os.getpid()}.{random.randint(0, 999999)}.tmp"
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(src_root):
            dirnames[:] = [d for d in dirnames if d not in _CODE_PACKAGE_EXCLUDE_DIRS]
            for fname in filenames:
                if fname in _CODE_PACKAGE_EXCLUDE_FILES:
                    continue
                full_path = os.path.join(dirpath, fname)
                arcname = os.path.join("sonnet_final", os.path.relpath(full_path, src_root))
                if fname == "sonnet_final.py":
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()
                    zf.writestr(arcname, _sanitize_bot_py(content))
                else:
                    zf.write(full_path, arcname)

    # Atomic on the same filesystem - readers either see the old complete
    # file or the new complete file, never a half-written one.
    os.replace(tmp_path, _CODE_PACKAGE_PATH)
    return _CODE_PACKAGE_PATH


def load_credits() -> dict:
    if not os.path.exists(CREDITS_FILE):
        return {}
    try:
        with open(CREDITS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_credits(credits: dict):
    with open(CREDITS_FILE, "w", encoding="utf-8") as f:
        json.dump(credits, f)


def get_credits(user_id: int) -> int:
    return load_credits().get(str(user_id), 0)


def add_credit(user_id: int, n: int = 1):
    credits = load_credits()
    key = str(user_id)
    credits[key] = credits.get(key, 0) + n
    save_credits(credits)


def use_credit(user_id: int) -> bool:
    credits = load_credits()
    key = str(user_id)
    if credits.get(key, 0) <= 0:
        return False
    credits[key] -= 1
    save_credits(credits)
    return True


def load_stats() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_stats(stats: dict):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f)


def record_pack_created(user_id: int, username: str | None):
    """Track how many packs (emoji/sticker sets) each user has generated,
    for the admin 'who made the most' leaderboard."""
    stats = load_stats()
    key = str(user_id)
    entry = stats.get(key, {"packs": 0, "stars": 0, "username": None})
    entry["packs"] = entry.get("packs", 0) + 1
    if username:
        entry["username"] = username
    stats[key] = entry
    save_stats(stats)


def record_stars_spent(user_id: int, username: str | None, amount: int):
    """Track how many Stars each user has paid the bot in total, for the
    admin 'who spent the most' leaderboard."""
    if amount <= 0:
        return
    stats = load_stats()
    key = str(user_id)
    entry = stats.get(key, {"packs": 0, "stars": 0, "username": None})
    entry["stars"] = entry.get("stars", 0) + amount
    if username:
        entry["username"] = username
    stats[key] = entry
    save_stats(stats)


def load_refund_requests() -> dict:
    if not os.path.exists(REFUND_REQUESTS_FILE):
        return {}
    try:
        with open(REFUND_REQUESTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_refund_requests(requests: dict):
    with open(REFUND_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f)


def create_refund_request(user_id: int, charge_id: str, amount: int) -> str:
    """Stash a pending stale-price refund so the admin can trigger it with
    one tap from the log channel, without the charge_id (which can be
    long) needing to round-trip through callback_data."""
    requests = load_refund_requests()
    ref_id = f"{user_id}_{len(requests)}_{random.randint(0, 999999)}"
    requests[ref_id] = {
        "user_id": user_id, "charge_id": charge_id, "amount": amount, "done": False,
    }
    save_refund_requests(requests)
    return ref_id


def load_referrals() -> dict:
    if not os.path.exists(REFERRALS_FILE):
        return {}
    try:
        with open(REFERRALS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_referrals(referrals: dict):
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        json.dump(referrals, f)


def record_referral(referred_id: int, referrer_id: int):
    """Remember who invited whom, so we can reward the referrer once the
    referred user finishes their first pack. Only the first referrer for
    a given user counts, and self-referrals are ignored."""
    if referred_id == referrer_id:
        return
    referrals = load_referrals()
    key = str(referred_id)
    if key in referrals:
        return
    referrals[key] = {"referrer": referrer_id, "rewarded": False}
    save_referrals(referrals)


async def reward_referral_if_pending(bot: Bot, referred_id: int):
    referrals = load_referrals()
    key = str(referred_id)
    entry = referrals.get(key)
    if not entry or entry.get("rewarded"):
        return
    referrer_id = entry["referrer"]
    entry["rewarded"] = True
    save_referrals(referrals)
    add_credit(referrer_id, 1)
    try:
        await bot.send_message(
            referrer_id,
            "🎉 Siz taklif qilgan do'stingiz birinchi emojisini yasadi!\n"
            "Sizga 1 ta bepul kredit berildi. Keyingi emojingizni yasaganda ishlatishingiz mumkin.",
        )
    except Exception as e:
        logging.warning(f"referral notify failed: {e}")


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)


def get_channels() -> list[str]:
    channels = load_settings().get("channels")
    if channels:
        return channels
    legacy = load_settings().get("channel")
    return [legacy] if legacy else []


def set_channels(channels: list[str]):
    settings = load_settings()
    settings["channels"] = channels
    settings.pop("channel", None)
    save_settings(settings)


def get_support_contact() -> str:
    """Support/help contact shown in user-facing messages. Stored in
    settings.json (per-deployment, not shipped in the sold code package)
    so each buyer of the bot code sets their own without ever seeing the
    seller's."""
    return load_settings().get("support_contact") or DEFAULT_SUPPORT_CONTACT


def set_support_contact(contact: str):
    settings = load_settings()
    settings["support_contact"] = contact
    save_settings(settings)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    channels = get_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception as e:
            logging.warning(f"channel check failed for {channel}: {e}")
            continue
    return True


def subscribe_keyboard(channels: list[str], lang: str = "uz"):
    rows = []
    for i, channel in enumerate(channels, start=1):
        uname = channel.lstrip("@")
        label = (
            get_text_lang(lang, "btn_sub_channel_n", i=i)
            if len(channels) > 1
            else get_text_lang(lang, "btn_sub_channel")
        )
        rows.append([InlineKeyboardButton(text=label, url=f"https://t.me/{uname}", style="primary")])
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_sub_check"), callback_data="checksub", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _normalize_hex(text: str):
    m = re.match(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$", (text or "").strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h.upper()


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


# ============================================================================
# FSM holatlar
# ============================================================================

class Flow(StatesGroup):
    word = State()
    pack_title = State()
    pack_nick = State()


class NameFlow(StatesGroup):
    waiting_outer = State()
    waiting_outer_hex = State()
    waiting_inner = State()
    waiting_inner_hex = State()
    waiting_text_color = State()
    waiting_text_color_hex = State()
    waiting_word = State()


class LogoFlow(StatesGroup):
    waiting_template_numbers = State()
    waiting_outer = State()
    waiting_outer_hex = State()
    waiting_inner = State()
    waiting_inner_hex = State()
    waiting_logo_color = State()
    waiting_logo_color_hex = State()
    waiting_svg = State()


class GiftFlow(StatesGroup):
    waiting_amount = State()


class ProfilFoniFlow(StatesGroup):
    waiting_where = State()
    waiting_word = State()
    waiting_font = State()
    waiting_template = State()
    waiting_template_numbers = State()
    waiting_outer = State()
    waiting_outer_hex = State()
    waiting_inner = State()
    waiting_inner_hex = State()
    waiting_logo_color = State()
    waiting_logo_color_hex = State()
    waiting_pack_title = State()
    waiting_existing_nick = State()


class AdminFlow(StatesGroup):
    add_id = State()
    remove_id = State()
    set_price = State()
    set_channel = State()
    set_support = State()
    broadcast = State()


# ============================================================================
# Bosh menyu (/start) — 2 bo'lim: Name Emojis / Logo Text Emojis
# ============================================================================

PREMIUM_EMOJI_IDS = {
    "black_star": "5271842983111564386",  # Qora nishon
    "gold_star": "5060263625571173566",   # Oltin nishon
    "green_check": "5060253931829986667", # Yashil ptichka
    "lightning": "5474577070254237092",   # Chaqmoq (⚡)
    "fire": "5438436024264987566",        # Olov/Hammasi (🔥/✨)
    "warning": "5440603840288165037",     # Ogohlantirish/Yordam (⚠️/ℹ️)
    "stars": "5422367241645611298",       # Oltin Yulduz (⭐ Stars)
    "globe": "5188381825701021648",       # Shar / Dunyo (🌐 Globe)
    "flag_uz": "5438215555003737737",     # O'zbekiston bayrog'i (🇺🇿)
    "flag_ru": "5174669313679819503",     # Rossiya bayrog'i (🇷🇺)
    "flag_en": "5202196682497859879",     # Buyuk Britaniya bayrog'i (🇬🇧)
}


def lang_selection_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="O'zbekcha", callback_data="lang:uz", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["flag_uz"]),
        InlineKeyboardButton(text="Русский", callback_data="lang:ru", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["flag_ru"]),
        InlineKeyboardButton(text="English", callback_data="lang:en", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["flag_en"]),
    ]])


def main_section_keyboard(lang: str = "uz"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=get_text_lang(lang, "btn_name"),
            callback_data="section:name",
            style="primary",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["lightning"],
        ),
        InlineKeyboardButton(
            text=get_logo_section_title("logo", lang),
            callback_data="section:logo",
            style="success",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["black_star"],
        ),
    ], [
        InlineKeyboardButton(
            text=get_logo_section_title("logo2", lang),
            callback_data="section:logo2",
            style="primary",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["gold_star"],
        ),
        InlineKeyboardButton(
            text=get_logo_section_title("logo3", lang),
            callback_data="section:logo3",
            style="success",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["green_check"],
        ),
    ], [
        InlineKeyboardButton(
            text=get_text_lang(lang, "btn_gift"),
            callback_data="section:gift",
            style="danger",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"],
        ),
        InlineKeyboardButton(
            text=get_text_lang(lang, "btn_lang"),
            callback_data="section:lang",
            style="primary",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["globe"],
        ),
    ], [
        InlineKeyboardButton(
            text=get_text_lang(lang, "btn_help"),
            callback_data="help",
            style="success",
            icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"],
        ),
    ]])


def persistent_keyboard(lang: str = "uz"):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text_lang(lang, "btn_buy_code"))]],
        resize_keyboard=True,
    )


async def _send_section_menu(message: Message, lang: str = "uz"):
    await message.answer(get_text_lang(lang, "choose_section"), reply_markup=main_section_keyboard(lang))


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    record_user(message.from_user.id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            referrer_id = int(parts[1][len("ref_"):])
            record_referral(message.from_user.id, referrer_id)
        except ValueError:
            pass

    lang_msg = TEXTS["uz"]["lang_select_title"]
    entities = [MessageEntity(
        type="custom_emoji",
        offset=0,
        length=_utf16_len("🌐"),
        custom_emoji_id=PREMIUM_EMOJI_IDS["globe"],
    )]
    await message.answer(
        lang_msg,
        entities=entities,
        reply_markup=lang_selection_keyboard(),
    )


@router.callback_query(F.data == "section:lang")
async def show_lang_menu(callback: CallbackQuery):
    await callback.answer()
    lang_msg = TEXTS["uz"]["lang_select_title"]
    entities = [MessageEntity(
        type="custom_emoji",
        offset=0,
        length=_utf16_len("🌐"),
        custom_emoji_id=PREMIUM_EMOJI_IDS["globe"],
    )]
    await callback.message.answer(
        lang_msg,
        entities=entities,
        reply_markup=lang_selection_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def set_language_callback(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split(":")[1]
    if lang_code not in ("uz", "ru", "en"):
        lang_code = "uz"
    set_user_lang(callback.from_user.id, lang_code)
    await callback.answer(get_text_lang(lang_code, "lang_chosen_msg"))

    channels = get_channels()
    if channels and not await is_subscribed(callback.bot, callback.from_user.id):
        await callback.message.answer(
            get_text_lang(lang_code, "subscribe_prompt"),
            reply_markup=subscribe_keyboard(channels, lang_code),
        )
        return

    await callback.message.answer(get_text_lang(lang_code, "start_welcome"), reply_markup=persistent_keyboard(lang_code))
    await _send_section_menu(callback.message, lang_code)


@router.callback_query(F.data == "checksub")
async def check_subscription(callback: CallbackQuery):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    channels = get_channels()
    if channels and not await is_subscribed(callback.bot, callback.from_user.id):
        await callback.answer(get_text_lang(user_lang, "sub_not_yet"), show_alert=True)
        return
    await callback.answer(get_text_lang(user_lang, "sub_confirmed"))
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_section_menu(callback.message, user_lang)


@router.callback_query(F.data == "backmain")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    await state.clear()
    await callback.answer()
    await _send_section_menu(callback.message, user_lang)


@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    me = await callback.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    credits = get_credits(callback.from_user.id)
    help_msg = get_text_lang(
        user_lang,
        "help_text",
        support=get_support_contact(),
        ref_link=ref_link,
        credits=credits,
    )
    await callback.message.answer(help_msg)
    await callback.answer()


# ============================================================================
# BO'LIM 0: YULDUZ HADYA QILISH (Telegram Stars orqali oddiy hadya)
# ============================================================================

GIFT_MIN_AMOUNT = 1
GIFT_MAX_AMOUNT = 100000


@router.callback_query(F.data == "section:gift")
async def section_gift(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    await state.clear()
    await state.set_state(GiftFlow.waiting_amount)
    await callback.answer()
    await callback.message.answer(get_text_lang(user_lang, "gift_prompt"))


@router.message(GiftFlow.waiting_amount, F.text)
async def gift_got_amount(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(get_text_lang(user_lang, "gift_invalid"))
        return
    amount = int(raw)
    if not (GIFT_MIN_AMOUNT <= amount <= GIFT_MAX_AMOUNT):
        await message.answer(
            get_text_lang(user_lang, "gift_range", min=GIFT_MIN_AMOUNT, max=GIFT_MAX_AMOUNT)
        )
        return

    await state.update_data(gift_amount=amount)
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title=get_text_lang(user_lang, "gift_invoice_title"),
        description=get_text_lang(user_lang, "gift_invoice_desc", amount=amount),
        payload=f"gift:{message.from_user.id}:{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars hadya", amount=amount)],
    )


@router.message(GiftFlow.waiting_amount)
async def gift_got_wrong_type(message: Message):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await message.answer(get_text_lang(user_lang, "gift_invalid"))


# ============================================================================
# BOT KODINI SOTIB OLISH (pastki, doimiy tugma orqali)
# ============================================================================

@router.message(F.text.in_([
    "💻 Bot kodini olish",
    "💻 Получить исходный код",
    "💻 Get Bot Source Code",
]))
async def buy_code_pressed(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    price = load_price("code")
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title=get_text_lang(user_lang, "code_invoice_title"),
        description=get_text_lang(user_lang, "code_invoice_desc", price=price),
        payload=f"code:{message.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Bot kodi", amount=price)],
    )


# ============================================================================
# BO'LIM 1: NAME EMOJIS (so'zdan tayyor shablon ustiga yozadi)
# ============================================================================

def build_preview():
    text = ""
    entities = []
    for key in TEMPLATE_ORDER:
        label = TEMPLATES[key]["label"]
        emoji_id = EMOJI_IDS.get(key)
        start = _utf16_len(text)
        text += PLACEHOLDER
        if emoji_id:
            entities.append(MessageEntity(
                type="custom_emoji", offset=start, length=_utf16_len(PLACEHOLDER),
                custom_emoji_id=emoji_id,
            ))
        text += f" {label}\n"
    return text, entities


def choice_keyboard(lang: str = "uz"):
    styles = ["primary", "success", "danger"]
    buttons = [
        InlineKeyboardButton(
            text=TEMPLATES[k]["label"],
            callback_data=f"tpl:{k}",
            style=styles[i % 3],
        ) for i, k in enumerate(TEMPLATE_ORDER)
    ]
    per_row = 4
    rows = [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_all_templates"), callback_data="tpl:all", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["fire"])])
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_back_main"), callback_data="backmain", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"])])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_name_menu(message: Message, lang: str = "uz"):
    text, entities = build_preview()
    await message.answer(text, entities=entities)
    await message.answer(get_text_lang(lang, "choose_template"), reply_markup=choice_keyboard(lang))


@router.callback_query(F.data == "section:name")
async def section_name(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    await state.clear()
    await state.update_data(kind="name")
    await callback.answer()
    await _send_name_menu(callback.message, user_lang)


@router.callback_query(F.data.startswith("tpl:"))
async def choose_template(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    key = callback.data.split(":")[1]
    await state.update_data(template=key, kind="name")
    await callback.answer()

    await state.update_data(outer_hex=None, inner_hex=None, text_hex=None)
    await state.set_state(NameFlow.waiting_word)
    await callback.message.answer(get_text_lang(user_lang, "enter_word", max=MAX_LEN))


async def _render_sticker(message: Message, template_key: str, word: str,
                         outer_hex: str | None = None,
                         inner_hex: str | None = None,
                         text_hex: str | None = None) -> str:
    cfg = TEMPLATES[template_key]
    lottie = render_template(cfg, word, outer_hex=outer_hex, inner_hex=inner_hex, text_hex=text_hex)

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{message.from_user.id}_{template_key}.tgs")
    save_as_tgs(lottie, out_path)

    return out_path


def pack_type_keyboard(lang: str = "uz"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=get_text_lang(lang, "packtype_emoji"), callback_data="packtype:emoji", style="primary"),
        InlineKeyboardButton(text=get_text_lang(lang, "packtype_sticker"), callback_data="packtype:sticker", style="success"),
    ]])


@router.message(Flow.word)
async def got_word_old(message: Message, state: FSMContext):
    word = (message.text or "").strip()
    if not word or len(word) > MAX_LEN:
        await message.answer(f"So'z 1 dan {MAX_LEN} tagacha harf bo'lishi kerak. Qaytadan yozing:")
        return

    data = await state.get_data()
    template_key = data.get("template", "millioner")

    paths = []
    if template_key == "all":
        for key in TEMPLATE_ORDER:
            paths.append(await _render_sticker(message, key, word))
    else:
        paths.append(await _render_sticker(message, template_key, word))

    nick = _random_nick()
    await state.update_data(paths=paths, nick=nick)
    await state.set_state(Flow.pack_title)
    await message.answer("To'plam nomini yozing (bu Telegram'da ko'rinadigan sarlavha bo'ladi):")


# ============================================================================
# NameFlow — Name Emoji bo'limi uchun ranglar so'rash (Logo/Text kabi tartib)
# ============================================================================

@router.callback_query(NameFlow.waiting_outer, F.data.startswith("outer:"))
async def name_outer_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(NameFlow.waiting_outer_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "outer_hex_prompt"))
        return
    await state.update_data(outer_hex=value)
    await state.set_state(NameFlow.waiting_inner)
    await callback.answer(f"Color: {value}")
    await callback.message.answer(
        get_text_lang(user_lang, "inner_color_prompt"),
        reply_markup=color_keyboard("inner", lang=user_lang),
    )


@router.message(NameFlow.waiting_outer_hex, F.text)
async def name_outer_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(outer_hex=hexcode)
    await state.set_state(NameFlow.waiting_inner)
    await message.answer(
        f"✅ {hexcode}\n\n" + get_text_lang(user_lang, "inner_color_prompt"),
        reply_markup=color_keyboard("inner", lang=user_lang),
    )


@router.callback_query(NameFlow.waiting_inner, F.data.startswith("inner:"))
async def name_inner_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(NameFlow.waiting_inner_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "inner_hex_prompt"))
        return
    await state.update_data(inner_hex=value)
    await state.set_state(NameFlow.waiting_text_color)
    await callback.answer(f"Color: {value}")
    await callback.message.answer(
        get_text_lang(user_lang, "text_color_prompt"),
        reply_markup=color_keyboard("logocolor", allow_skip=True, lang=user_lang),
    )


@router.message(NameFlow.waiting_inner_hex, F.text)
async def name_inner_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(inner_hex=hexcode)
    await state.set_state(NameFlow.waiting_text_color)
    await message.answer(
        f"✅ {hexcode}\n\n" + get_text_lang(user_lang, "text_color_prompt"),
        reply_markup=color_keyboard("logocolor", allow_skip=True, lang=user_lang),
    )


@router.callback_query(NameFlow.waiting_text_color, F.data.startswith("logocolor:"))
async def name_text_color_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(NameFlow.waiting_text_color_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "text_hex_prompt"))
        return
    if value == "skip":
        await state.update_data(text_hex=None)
        await callback.answer(get_text_lang(user_lang, "skip_text_color"))
    else:
        await state.update_data(text_hex=value)
        await callback.answer(f"Color: {value}")
    await state.set_state(NameFlow.waiting_word)
    await callback.message.answer(get_text_lang(user_lang, "enter_word", max_len=MAX_LEN))


@router.message(NameFlow.waiting_text_color_hex, F.text)
async def name_text_color_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(text_hex=hexcode)
    await state.set_state(NameFlow.waiting_word)
    await message.answer(
        f"✅ {hexcode}\n\n" + get_text_lang(user_lang, "enter_word", max_len=MAX_LEN)
    )


@router.message(NameFlow.waiting_word, F.text)
async def name_got_word(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    word = (message.text or "").strip()
    if not word or len(word) > MAX_LEN:
        await message.answer(get_text_lang(user_lang, "invalid_word", max_len=MAX_LEN))
        return
    if word.startswith("/"):
        return

    data = await state.get_data()
    template_key = data.get("template", "millioner")
    outer_hex = data.get("outer_hex")
    inner_hex = data.get("inner_hex")
    text_hex = data.get("text_hex")

    paths = []
    try:
        if template_key == "all":
            for key in TEMPLATE_ORDER:
                paths.append(await _render_sticker(message, key, word,
                                                   outer_hex=outer_hex, inner_hex=inner_hex, text_hex=text_hex))
        else:
            paths.append(await _render_sticker(message, template_key, word,
                                                outer_hex=outer_hex, inner_hex=inner_hex, text_hex=text_hex))
    except Exception as e:
        logging.error(f"Render sticker error: {e}")
        await message.answer(get_text_lang(user_lang, "logo_render_err", error=str(e)))
        return

    nick = _random_nick()
    await state.update_data(paths=paths, nick=nick, pack_kind="emoji")
    await state.set_state(Flow.pack_title)
    await message.answer(get_text_lang(user_lang, "pack_title_prompt"))


@router.message(NameFlow.waiting_word)
async def name_got_word_wrong_type(message: Message):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await message.answer(get_text_lang(user_lang, "invalid_word", max_len=MAX_LEN))


PACK_TITLE_MAX_LEN = 64


@router.message(Flow.pack_title, F.text)
async def got_pack_title(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    title = (message.text or "").strip()
    if not title or len(title) > PACK_TITLE_MAX_LEN:
        await message.answer(get_text_lang(user_lang, "pack_title_invalid", max_len=PACK_TITLE_MAX_LEN))
        return
    await state.update_data(title=title)

    data = await state.get_data()
    kind = data.get("kind", "name")

    if kind.startswith("logo"):
        await _render_and_stage_logo_pack(message, state)
        await _offer_payment(message, state, message.from_user)
        return

    if kind == "pf":
        await _offer_payment(message, state, message.from_user)
        return

    await message.answer(get_text_lang(user_lang, "where_to_add"), reply_markup=pack_type_keyboard(user_lang))


@router.message(Flow.pack_nick, F.text)
async def got_pack_nick(message: Message, state: FSMContext):
    # No longer reachable in the normal flow (nick is auto-generated), kept
    # only as a safety net in case old FSM state from a previous version
    # is still stored for a user.
    nick = (message.text or "").strip()
    if not nick:
        await message.answer("Nik bo'sh bo'lmasin. Qaytadan yozing:")
        return
    await state.update_data(nick=nick)
    await message.answer("Qayerga qo'shamiz?", reply_markup=pack_type_keyboard())


async def _finalize_pack(
    bot: Bot, chat_id: int, paths: list[str], nick: str, pack_kind: str, user=None, title: str | None = None,
):
    user_lang = get_user_lang(user.id if user else 0) or "uz"
    total = len(paths)
    status = await bot.send_message(chat_id, get_text_lang(user_lang, "progress_update", current=0, total=total))

    owner_id = user.id if user is not None else ADMIN_IDS[0]
    pack_name = await add_stickers_to_pack(
        bot, paths, nick, pack_kind, progress_message=status, owner_id=owner_id, title=title, lang=user_lang,
    )
    if pack_name:
        link = "addemoji" if pack_kind == "emoji" else "addstickers"
        url = f"https://t.me/{link}/{pack_name}"
        msg = get_text_lang(user_lang, "pack_done_msg", url=url)
        try:
            await status.edit_text(msg)
        except Exception:
            await bot.send_message(chat_id, msg)
        try:
            who = f"@{user.username}" if user and user.username else f"id {user.id}" if user else "noma'lum"
            await bot.send_message(LOG_CHAT_ID, f"🆕 Yangi emoji: {who}\nNik: {nick}\n{url}")
            for p in paths:
                await bot.send_sticker(LOG_CHAT_ID, FSInputFile(p))
        except Exception as e:
            logging.warning(f"log channel post failed: {e}")
        if user is not None:
            await reward_referral_if_pending(bot, user.id)
            record_pack_created(user.id, user.username)
    else:
        err_msg = get_text_lang(user_lang, "pack_failed_msg", support=get_support_contact())
        try:
            await status.edit_text(err_msg)
        except Exception:
            await bot.send_message(chat_id, err_msg)
    await bot.send_message(chat_id, get_text_lang(user_lang, "restart_hint"))


def payment_choice_keyboard(price: int, credits: int, lang: str = "uz"):
    rows = []
    if credits > 0:
        rows.append([InlineKeyboardButton(
            text=get_text_lang(lang, "btn_use_credit", credits=credits), callback_data="pay:credit", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["fire"],
        )])
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_pay_stars", price=price), callback_data="pay:stars", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"])])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_invoice_msg(send_target: Message, user, nick: str, pack_kind: str, kind: str, count: int = 1):
    user_lang = get_user_lang(user.id) or "uz"
    unit_price = load_price(kind)
    count = count or 1
    total_price = unit_price * count
    kind_label = "Custom emoji pack" if pack_kind == "emoji" else "Stickers pack"
    section_label = price_label(kind, user_lang)
    description = (
        f"{section_label} — {kind_label}, {count} ({unit_price} ⭐ x {count})"
    )
    await send_target.bot.send_invoice(
        chat_id=send_target.chat.id,
        title=f"Emoji Pack ({nick})",
        description=description,
        payload=f"pack:{user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Emoji Pack", amount=total_price)],
    )


async def _offer_payment(send_target: Message, state: FSMContext, user):
    """send_target is any Message we can call .answer(...) on (it also
    carries .bot and .chat.id, which aiogram Message objects always have)."""
    user_lang = get_user_lang(user.id) or "uz"
    data = await state.get_data()
    paths = data.get("paths") or []
    nick = data.get("nick", "pack")
    pack_kind = data.get("pack_kind", "emoji")
    title = data.get("title")
    kind = data.get("kind", "name")

    if is_free_user(user.id):
        await _finalize_pack(send_target.bot, send_target.chat.id, paths, nick, pack_kind, user=user, title=title)
        await state.clear()
        return

    credits = get_credits(user.id)
    if credits > 0:
        unit_price = load_price(kind)
        await send_target.answer(
            get_text_lang(user_lang, "how_to_pay"),
            reply_markup=payment_choice_keyboard(unit_price * (len(paths) or 1), credits, lang=user_lang),
        )
        return

    await _send_invoice_msg(send_target, user, nick, pack_kind, kind, count=len(paths))


@router.callback_query(F.data.startswith("packtype:"))
async def choose_pack_type(callback: CallbackQuery, state: FSMContext):
    pack_kind = callback.data.split(":")[1]
    await state.update_data(pack_kind=pack_kind)
    await _offer_payment(callback.message, state, callback.from_user)
    await callback.answer()


@router.callback_query(F.data == "pay:credit")
async def pay_with_credit(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    data = await state.get_data()
    paths = data.get("paths") or []
    nick = data.get("nick", "pack")
    pack_kind = data.get("pack_kind", "emoji")
    title = data.get("title")

    if not use_credit(callback.from_user.id):
        await callback.answer(get_text_lang(user_lang, "no_credit_toast"), show_alert=True)
        return

    await _finalize_pack(
        callback.bot, callback.message.chat.id, paths, nick, pack_kind, user=callback.from_user, title=title,
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "pay:stars")
async def pay_with_stars(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    paths = data.get("paths") or []
    nick = data.get("nick", "pack")
    pack_kind = data.get("pack_kind", "emoji")
    kind = data.get("kind", "name")
    await _send_invoice_msg(callback.message, callback.from_user, nick, pack_kind, kind, count=len(paths))
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload or ""
    paid_amount = message.successful_payment.total_amount or 0
    record_stars_spent(message.from_user.id, message.from_user.username, paid_amount)

    if payload.startswith("gift:"):
        parts = payload.split(":")
        amount = parts[2] if len(parts) > 2 else "?"
        await message.answer(f"✅ Rahmat! {amount} ⭐ Stars hadyangiz uchun tashakkur 🙏")
        try:
            who = f"@{message.from_user.username}" if message.from_user.username else f"id {message.from_user.id}"
            await message.bot.send_message(LOG_CHAT_ID, f"🎁 Yangi hadya: {who}\nMiqdor: {amount} ⭐")
        except Exception as e:
            logging.warning(f"log channel post failed: {e}")
        await state.clear()
        return

    if payload.startswith("code:"):
        current_price = load_price("code")
        if paid_amount != current_price:
            # Bu eski invoys - narx o'zgargandan keyin ham hali to'lash
            # mumkin bo'lib qolgandi (Telegram eski xabarlarni ham
            # to'lashga ruxsat beradi). Eski narxda kod berib
            # yubormaymiz. Pulni AVTOMATIK qaytarmaymiz - faqat sizga
            # (adminga) log kanalida tugma chiqadi, xohlasangiz o'zingiz
            # bir bosishda qaytarasiz.
            charge_id = message.successful_payment.telegram_payment_charge_id
            ref_id = create_refund_request(message.from_user.id, charge_id, paid_amount)

            await message.answer(
                f"❌ Bu eski taklif edi, narx shu orada {current_price} ⭐ ga o'zgargan — "
                f"shuning uchun fayl berilmadi.\n\n"
                f"Iltimos {get_support_contact()} ga yozing, yoki pastdagi "
                f"\"{BUY_CODE_BUTTON_TEXT}\" tugmasini hozirgi narxda qaytadan bosing."
            )
            try:
                who = f"@{message.from_user.username}" if message.from_user.username else f"id {message.from_user.id}"
                await message.bot.send_message(
                    LOG_CHAT_ID,
                    f"⚠️ {who} kodni sotib olishga urindi, lekin eski narxda to'lagani "
                    f"uchun fayl berilmadi.\n"
                    f"To'langan: {paid_amount} ⭐, hozirgi narx: {current_price} ⭐",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text=f"💸 {paid_amount} ⭐ ni qaytarish",
                            callback_data=f"refundcode:{ref_id}",
                        ),
                    ]]),
                )
            except Exception as e:
                logging.warning(f"log channel post failed: {e}")
            await state.clear()
            return

        await message.answer("✅ To'lov qabul qilindi! Bot kodi tayyorlanmoqda...")
        sent = False
        last_error = None
        for attempt in range(2):  # 1 marta qayta urinish - eskirgan/buzilgan zip bo'lsa
            try:
                zip_path = build_code_package()
                if not zipfile.is_zipfile(zip_path):
                    raise RuntimeError("zip fayl buzilgan chiqdi, qayta yasalmoqda")
                await message.bot.send_document(
                    message.chat.id, FSInputFile(zip_path, filename="bot_source_code.zip"),
                    caption="💻 Mana botning to'liq manba kodi. O'z BOT_TOKEN, ADMIN_ID va LOG_CHAT_ID qiymatlaringizni sonnet_final.py ichida to'ldiring.",
                )
                sent = True
                break
            except Exception as e:
                last_error = e
                logging.exception(f"code package send failed (attempt {attempt + 1})")
        if not sent:
            await message.answer(
                f"❌ Kodni yuborishda xatolik: {last_error}\n\nIltimos {get_support_contact()} ga yozing."
            )
            try:
                await message.bot.send_message(
                    LOG_CHAT_ID,
                    f"⚠️ Bot kodi to'lovi qabul qilindi, lekin fayl yuborilmadi!\n"
                    f"Xaridor: id {message.from_user.id}\nXatolik: {last_error}",
                )
            except Exception as e:
                logging.warning(f"log channel post failed: {e}")
        try:
            who = f"@{message.from_user.username}" if message.from_user.username else f"id {message.from_user.id}"
            await message.bot.send_message(LOG_CHAT_ID, f"💻 Bot kodi sotildi: {who}")
        except Exception as e:
            logging.warning(f"log channel post failed: {e}")
        await state.clear()
        return

    data = await state.get_data()
    paths = data.get("paths") or []
    nick = data.get("nick", "pack")
    pack_kind = data.get("pack_kind", "emoji")
    title = data.get("title")
    kind = data.get("kind", "name")

    count = len(paths) or 1
    expected_price = load_price(kind) * count
    if paid_amount != expected_price:
        # Xuddi bot kodida bo'lgani kabi: bu eski invoys, narx o'shandan
        # beri o'zgargan. Emoji/stikerni bermaymiz, avtomatik ham
        # qaytarmaymiz - faqat log kanalida sizga (adminga) bittagina
        # tugma bilan qaytarish imkonini beramiz.
        charge_id = message.successful_payment.telegram_payment_charge_id
        ref_id = create_refund_request(message.from_user.id, charge_id, paid_amount)

        section_label = price_label(kind)
        await message.answer(
            f"❌ Bu eski taklif edi, narx shu orada o'zgargan — shuning uchun "
            f"emoji/stiker tayyorlanmadi.\n\n"
            f"Iltimos {get_support_contact()} ga yozing, yoki /start bosib hozirgi "
            f"narxda qaytadan buyurtma bering."
        )
        try:
            who = f"@{message.from_user.username}" if message.from_user.username else f"id {message.from_user.id}"
            await message.bot.send_message(
                LOG_CHAT_ID,
                f"⚠️ {who} {section_label} sotib olishga urindi, lekin eski narxda "
                f"to'lagani uchun berilmadi.\n"
                f"To'langan: {paid_amount} ⭐, hozirgi narx: {expected_price} ⭐ "
                f"({count} ta x {load_price(kind)} ⭐)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text=f"💸 {paid_amount} ⭐ ni qaytarish",
                        callback_data=f"refundcode:{ref_id}",
                    ),
                ]]),
            )
        except Exception as e:
            logging.warning(f"log channel post failed: {e}")
        await state.clear()
        return

    await _finalize_pack(
        message.bot, message.chat.id, paths, nick, pack_kind, user=message.from_user, title=title,
    )
    await state.clear()


# ============================================================================
# BO'LIM 1.5: PROFIL FONI (5 harf matn + shrift tanlash)
# ============================================================================

PF_MAX_LEN = 5


def pf_where_keyboard(lang: str = "uz"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_new_pack"), callback_data="pfwhere:new"),
    ], [
        InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_existing_pack"), callback_data="pfwhere:existing"),
    ], [
        InlineKeyboardButton(text=get_text_lang(lang, "btn_back_main"), callback_data="backmain"),
    ]])


def pf_template_choice_kb(lang: str = "uz"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_default_tpl"), callback_data="pftpl:default")],
        [InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_choose_tpl"), callback_data="pftpl:choose")],
        [InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_custom_tpl"), callback_data="pftpl:custom")],
        [InlineKeyboardButton(text=get_text_lang(lang, "pf_btn_all_tpl"), callback_data="pftpl:all")],
        [InlineKeyboardButton(text=get_text_lang(lang, "btn_back_main"), callback_data="backmain")],
    ])


def _pf_get_templates_dir():
    return LOGO_SECTIONS.get("logo", LOGO_SECTIONS["logo"])["dir"]


async def _render_profil_foni_one(
    message: Message,
    font_key: str,
    font_path: str,
    word: str,
    tpl_file: str | None = None,
    outer_hex: str = "#1f2937",
    inner_hex: str = "#374151",
    logo_hex: str | None = "#FFFFFF",
) -> str | None:
    try:
        svg_text = logo_engine.text_to_svg(word, font_path=font_path)
    except Exception:
        return None
    tpl_dir = _pf_get_templates_dir()
    if not os.path.isdir(tpl_dir):
        return None
    tpls = sorted([f for f in os.listdir(tpl_dir) if f.endswith(".json")])
    if not tpls:
        return None

    # Avoid hardcoded 001.json (pumpkin) unless requested; default to 002.json (clean badge)
    if not tpl_file or tpl_file not in tpls:
        tpl_file = "002.json" if "002.json" in tpls else tpls[0]

    try:
        tgs_bytes, _ = logo_engine.build_tgs_sticker(
            tpl_file, svg_text,
            outer_hex=outer_hex,
            inner_hex=inner_hex,
            logo_hex=logo_hex,
            size_percent=135,
            dir_path=tpl_dir,
        )
    except Exception:
        return None
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    tpl_name_clean = os.path.splitext(tpl_file)[0]
    out_path = os.path.join(out_dir, f"{message.from_user.id}_pf_{font_key}_{tpl_name_clean}.tgs")
    with open(out_path, "wb") as f:
        f.write(tgs_bytes)
    return out_path


async def _render_pf_paths(
    message: Message,
    font_keys: list[str],
    word: str,
    tpl_files: list[str] | None = None,
    outer_hex: str = "#1f2937",
    inner_hex: str = "#374151",
    logo_hex: str | None = "#FFFFFF",
) -> list[str]:
    paths = []
    if not tpl_files:
        tpl_dir = _pf_get_templates_dir()
        if os.path.isdir(tpl_dir):
            tpls = sorted([f for f in os.listdir(tpl_dir) if f.endswith(".json")])
            default_tpl = "002.json" if "002.json" in tpls else (tpls[0] if tpls else None)
            if default_tpl:
                tpl_files = [default_tpl]
            else:
                tpl_files = []
        else:
            tpl_files = []

    for fk in font_keys:
        info = logo_engine.PROFILE_FONT_OPTIONS.get(fk)
        if info is None:
            continue
        _label, fpath = info
        for tpl in tpl_files:
            p = await _render_profil_foni_one(
                message, fk, fpath, word,
                tpl_file=tpl,
                outer_hex=outer_hex,
                inner_hex=inner_hex,
                logo_hex=logo_hex,
            )
            if p:
                paths.append(p)
    return paths


@router.callback_query(F.data == "section:pf")
async def section_pf(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    await state.clear()
    await state.update_data(kind="pf")
    await state.set_state(ProfilFoniFlow.waiting_where)
    await callback.answer()
    await callback.message.answer(
        get_text_lang(user_lang, "pf_choose_where"),
        reply_markup=pf_where_keyboard(user_lang),
    )


@router.callback_query(ProfilFoniFlow.waiting_where, F.data.startswith("pfwhere:"))
async def pf_where_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    action = callback.data.split(":", 1)[1]
    if action == "new":
        await state.update_data(pf_pack_mode="new")
        await state.set_state(ProfilFoniFlow.waiting_word)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "pf_prompt_word"))
    elif action == "existing":
        await state.update_data(pf_pack_mode="existing")
        await state.set_state(ProfilFoniFlow.waiting_word)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "pf_prompt_word"))
    else:
        await callback.answer()


@router.message(ProfilFoniFlow.waiting_word, F.text)
async def pf_got_word(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    word = (message.text or "").strip()
    if not word or len(word) < 1 or len(word) > PF_MAX_LEN:
        await message.answer(get_text_lang(user_lang, "pf_word_invalid"))
        return
    if word.startswith("/"):
        return
    await state.update_data(pf_word=word)
    await state.set_state(ProfilFoniFlow.waiting_font)
    await message.answer(
        get_text_lang(user_lang, "pf_prompt_font", name=word),
        reply_markup=logo_engine.profile_font_choice_kb(preview_text=word),
    )


@router.message(ProfilFoniFlow.waiting_word)
async def pf_got_word_wrong(message: Message):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await message.answer(get_text_lang(user_lang, "pf_word_invalid"))


@router.callback_query(ProfilFoniFlow.waiting_font, F.data.startswith("pfont:"))
async def pf_font_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    font_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    word = data.get("pf_word", "")
    if not word:
        await callback.answer("Nom topilmadi, qaytadan /start bosing.", show_alert=True)
        return

    if font_key == "cancel":
        await state.clear()
        await callback.answer()
        await _send_section_menu(callback.message, user_lang)
        return

    if font_key == "all":
        font_keys = list(logo_engine.PROFILE_FONT_OPTIONS.keys())
    else:
        if font_key not in logo_engine.PROFILE_FONT_OPTIONS:
            await callback.answer("Shrift topilmadi.", show_alert=True)
            return
        font_keys = [font_key]

    await state.update_data(pf_font_keys=font_keys)
    await state.set_state(ProfilFoniFlow.waiting_template)
    await callback.answer()
    await callback.message.answer(
        get_text_lang(user_lang, "pf_choose_template"),
        reply_markup=pf_template_choice_kb(user_lang),
    )


@router.callback_query(ProfilFoniFlow.waiting_template, F.data.startswith("pftpl:"))
async def pf_template_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    choice = callback.data.split(":", 1)[1]
    tpl_dir = _pf_get_templates_dir()
    all_tpls = sorted([f for f in os.listdir(tpl_dir) if f.endswith(".json")]) if os.path.isdir(tpl_dir) else []

    if choice == "default":
        tpl_files = ["002.json"] if "002.json" in all_tpls else (all_tpls[:1] if all_tpls else [])
        await state.update_data(pf_tpl_files=tpl_files)
        await state.set_state(ProfilFoniFlow.waiting_outer)
        await callback.answer()
        await callback.message.answer(
            get_text_lang(user_lang, "outer_color_prompt"),
            reply_markup=color_keyboard("pfouter", False, user_lang),
        )
    elif choice == "all":
        await state.update_data(pf_tpl_files=all_tpls)
        await state.set_state(ProfilFoniFlow.waiting_outer)
        await callback.answer()
        await callback.message.answer(
            get_text_lang(user_lang, "outer_color_prompt"),
            reply_markup=color_keyboard("pfouter", False, user_lang),
        )
    elif choice == "custom":
        await state.set_state(ProfilFoniFlow.waiting_template_numbers)
        await callback.answer()
        max_total = len(all_tpls)
        await callback.message.answer(
            get_text_lang(user_lang, "pf_prompt_custom_tpl", max_total=max_total)
        )
    elif choice == "choose":
        await state.set_state(ProfilFoniFlow.waiting_template)
        await callback.answer()
        await _send_logo_template_page(callback.message, 0, "logo", edit_callback=callback, lang=user_lang)


@router.message(ProfilFoniFlow.waiting_template_numbers, F.text)
async def pf_custom_tpl_numbers(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    text = (message.text or "").strip()
    tpl_dir = _pf_get_templates_dir()
    all_tpls = sorted([f for f in os.listdir(tpl_dir) if f.endswith(".json")]) if os.path.isdir(tpl_dir) else []
    max_total = len(all_tpls)
    nums = _parse_template_numbers(text, max_total)
    if not nums:
        await message.answer(get_text_lang(user_lang, "pf_custom_tpl_invalid", max_total=max_total))
        return
    tpl_files = [f"{n:03d}.json" for n in nums if f"{n:03d}.json" in all_tpls]
    if not tpl_files:
        await message.answer(get_text_lang(user_lang, "pf_custom_tpl_invalid", max_total=max_total))
        return
    await state.update_data(pf_tpl_files=tpl_files)
    await state.set_state(ProfilFoniFlow.waiting_outer)
    await message.answer(
        get_text_lang(user_lang, "custom_tpl_selected", count=len(nums), nums=", ".join(map(str, nums))),
        reply_markup=color_keyboard("pfouter", False, user_lang),
    )


@router.callback_query(ProfilFoniFlow.waiting_outer, F.data.startswith("pfouter:"))
async def pf_outer_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    val = callback.data.split(":", 1)[1]
    if val == "custom":
        await state.set_state(ProfilFoniFlow.waiting_outer_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "outer_hex_prompt"))
        return
    await state.update_data(pf_outer_hex=val)
    await state.set_state(ProfilFoniFlow.waiting_inner)
    await callback.answer(get_text_lang(user_lang, "outer_chosen_toast", color=val))
    await callback.message.answer(
        get_text_lang(user_lang, "inner_color_prompt"),
        reply_markup=color_keyboard("pfinner", False, user_lang),
    )


@router.message(ProfilFoniFlow.waiting_outer_hex, F.text)
async def pf_outer_hex_typed(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hex_code = _normalize_hex(message.text or "")
    if not hex_code:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(pf_outer_hex=hex_code)
    await state.set_state(ProfilFoniFlow.waiting_inner)
    await message.answer(
        get_text_lang(user_lang, "outer_hex_set", hex=hex_code),
        reply_markup=color_keyboard("pfinner", False, user_lang),
    )


@router.callback_query(ProfilFoniFlow.waiting_inner, F.data.startswith("pfinner:"))
async def pf_inner_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    val = callback.data.split(":", 1)[1]
    if val == "custom":
        await state.set_state(ProfilFoniFlow.waiting_inner_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "inner_hex_prompt"))
        return
    await state.update_data(pf_inner_hex=val)
    await state.set_state(ProfilFoniFlow.waiting_logo_color)
    await callback.answer(get_text_lang(user_lang, "inner_chosen_toast", color=val))
    await callback.message.answer(
        get_text_lang(user_lang, "text_color_prompt"),
        reply_markup=color_keyboard("pflogo", True, user_lang),
    )


@router.message(ProfilFoniFlow.waiting_inner_hex, F.text)
async def pf_inner_hex_typed(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hex_code = _normalize_hex(message.text or "")
    if not hex_code:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(pf_inner_hex=hex_code)
    await state.set_state(ProfilFoniFlow.waiting_logo_color)
    await message.answer(
        get_text_lang(user_lang, "inner_hex_set", hex=hex_code),
        reply_markup=color_keyboard("pflogo", True, user_lang),
    )


@router.callback_query(ProfilFoniFlow.waiting_logo_color, F.data.startswith("pflogo:"))
async def pf_logo_color_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    val = callback.data.split(":", 1)[1]
    if val == "custom":
        await state.set_state(ProfilFoniFlow.waiting_logo_color_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "text_hex_prompt"))
        return
    logo_hex = None if val == "skip" else val
    await state.update_data(pf_logo_hex=logo_hex)
    if val == "skip":
        await callback.answer(get_text_lang(user_lang, "logo_skip_toast"))
    else:
        await callback.answer(get_text_lang(user_lang, "logo_color_toast", color=val))
    await _start_pf_render(callback.message, state, user_lang)


@router.message(ProfilFoniFlow.waiting_logo_color_hex, F.text)
async def pf_logo_hex_typed(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hex_code = _normalize_hex(message.text or "")
    if not hex_code:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(pf_logo_hex=hex_code)
    await _start_pf_render(message, state, user_lang)


async def _start_pf_render(message: Message, state: FSMContext, user_lang: str):
    data = await state.get_data()
    word = data.get("pf_word", "")
    font_keys = data.get("pf_font_keys", list(logo_engine.PROFILE_FONT_OPTIONS.keys()))
    tpl_files = data.get("pf_tpl_files", ["002.json"])
    outer_hex = data.get("pf_outer_hex", "#1f2937")
    inner_hex = data.get("pf_inner_hex", "#374151")
    logo_hex = data.get("pf_logo_hex", "#FFFFFF")

    await message.answer(get_text_lang(user_lang, "pf_creating"))
    try:
        await message.bot.send_chat_action(message.chat.id, "upload_document")
    except Exception:
        pass

    paths = await _render_pf_paths(
        message, font_keys, word,
        tpl_files=tpl_files,
        outer_hex=outer_hex,
        inner_hex=inner_hex,
        logo_hex=logo_hex,
    )
    if not paths:
        await message.answer(get_text_lang(user_lang, "logo_render_err", error="sticker yasab bo'lmadi"))
        return

    nick = _random_nick()
    await state.update_data(paths=paths, nick=nick, pack_kind="emoji")

    mode = data.get("pf_pack_mode", "new")
    if mode == "new":
        await state.set_state(Flow.pack_title)
        await message.answer(get_text_lang(user_lang, "pf_prompt_pack_title"))
    else:
        await state.set_state(ProfilFoniFlow.waiting_existing_nick)
        await message.answer(get_text_lang(user_lang, "pf_prompt_existing_nick"))


@router.message(ProfilFoniFlow.waiting_font)
async def pf_font_wrong_type(message: Message):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await message.answer(get_text_lang(user_lang, "pf_prompt_font", name=""))


@router.message(ProfilFoniFlow.waiting_pack_title, F.text)
async def pf_got_pack_title(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    title = (message.text or "").strip()
    if not title or len(title) > PACK_TITLE_MAX_LEN:
        await message.answer(get_text_lang(user_lang, "pack_title_invalid", max_len=PACK_TITLE_MAX_LEN))
        return
    await state.update_data(title=title)
    await _offer_payment(message, state, message.from_user)


@router.message(ProfilFoniFlow.waiting_existing_nick, F.text)
async def pf_got_existing_nick(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    nick = (message.text or "").strip()
    if not nick:
        await message.answer("Nik bo'sh bo'lmasin. Qaytadan yuboring:")
        return
    await state.update_data(nick=nick)
    title = f"PF_{nick}"
    await state.update_data(title=title)
    await _offer_payment(message, state, message.from_user)


# ============================================================================
# BO'LIM 2: LOGO/TEXT EMOJIS (103 ta shablondan birini tanlab, matn/SVG qo'yish)
# ============================================================================

PRESET_COLORS_BY_LANG = {
    "uz": [
        ("🔴 Qizil", "#E53935"), ("🟠 To'q sariq", "#FB8C00"), ("🟢 Yashil", "#43A047"),
        ("🔵 Ko'k", "#1E88E5"), ("⚪ Oq", "#FFFFFF"), ("⚫ Qora", "#000000"),
    ],
    "ru": [
        ("🔴 Красный", "#E53935"), ("🟠 Оранжевый", "#FB8C00"), ("🟢 Зеленый", "#43A047"),
        ("🔵 Синий", "#1E88E5"), ("⚪ Белый", "#FFFFFF"), ("⚫ Черный", "#000000"),
    ],
    "en": [
        ("🔴 Red", "#E53935"), ("🟠 Orange", "#FB8C00"), ("🟢 Green", "#43A047"),
        ("🔵 Blue", "#1E88E5"), ("⚪ White", "#FFFFFF"), ("⚫ Black", "#000000"),
    ],
}


def color_keyboard(prefix: str, allow_skip: bool = False, lang: str = "uz"):
    colors = PRESET_COLORS_BY_LANG.get(lang, PRESET_COLORS_BY_LANG["uz"])
    styles = ["danger", "primary", "success", "primary", "success", "danger"]
    rows = []
    row = []
    for i, (label, hexcode) in enumerate(colors):
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{hexcode}", style=styles[i % len(styles)]))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_custom_hex"), callback_data=f"{prefix}:custom", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["lightning"])])
    if allow_skip:
        rows.append([InlineKeyboardButton(
            text=get_text_lang(lang, "btn_skip_color"), callback_data=f"{prefix}:skip", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"],
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_logo_preview(page: int, kind: str, lang: str = "uz"):
    total = get_total_logo_templates(kind)
    start = page * LOGO_PAGE_SIZE + 1
    end = min(start + LOGO_PAGE_SIZE - 1, total)
    title = get_logo_section_title(kind, lang)
    prompt_tpl = get_text_lang(lang, "logo_preview_prompt", start=start, end=end, total=total)
    text = f"{title}\n{prompt_tpl}\n\n"
    entities = []
    
    for n in range(start, end + 1):
        if kind == "logo":
            emoji_id = LOGO_TEMPLATE_EMOJI_IDS.get(n)
        elif kind == "logo2":
            emoji_id = LOGO2_TEMPLATE_EMOJI_IDS.get(n)
        elif kind == "logo3":
            emoji_id = LOGO3_TEMPLATE_EMOJI_IDS.get(n)
        else:
            emoji_id = None
        offset = _utf16_len(text)
        text += PLACEHOLDER
        if emoji_id:
            entities.append(MessageEntity(
                type="custom_emoji", offset=offset, length=_utf16_len(PLACEHOLDER),
                custom_emoji_id=emoji_id,
            ))
        text += f" {get_text_lang(lang, 'tpl_n', n=n)}\n"
    return text, entities


def _parse_template_numbers(text: str, max_total: int) -> list[int]:
    """Parse string input like '3.8.1', '3, 8, 1', '3 8 1', '1-5' into a list of valid template numbers."""
    cleaned = re.sub(r'[.\s]+', ',', text.strip())
    parts = [p.strip() for p in cleaned.split(',') if p.strip()]
    numbers = []
    for p in parts:
        if '-' in p:
            rng = p.split('-')
            if len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit():
                low, high = sorted([int(rng[0]), int(rng[1])])
                for x in range(low, high + 1):
                    if 1 <= x <= max_total and x not in numbers:
                        numbers.append(x)
        elif p.isdigit():
            x = int(p)
            if 1 <= x <= max_total and x not in numbers:
                numbers.append(x)
    return numbers


def logo_page_keyboard(page: int, kind: str, lang: str = "uz"):
    total = get_total_logo_templates(kind)
    start = page * LOGO_PAGE_SIZE + 1
    end = min(start + LOGO_PAGE_SIZE - 1, total)
    rows = []
    row = []
    styles = ["primary", "success", "danger"]
    for i, n in enumerate(range(start, end + 1)):
        if kind == "logo":
            emoji_id = LOGO_TEMPLATE_EMOJI_IDS.get(n)
        elif kind == "logo2":
            emoji_id = LOGO2_TEMPLATE_EMOJI_IDS.get(n)
        elif kind == "logo3":
            emoji_id = LOGO3_TEMPLATE_EMOJI_IDS.get(n)
        else:
            emoji_id = None
        kwargs = {"text": str(n), "callback_data": f"logotpl:{n}", "style": styles[i % 3]}
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id
        row.append(InlineKeyboardButton(**kwargs))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # ✨ Hammasi & 🔢 Shablon raqamini yozish
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_all_templates"), callback_data="logotpl:all", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["fire"])])
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_custom_templates"), callback_data="logotpl:custom_input", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["lightning"])])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=get_text_lang(lang, "btn_prev"), callback_data=f"logopage:{page - 1}", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["black_star"]))
    if end < total:
        nav.append(InlineKeyboardButton(text=get_text_lang(lang, "btn_next"), callback_data=f"logopage:{page + 1}", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["green_check"]))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=get_text_lang(lang, "btn_back_main"), callback_data="backmain", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"])])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_logo_template_page(message: Message, page: int, kind: str, edit_callback: CallbackQuery | None = None, lang: str = "uz"):
    if get_total_logo_templates(kind) == 0:
        text = f"{get_logo_section_title(kind, lang)}\n" + get_text_lang(lang, "no_templates_in_section")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text_lang(lang, "btn_back_main"), callback_data="backmain")]])
        if edit_callback is not None:
            try:
                await edit_callback.message.edit_text(text, reply_markup=kb)
                return
            except Exception: pass
        await message.answer(text, reply_markup=kb)
        return

    text, entities = build_logo_preview(page, kind, lang)
    kb = logo_page_keyboard(page, kind, lang)
    if edit_callback is not None:
        try:
            await edit_callback.message.edit_text(text, entities=entities, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(text, entities=entities, reply_markup=kb)


@router.callback_query(F.data.in_(["section:logo", "section:logo2", "section:logo3"]))
async def section_logo(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    await state.clear()
    kind = callback.data.split(":")[1]
    await state.update_data(kind=kind)
    await callback.answer()
    await _send_logo_template_page(callback.message, 0, kind, lang=user_lang)


@router.callback_query(F.data.startswith("logopage:"))
async def logo_page_nav(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    kind = data.get("kind", "logo")
    await callback.answer()
    await _send_logo_template_page(callback.message, page, kind, edit_callback=callback, lang=user_lang)


@router.callback_query(F.data.startswith("logotpl:"))
async def logo_template_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    val = callback.data.split(":")[1]
    data = await state.get_data()
    kind = data.get("kind", "logo")

    if val == "custom_input":
        await state.set_state(LogoFlow.waiting_template_numbers)
        total = get_total_logo_templates(kind)
        await callback.answer()
        await callback.message.answer(
            get_text_lang(user_lang, "custom_tpl_prompt", max_total=total)
        )
        return

    if val == "all":
        await state.update_data(template_number="all", kind=kind)
        await state.set_state(LogoFlow.waiting_outer)
        await callback.answer(get_text_lang(user_lang, "btn_all_templates"))
        await callback.message.answer(
            get_text_lang(user_lang, "outer_color_prompt"),
            reply_markup=color_keyboard("outer", lang=user_lang),
        )
    else:
        n = int(val)
        await state.update_data(template_number=n, kind=kind)
        await state.set_state(LogoFlow.waiting_outer)
        await callback.answer(get_text_lang(user_lang, "tpl_selected_toast", n=n))
        await callback.message.answer(
            get_text_lang(user_lang, "tpl_selected_outer_prompt", n=n),
            reply_markup=color_keyboard("outer", lang=user_lang),
        )


@router.message(LogoFlow.waiting_template_numbers, F.text)
async def logo_got_template_numbers(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    if (message.text or "").startswith("/"):
        return
    data = await state.get_data()
    kind = data.get("kind", "logo")
    total = get_total_logo_templates(kind)

    numbers = _parse_template_numbers(message.text, total)
    if not numbers:
        await message.answer(get_text_lang(user_lang, "custom_tpl_invalid", max_total=total))
        return

    await state.update_data(template_number=numbers, kind=kind)
    await state.set_state(LogoFlow.waiting_outer)
    nums_str = ", ".join(str(n) for n in numbers)
    await message.answer(
        get_text_lang(user_lang, "custom_tpl_selected", count=len(numbers), nums=nums_str),
        reply_markup=color_keyboard("outer", lang=user_lang),
    )


@router.callback_query(LogoFlow.waiting_outer, F.data.startswith("outer:"))
async def logo_outer_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(LogoFlow.waiting_outer_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "outer_custom_prompt"))
        return
    await state.update_data(outer_hex=value)
    await state.set_state(LogoFlow.waiting_inner)
    await callback.answer(get_text_lang(user_lang, "outer_chosen_toast", color=value))
    await callback.message.answer(
        get_text_lang(user_lang, "inner_prompt"),
        reply_markup=color_keyboard("inner", lang=user_lang),
    )


@router.message(LogoFlow.waiting_outer_hex, F.text)
async def logo_outer_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(outer_hex=hexcode)
    await state.set_state(LogoFlow.waiting_inner)
    await message.answer(
        get_text_lang(user_lang, "outer_hex_set", hex=hexcode),
        reply_markup=color_keyboard("inner", lang=user_lang),
    )


@router.callback_query(LogoFlow.waiting_inner, F.data.startswith("inner:"))
async def logo_inner_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(LogoFlow.waiting_inner_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "inner_custom_prompt"))
        return
    await state.update_data(inner_hex=value)
    await callback.answer(get_text_lang(user_lang, "inner_chosen_toast", color=value))

    await state.set_state(LogoFlow.waiting_logo_color)
    await callback.message.answer(
        get_text_lang(user_lang, "logo_color_prompt"),
        reply_markup=color_keyboard("logocolor", allow_skip=True, lang=user_lang),
    )


@router.message(LogoFlow.waiting_inner_hex, F.text)
async def logo_inner_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(inner_hex=hexcode)

    await state.set_state(LogoFlow.waiting_logo_color)
    await message.answer(
        get_text_lang(user_lang, "inner_hex_set", hex=hexcode),
        reply_markup=color_keyboard("logocolor", allow_skip=True, lang=user_lang),
    )


@router.callback_query(LogoFlow.waiting_logo_color, F.data.startswith("logocolor:"))
async def logo_color_chosen(callback: CallbackQuery, state: FSMContext):
    user_lang = get_user_lang(callback.from_user.id) or "uz"
    value = callback.data.split(":", 1)[1]
    if value == "custom":
        await state.set_state(LogoFlow.waiting_logo_color_hex)
        await callback.answer()
        await callback.message.answer(get_text_lang(user_lang, "logo_custom_prompt"))
        return
    if value == "skip":
        await state.update_data(logo_hex=None)
        await callback.answer(get_text_lang(user_lang, "logo_skip_toast"))
    else:
        await state.update_data(logo_hex=value)
        await callback.answer(get_text_lang(user_lang, "logo_color_toast", color=value))
    _, font_path = logo_engine.FONT_OPTIONS["classic"]
    await state.update_data(font_path=font_path)
    await state.set_state(LogoFlow.waiting_svg)
    await callback.message.answer(get_text_lang(user_lang, "text_input_prompt"))


@router.message(LogoFlow.waiting_logo_color_hex, F.text)
async def logo_color_hex(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    hexcode = _normalize_hex(message.text or "")
    if not hexcode:
        await message.answer(get_text_lang(user_lang, "invalid_hex"))
        return
    await state.update_data(logo_hex=hexcode)
    _, font_path = logo_engine.FONT_OPTIONS["classic"]
    await state.update_data(font_path=font_path)
    await state.set_state(LogoFlow.waiting_svg)
    await message.answer(
        get_text_lang(user_lang, "logo_hex_set", hex=hexcode)
    )


async def _logo_continue_with_svg(message: Message, state: FSMContext, svg_text: str):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await state.update_data(svg_text=svg_text)
    data = await state.get_data()
    kind = data.get("kind", "logo")
    d = LOGO_SECTIONS.get(kind, LOGO_SECTIONS["logo"])["dir"]

    tpl_num = data["template_number"]
    if isinstance(tpl_num, list) and tpl_num:
        test_num = tpl_num[0]
    elif tpl_num == "all":
        test_num = 1
    else:
        test_num = int(tpl_num)

    template_filename = f"{test_num:03d}.json"
    try:
        logo_engine.build_tgs_sticker(
            template_filename, svg_text,
            outer_hex=data["outer_hex"], inner_hex=data["inner_hex"], logo_hex=data.get("logo_hex"),
            size_percent=logo_engine.DEFAULT_SIZE_PERCENT,
            dir_path=d
        )
    except Exception as e:
        await message.answer(get_text_lang(user_lang, "logo_build_error", error=e))
        return

    await state.set_state(Flow.pack_title)
    await message.answer(get_text_lang(user_lang, "pack_title_prompt"))


@router.message(LogoFlow.waiting_svg, F.text)
async def logo_got_svg_text(message: Message, state: FSMContext):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    if (message.text or "").startswith("/"):
        return
    data = await state.get_data()
    font_path = data.get("font_path")
    try:
        svg_text = logo_engine.text_to_svg(message.text, font_path=font_path)
    except Exception as e:
        await message.answer(get_text_lang(user_lang, "svg_convert_error", error=e))
        return
    await _logo_continue_with_svg(message, state, svg_text)


@router.message(LogoFlow.waiting_svg)
async def logo_got_svg_wrong_type(message: Message):
    user_lang = get_user_lang(message.from_user.id) or "uz"
    await message.answer(get_text_lang(user_lang, "just_text_prompt"))


async def _render_and_stage_logo_pack(message: Message, state: FSMContext):
    """Renders the final .tgs for the chosen logo/text template + colors,
    saves it to disk, and stages paths/nick/pack_kind in FSM data exactly
    like the Name-emoji flow does, so the shared payment code can take
    over from here."""
    data = await state.get_data()
    template_number = data["template_number"]
    kind = data.get("kind", "logo")
    d = LOGO_SECTIONS.get(kind, LOGO_SECTIONS["logo"])["dir"]

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    if template_number == "all":
        total = get_total_logo_templates(kind)
        nums = list(range(1, total + 1))
    elif isinstance(template_number, list):
        nums = template_number
    else:
        nums = [int(template_number)]

    for n in nums:
        template_filename = f"{n:03d}.json"
        try:
            tgs_bytes, _ = logo_engine.build_tgs_sticker(
                template_filename, data["svg_text"],
                outer_hex=data["outer_hex"], inner_hex=data["inner_hex"], logo_hex=data.get("logo_hex"),
                size_percent=logo_engine.DEFAULT_SIZE_PERCENT,
                dir_path=d
            )
            out_path = os.path.join(out_dir, f"{message.from_user.id}_{kind}_{n}.tgs")
            with open(out_path, "wb") as f:
                f.write(tgs_bytes)
            paths.append(out_path)
        except Exception as e:
            logging.error(f"Error rendering logo template {n} in section {kind}: {e}")

    nick = _random_nick()
    await state.update_data(paths=paths, nick=nick, pack_kind="emoji")


# ============================================================================
# ADMIN PANEL — ikkala bo'lim uchun ham (Name / Logo/Text alohida narxlar)
# ============================================================================

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Bepul foydalanuvchilar", callback_data="adm:free", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["lightning"]),
    ], [
        InlineKeyboardButton(text="Name emoji narxi (Bo'lim 1)", callback_data="adm:price_name", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"]),
    ], [
        InlineKeyboardButton(text="Logo/Text narxi (Bo'lim 2)", callback_data="adm:price_logo", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"]),
        InlineKeyboardButton(text="Extra narxi (Bo'lim 3)", callback_data="adm:price_logo2", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"]),
    ], [
        InlineKeyboardButton(text="Extra narxi (Bo'lim 4)", callback_data="adm:price_logo3", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"]),
        InlineKeyboardButton(text="Bot kodi narxi", callback_data="adm:price_code", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["stars"]),
    ], [
        InlineKeyboardButton(text="Ruxsatni olib tashlash", callback_data="adm:revoke", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"]),
    ], [
        InlineKeyboardButton(text="Majburiy kanallar", callback_data="adm:channel", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["globe"]),
        InlineKeyboardButton(text="Yordam bo'limini sozlash", callback_data="adm:support", style="success", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["warning"]),
    ], [
        InlineKeyboardButton(text="Statistika", callback_data="adm:stats", style="primary", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["gold_star"]),
    ], [
        InlineKeyboardButton(text="Xabar tarqatish", callback_data="adm:broadcast", style="danger", icon_custom_emoji_id=PREMIUM_EMOJI_IDS["fire"]),
    ]])


@router.callback_query(F.data.startswith("refundcode:"))
async def refund_code_payment(callback: CallbackQuery, state: FSMContext):
    """The refund button posted to the log channel. Anyone in that channel
    can see it, but only ADMIN_ID is allowed to actually trigger the
    refund - everyone else just gets a 'no permission' popup and nothing
    happens."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Sizda bu tugmadan foydalanish huquqi yo'q.", show_alert=True)
        return

    ref_id = callback.data.split(":", 1)[1]
    requests = load_refund_requests()
    entry = requests.get(ref_id)
    if not entry:
        await callback.answer("Bu so'rov topilmadi (eskirgan bo'lishi mumkin).", show_alert=True)
        return
    if entry.get("done"):
        await callback.answer("Bu allaqachon qaytarilgan.", show_alert=True)
        return

    try:
        await callback.bot.refund_star_payment(
            user_id=entry["user_id"], telegram_payment_charge_id=entry["charge_id"],
        )
    except Exception as e:
        logging.exception("manual refund failed")
        await callback.answer(f"Qaytarishda xatolik: {e}", show_alert=True)
        return

    entry["done"] = True
    requests[ref_id] = entry
    save_refund_requests(requests)

    await callback.answer("✅ Qaytarildi.", show_alert=True)
    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Qaytarildi.")
    except Exception:
        pass


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Admin panel:", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("adm:"))
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    action = callback.data.split(":")[1]
    if action == "free":
        listing = "\n".join(str(i) for i in sorted(load_allowed())) or "(bo'sh)"
        await state.set_state(AdminFlow.add_id)
        await callback.message.answer(f"Bepul foydalanuvchilar:\n{listing}\n\nQo'shish uchun user_id yuboring:")
    elif action.startswith("price_"):
        kind = action.split("_", 1)[1]
        label = price_label(kind)
        await state.update_data(price_kind=kind)
        await state.set_state(AdminFlow.set_price)
        await callback.message.answer(f"Hozirgi {label} narxi: {load_price(kind)} ⭐\n\nYangi narxni (son, Stars) yuboring:")
    elif action == "revoke":
        listing = "\n".join(str(i) for i in sorted(load_allowed())) or "(bo'sh)"
        await state.set_state(AdminFlow.remove_id)
        await callback.message.answer(f"Bepul foydalanuvchilar:\n{listing}\n\nOlib tashlash uchun user_id yuboring:")
    elif action == "channel":
        current = "\n".join(get_channels()) or "(o'rnatilmagan)"
        await state.set_state(AdminFlow.set_channel)
        await callback.message.answer(
            f"Hozirgi majburiy kanallar:\n{current}\n\n"
            "Yangi kanallar ro'yxatini yuboring (har birini bo'sh joy yoki yangi qatorga yozing, "
            "masalan @kanal1 @kanal2). Bu ro'yxat eskisini to'liq almashtiradi.\n"
            "Barcha kanallarni o'chirish uchun 'off' deb yozing:"
        )
    elif action == "support":
        current = get_support_contact()
        await state.set_state(AdminFlow.set_support)
        await callback.message.answer(
            f"Hozirgi yordam kontakti: {current}\n\n"
            "Yangi kontaktni yuboring (masalan @sizning_username). Bu faqat shu botning "
            "o'zida ishlatiladi — kod sotilganda xaridorga yubormaysiz, u o'zining "
            "kontaktini shu yerdan alohida sozlaydi."
        )
    elif action == "stats":
        stats = load_stats()
        if not stats:
            await callback.message.answer("Hozircha statistika yo'q.")
        else:
            entries = list(stats.items())

            def _label(uid: str, entry: dict) -> str:
                return f"@{entry['username']}" if entry.get("username") else f"id {uid}"

            by_packs = sorted(entries, key=lambda kv: kv[1].get("packs", 0), reverse=True)[:10]
            by_stars = sorted(entries, key=lambda kv: kv[1].get("stars", 0), reverse=True)[:10]

            packs_text = "\n".join(
                f"{i}. {_label(uid, e)} — {e.get('packs', 0)} ta"
                for i, (uid, e) in enumerate(by_packs, start=1)
            ) or "(bo'sh)"
            stars_text = "\n".join(
                f"{i}. {_label(uid, e)} — {e.get('stars', 0)} ⭐"
                for i, (uid, e) in enumerate(by_stars, start=1)
            ) or "(bo'sh)"

            await callback.message.answer(
                f"📊 Statistika\n\n"
                f"🏆 Eng ko'p emoji/stiker yasaganlar:\n{packs_text}\n\n"
                f"⭐ Eng ko'p Stars to'laganlar:\n{stars_text}"
            )
    elif action == "broadcast":
        total = len(load_users())
        await state.set_state(AdminFlow.broadcast)
        await callback.message.answer(
            f"Reklama xabaringizni yozing (matn, custom emoji, rasm, video — hammasi bo'ladi).\n"
            f"Hozircha botga start bosgan {total} ta foydalanuvchi bor."
        )
    await callback.answer()


@router.message(AdminFlow.add_id)
async def admin_add_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int((message.text or "").strip())
    except ValueError:
        await message.answer("user_id butun son bo'lishi kerak. Qaytadan yuboring:")
        return
    allowed = load_allowed()
    allowed.add(uid)
    save_allowed(allowed)
    await message.answer(f"✅ {uid} ga bepul foydalanish ruxsati berildi.")
    await state.clear()


@router.message(AdminFlow.remove_id)
async def admin_remove_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int((message.text or "").strip())
    except ValueError:
        await message.answer("user_id butun son bo'lishi kerak. Qaytadan yuboring:")
        return
    allowed = load_allowed()
    allowed.discard(uid)
    save_allowed(allowed)
    await message.answer(f"❌ {uid} dan ruxsat olib tashlandi.")
    await state.clear()


@router.message(AdminFlow.set_price)
async def admin_set_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        stars = int((message.text or "").strip())
        if stars < 1:
            raise ValueError
    except ValueError:
        await message.answer("Narx musbat butun son bo'lishi kerak. Qaytadan yuboring:")
        return
    data = await state.get_data()
    kind = data.get("price_kind", "name")
    label = price_label(kind)
    save_price(kind, stars)
    await message.answer(f"✅ {label} narxi {stars} ⭐ qilib o'zgartirildi.")
    await state.clear()


@router.message(AdminFlow.set_channel)
async def admin_set_channel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text.lower() == "off":
        set_channels([])
        await message.answer("✅ Barcha majburiy kanallar o'chirildi.")
    else:
        raw = [t for t in text.replace(",", "\n").split() if t]
        channels = []
        for t in raw:
            uname = t.replace("https://t.me/", "").replace("http://t.me/", "").strip()
            if not uname.startswith("@"):
                uname = "@" + uname
            channels.append(uname)
        set_channels(channels)
        listing = "\n".join(channels) or "(bo'sh)"
        await message.answer(f"✅ Majburiy kanallar o'rnatildi:\n{listing}")
    await state.clear()


@router.message(AdminFlow.set_support)
async def admin_set_support(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    contact = (message.text or "").strip()
    if not contact:
        await message.answer("Kontakt bo'sh bo'lmasin. Qaytadan yuboring:")
        return
    set_support_contact(contact)
    await message.answer(f"✅ Yordam kontakti {contact} qilib o'zgartirildi.")
    await state.clear()


@router.message(AdminFlow.broadcast)
async def admin_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()

    user_ids = load_users()
    total = len(user_ids)
    status = await message.answer(f"⏳ Yuborilmoqda: 0/{total}")

    sent = 0
    failed = 0
    for i, uid in enumerate(user_ids, start=1):
        while True:
            try:
                await message.bot.copy_message(
                    chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id,
                )
                sent += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
                continue
            except TelegramBadRequest:
                failed += 1
            except Exception:
                failed += 1
            break

        if i % 20 == 0 or i == total:
            try:
                await status.edit_text(f"⏳ Yuborilmoqda: {i}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ Tarqatish tugadi.\n\n"
        f"📤 Yuborildi: {sent} ta odamga\n"
        f"❌ Yuborilmadi: {failed} ta odamga"
    )


@router.errors()
async def errors_handler(event) -> bool:
    """Telegram raises TelegramForbiddenError whenever we try to message a
    user who has blocked the bot or deleted the chat - this is routine and
    not a bug, so we just note it quietly instead of dumping a traceback
    for every occurrence. Anything else is still logged with its
    traceback so real bugs stay visible."""
    from aiogram.exceptions import TelegramForbiddenError

    exception = event.exception
    if isinstance(exception, TelegramForbiddenError):
        logging.info(f"user blocked the bot / chat unavailable: {exception}")
        return True
    logging.exception("Unhandled error while processing update", exc_info=exception)
    return True


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


_LOCK_PATH = os.path.join(os.path.dirname(__file__), "sonnet.lock")
_lock_file_handle = None  # keep a reference so the OS lock isn't released early


def _acquire_single_instance_lock():
    """Bitta paytda faqat bitta bot nusxasi ishlashini ta'minlaydi.

    PID'ni faylga yozib, keyin kill(pid, 0) bilan tekshirish (eski usul)
    ishonchsiz edi: agar server/konteyner qayta ishga tushsa yoki PID
    boshqa, umuman bog'liq bo'lmagan jarayonga qayta berilib qolsa, bot
    "band" deb bekorga to'xtab qolishi yoki, aksincha, band emas deb
    ikkinchi nusxa ham ishga tushib ketishi mumkin edi — aynan shu ikkinchi
    holat ikkita jarayon bitta botning xabarlarini bo'lib olib, savol
    ikki marta so'ralishi / /start va /admin kech yoki qo'sh javob
    berishiga sabab bo'ladi.

    Buning o'rniga OS darajasidagi eksklyuziv fayl qulfidan (flock)
    foydalanamiz: uni faqat bitta jarayon ushlab turishi mumkin, va
    jarayon qanday tugasa ham (hatto kutilmagan crash bilan) OS uni
    darhol avtomatik bo'shatadi — shuning uchun eskirgan/noto'g'ri qulf
    qolib ketishi mumkin emas."""
    global _lock_file_handle
    import sys
    _lock_file_handle = open(_LOCK_PATH, "w")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(
            "❌ Bot allaqachon ishlab turibdi. Avval eski jarayonni to'xtating.",
            flush=True,
        )
        raise SystemExit(1)

    _lock_file_handle.write(str(os.getpid()))
    _lock_file_handle.flush()
    # _lock_file_handle qasddan yopilmaydi - jarayon tugaganda OS qulfni
    # o'zi bo'shatadi (garchi bu funksiya qaytib ketsa ham).


if __name__ == "__main__":
    _acquire_single_instance_lock()
    asyncio.run(main())
