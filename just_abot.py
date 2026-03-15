import telebot
import requests
import sqlite3
import random
import re
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from fuzzywuzzy import fuzz

TOKEN = "YOUR_TOKEN_HERE" 

ADMIN_IDS = [602830469, 6037311805]
DEVELOPERS = ["@LibyanErwin", "@IBnde"]
SUPPORT_USERNAME = "vkkvc"
ADMIN_SUPPORT_LINK = "ccuucuc"

TOKEN = '8521478146:AAF5BCZD6hBPWLhNjVNxmLMf2uZ8AQmGyG0'
bot = telebot.TeleBot(TOKEN)

user_amounts = {}

cache = {
    "ton": {"price": 5.0, "last_update": 0},
    "sar": {"price": 3.75, "last_update": 0},
    "egp": {"price": 50.0, "last_update": 0}
}
CACHE_DURATION = 300

def get_ton_price():
    now = time.time()
    if now - cache["ton"]["last_update"] < CACHE_DURATION:
        return cache["ton"]["price"]
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
        data = requests.get(url, timeout=5).json()
        price = float(data["price"])
        cache["ton"] = {"price": price, "last_update": now}
        return price
    except:
        return cache["ton"]["price"]

def get_sar_price():
    val = get_setting("price_sar")
    return float(val) if val else 3.75

def get_egp_price():
    val = get_setting("price_egp")
    return float(val) if val else 50.0

def get_currency_rate(key):
    val = get_setting(f"price_{key}")
    default_rates = {
        "ly_libyana": 13.8,
        "ly_madar": 14.5,
        "ly_cash": 10.74,
        "asia_egp": 30.0,
        "usdt_asia": 1.72
    }
    return float(val) if val else default_rates.get(key, 1.0)

def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  points INTEGER DEFAULT 0, 
                  with_middleman INTEGER DEFAULT 0, 
                  without_middleman INTEGER DEFAULT 0,
                  is_banned INTEGER DEFAULT 0,
                  quiz_attempts INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, 
                  value TEXT)''')
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("rules", """قوانين قروب Chat Zone:
1. لسنا مسؤولين على اي معاملة بدون وسيط من وسطاء Chat Zone.
2. موضوع امر( /الحالة ) هدا الامر يعطيك كم نسبة موثوقية الشخص يعني كم معاملة تعامل فيها وكذا.
3. اعلانك تكرره في 5 دقايق اول شي تاخذ تحذير ثم تقييد.
4. ممنوع بوتات النشر مهما كانت.
5. ممنوع السب او القذف او شتم.
6. ممنوع بيع وشراء وتداول اي عمل غير اخلاقي او ديني.
7. ممنوع تشويه سمعة بدون دلايل ترسلهم لي احد الوسطاء.
8. تنصب = حظر عام من بوت ايزل.
9. تكرار الاعلانات مرة كل دقيقتين.
10. اي مخالفة للقوانين انذار ثم تقييد."""))
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("questions", """كم مرة يسمح بتكرار الإعلان في الدقائق؟|5,خمسة,خمس دقائق
ماذا يحدث في حال النصب؟|حظر عام,حظر,انحظر
هل نحن مسؤولون عن المعاملات بدون وسيط؟|لا,غير مسؤولين
ماذا يحدث عند تكرار الإعلانات؟|تحذير ثم تقييد,تحذير,تقييد
هل يسمح ببوتات النشر؟|لا,ممنوع"""))
    
    default_prices = {
        "price_sar": "3.75",
        "price_egp": "50.0",
        "price_ly_libyana": "13.8",
        "price_ly_madar": "14.5",
        "price_ly_cash": "10.74",
        "price_usdt_asia": "1.72"
    }
    for k, v in default_prices.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def update_setting(key, value):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

def get_rules():
    return get_setting("rules")

def get_questions():
    raw = get_setting("questions")
    qs = []
    for line in raw.split('\n'):
        if '|' in line:
            q, a = line.split('|')
            qs.append({"q": q, "a": a.split(',')})
    return qs

def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT points, with_middleman, without_middleman, is_banned, quiz_attempts FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    if res:
        return {"points": res[0], "with_m": res[1], "without_m": res[2], "banned": res[3], "attempts": res[4]}
    return None

def update_user(user_id, username=None, points_add=0, with_m_add=0, without_m_add=0, ban=None, reset_attempts=False, add_attempt=False):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    if username:
        c.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    if ban is not None:
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (ban, user_id))
        if ban == 1:
            c.execute("UPDATE users SET points=0 WHERE user_id=?", (user_id,))
    if reset_attempts:
        c.execute("UPDATE users SET quiz_attempts=0 WHERE user_id=?", (user_id,))
    elif add_attempt:
        c.execute("UPDATE users SET quiz_attempts = quiz_attempts + 1 WHERE user_id=?", (user_id,))
    if points_add or with_m_add or without_m_add:
        c.execute("UPDATE users SET points = MIN(1000, points + ?), with_middleman = with_middleman + ?, without_middleman = without_middleman + ? WHERE user_id=?", 
                  (points_add, with_m_add, without_m_add, user_id))
    conn.commit()
    conn.close()

def get_user_by_username(username):
    if not username: return None
    username = username.replace("@", "")
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

init_db()

def currency_trigger(message):
    text = message.text.lower()
    match = re.search(r"(\d+\.?\d*)\s*(\$|تون|ton|ريال|sar)", text)
    if not match: return
    amount = float(match.group(1))
    unit = match.group(2)
    from_curr = "usd" if unit == "$" else ("ton" if unit in ["تون", "ton"] else "sar")
    user_amounts[message.chat.id] = {"amount": amount, "from": from_curr}
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    if from_curr != "usd": buttons.append(InlineKeyboardButton("إلى دولار $", callback_data="conv_usd"))
    if from_curr != "ton": buttons.append(InlineKeyboardButton("إلى تون TON", callback_data="conv_ton"))
    if from_curr != "sar": buttons.append(InlineKeyboardButton("إلى ريال سعودي", callback_data="conv_sar"))
    buttons.append(InlineKeyboardButton("إلى جنيه مصري", callback_data="conv_egp"))
    buttons.append(InlineKeyboardButton("إلى اسياسيل", callback_data="conv_asia"))
    buttons.append(InlineKeyboardButton("إلى دينار ليبي", callback_data="conv_ly"))
    kb.add(*buttons)
    bot.reply_to(message, f"تم اكتشاف مبلغ: {amount} {from_curr.upper()}\nاختر العملة التي تريد التحويل إليها:", reply_markup=kb)

@bot.message_handler(commands=['الاوامر'])
def show_admin_commands(message):
    if message.from_user.id not in ADMIN_IDS: return
    admin_text = """🛠 قائمة أوامر المشرفين:
1. زيد نقاط وساطة @user1 @user2 (3 نقاط لكل منهما)
2. زيد نقاط بيع بدون وساطة @user (10 نقاط)
3. /حظر_عام (بالرد على المستخدم)
4. /الحالة (بالرد على المستخدم)
5. /الاوامر (لعرض هذه القائمة)"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("لوحة التحكم ⚙️", callback_data="admin_settings"))
    bot.reply_to(message, admin_text, reply_markup=kb)

@bot.message_handler(commands=['start'])
def start(message):
    update_user(message.from_user.id, message.from_user.username)
    if message.chat.type != 'private': return
    text = f"مرحباً بك في بوت Chat Zone\n\nمطورين البوت:\n" + "\n".join(DEVELOPERS)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("حالتي 👤", callback_data="my_status"),
        InlineKeyboardButton("القوانين 📜", callback_data="rules"),
        InlineKeyboardButton("الدعم الفني 🛠", url=f"https://t.me/{SUPPORT_USERNAME}")
    )
    if message.from_user.id in ADMIN_IDS:
        kb.add(InlineKeyboardButton("لوحة التحكم ⚙️", callback_data="admin_settings"))
    bot.send_message(message.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "my_status":
        u = get_user(call.from_user.id)
        if not u or (u['points'] == 0 and u['with_m'] == 0 and u['without_m'] == 0):
            bot.send_message(call.message.chat.id, "لم تتم إضافة أي نقاط بعد.")
            return
        if u['banned']:
            bot.send_message(call.message.chat.id, "أنت محظور نهائياً!")
            return
        percentage = (u['points'] / 1000) * 100
        text = (f"👤 حالتك:\nنسبة الموثوقية: {percentage:.1f}%\nمعاملات بوسيط: {u['with_m']}\nمعاملات بدون وسيط: {u['without_m']}")
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("رجوع 🔙", callback_data="back_to_start"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "rules":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("رجوع 🔙", callback_data="back_to_start"))
        bot.edit_message_text(get_rules(), call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "back_to_start":
        text = f"مرحباً بك في بوت Chat Zone\n\nمطورين البوت:\n" + "\n".join(DEVELOPERS)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("حالتي 👤", callback_data="my_status"),
            InlineKeyboardButton("القوانين 📜", callback_data="rules"),
            InlineKeyboardButton("الدعم الفني 🛠", url=f"https://t.me/{SUPPORT_USERNAME}")
        )
        if call.from_user.id in ADMIN_IDS:
            kb.add(InlineKeyboardButton("لوحة التحكم ⚙️", callback_data="admin_settings"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "admin_settings":
        if call.from_user.id not in ADMIN_IDS: return
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("تعديل القوانين 📜", callback_data="edit_rules"))
        kb.add(InlineKeyboardButton("تعديل الأسئلة ❓", callback_data="edit_questions"))
        kb.add(InlineKeyboardButton("تعديل أسعار العملات 💰", callback_data="edit_prices"))
        kb.add(InlineKeyboardButton("رجوع 🔙", callback_data="back_to_start"))
        bot.edit_message_text("مرحباً بك في لوحة التحكم. ماذا تريد أن تعدل؟", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "edit_rules":
        if call.from_user.id not in ADMIN_IDS: return
        msg = bot.send_message(call.message.chat.id, "أرسل القوانين الجديدة الآن:")
        bot.register_next_step_handler(msg, save_rules)

    elif call.data == "edit_questions":
        if call.from_user.id not in ADMIN_IDS: return
        help_text = "أرسل الأسئلة الجديدة بالتنسيق التالي:\nالسؤال|الإجابة1,الإجابة2"
        msg = bot.send_message(call.message.chat.id, help_text)
        bot.register_next_step_handler(msg, save_questions)

    elif call.data == "edit_prices":
        if call.from_user.id not in ADMIN_IDS: return
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("الريال السعودي", callback_data="set_price_sar"),
               InlineKeyboardButton("الجنيه المصري", callback_data="set_price_egp"))
        kb.add(InlineKeyboardButton("اسياسيل", callback_data="set_price_usdt_asia"),
               InlineKeyboardButton("ليبيانا", callback_data="set_price_ly_libyana"))
        kb.add(InlineKeyboardButton("مدار", callback_data="set_price_ly_madar"),
               InlineKeyboardButton("كاش", callback_data="set_price_ly_cash"))
        kb.add(InlineKeyboardButton("رجوع 🔙", callback_data="admin_settings"))
        bot.edit_message_text("اختر العملة التي تريد تعديل سعرها مقابل الدولار:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("set_price_"):
        if call.from_user.id not in ADMIN_IDS: return
        key = call.data.replace("set_price_", "")
        msg = bot.send_message(call.message.chat.id, f"أرسل السعر الجديد لـ {key} مقابل 1 دولار:")
        bot.register_next_step_handler(msg, save_price, key)

    elif call.data.startswith("start_quiz_"):
        chat_id = call.data.replace("start_quiz_", "")
        qs = get_questions()
        if not qs:
            bot.approve_chat_join_request(chat_id, call.from_user.id)
            return
        q_item = random.choice(qs)
        msg = bot.edit_message_text(f"سؤال للتأكد:\n{q_item['q']}", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(msg, check_quiz_answer, q_item, chat_id)

    elif call.data.startswith("conv_"):
        data = user_amounts.get(call.message.chat.id)
        if not data: return
        target = call.data.replace("conv_", "")
        amount = data['amount']
        from_curr = data['from']
        
        ton_price = get_ton_price()
        sar_price = get_sar_price()
        egp_price = get_egp_price()
        
        usd_amount = amount if from_curr == "usd" else (amount * ton_price if from_curr == "ton" else amount / sar_price)
        
        res_text = ""
        if target == "usd": res_text = f"{amount} {from_curr.upper()} = {usd_amount:.2f}$"
        elif target == "ton": res_text = f"{amount} {from_curr.upper()} = {usd_amount/ton_price:.3f} TON"
        elif target == "sar": res_text = f"{amount} {from_curr.upper()} = {usd_amount * sar_price:.2f} ريال سعودي"
        elif target == "egp": res_text = f"{amount} {from_curr.upper()} = {usd_amount * egp_price:.2f} جنيه مصري"
        elif target == "asia": res_text = f"{amount} {from_curr.upper()} = {usd_amount * get_currency_rate('usdt_asia'):.2f} اسياسيل"
        elif target == "ly":
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("دينار ليبيانا", callback_data="ly_res_libyana"),
                   InlineKeyboardButton("دينار مدار", callback_data="ly_res_madar"))
            kb.add(InlineKeyboardButton("دينار كاش", callback_data="ly_res_cash"))
            bot.edit_message_text("اختر نوع العملة الليبية:", call.message.chat.id, call.message.message_id, reply_markup=kb)
            return
        if res_text: bot.edit_message_text(res_text, call.message.chat.id, call.message.message_id)

    elif call.data.startswith("ly_res_"):
        data = user_amounts.get(call.message.chat.id)
        if not data: return
        type_ly = call.data.replace("ly_res_", "")
        amount = data['amount']
        from_curr = data['from']
        ton_price = get_ton_price()
        sar_price = get_sar_price()
        usd_amount = amount if from_curr == "usd" else (amount * ton_price if from_curr == "ton" else amount / sar_price)
        rate = get_currency_rate(f"ly_{type_ly}")
        res_text = f"{amount} {from_curr.upper()} = {usd_amount * rate:.2f} دينار {type_ly}"
        bot.edit_message_text(res_text, call.message.chat.id, call.message.message_id)

def save_rules(message):
    if message.from_user.id not in ADMIN_IDS: return
    update_setting("rules", message.text)
    bot.reply_to(message, "✅ تم تحديث القوانين بنجاح!")

def save_questions(message):
    if message.from_user.id not in ADMIN_IDS: return
    update_setting("questions", message.text)
    bot.reply_to(message, "✅ تم تحديث الأسئلة بنجاح!")

def save_price(message, key):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        price = float(message.text)
        update_setting(f"price_{key}", str(price))
        bot.reply_to(message, f"✅ تم تحديث سعر {key} إلى {price} بنجاح!")
    except:
        bot.reply_to(message, "❌ خطأ: يرجى إرسال رقم صحيح.")

def check_quiz_answer(message, q_item, chat_id):
    user_id = message.from_user.id
    user_answer = message.text.lower() if message.text else ""
    is_correct = False
    for correct_a in q_item['a']:
        if fuzz.partial_ratio(user_answer, correct_a.lower()) > 80:
            is_correct = True
            break
    if is_correct:
        bot.approve_chat_join_request(chat_id, user_id)
        bot.send_message(message.chat.id, "إجابة صحيحة! تم قبول طلب انضمامك.")
        update_user(user_id, reset_attempts=True)
    else:
        update_user(user_id, add_attempt=True)
        u = get_user(user_id)
        if u and u['attempts'] >= 2:
            text = f"لقد أخطأت مرتين. يرجى مراجعة القوانين جيداً قبل المحاولة مرة أخرى.\n\n{get_rules()}\n\nتواصل مع مسؤولين المجموعة في حال ان البوت لم يقبل الطلب مع ان اجابتك صحيحة."
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("قرأتها ✅", callback_data=f"start_quiz_{chat_id}"))
            kb.add(InlineKeyboardButton("تواصل مع المسؤولين 📞", url=f"https://t.me/{ADMIN_SUPPORT_LINK}"))
            bot.send_message(message.chat.id, text, reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("حاول مجدداً 🔄", callback_data=f"start_quiz_{chat_id}"))
            bot.send_message(message.chat.id, "إجابة خاطئة، حاول مرة أخرى.", reply_markup=kb)

@bot.chat_join_request_handler()
def handle_join_request(request: ChatJoinRequest):
    user_id = request.from_user.id
    chat_id = request.chat.id
    update_user(user_id, request.from_user.username, reset_attempts=True)
    welcome_msg = f"أهلاً بك! للانضمام لمجموعة {request.chat.title}، يرجى قراءة القوانين جيداً ثم الضغط على الزر أدناه للإجابة على سؤال.\n\n{get_rules()}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("قرأتها ✅", callback_data=f"start_quiz_{chat_id}"))
    try: bot.send_message(user_id, welcome_msg, reply_markup=kb)
    except: pass

@bot.message_handler(commands=['الحالة'])
def check_status_cmd(message):
    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    u = get_user(target_user.id)
    if not u or (u['points'] == 0 and u['with_m'] == 0 and u['without_m'] == 0):
        bot.reply_to(message, "لم تتم إضافة أي نقاط بعد.")
        return
    percentage = (u['points'] / 1000) * 100
    text = (f"👤 حالة المستخدم {target_user.first_name}:\nنسبة الموثوقية: {percentage:.1f}%\nمعاملات بوسيط: {u['with_m']}\nمعاملات بدون وسيط: {u['without_m']}")
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text and m.text.startswith("زيد نقاط وساطة"))
def add_points_middleman_text(message):
    if message.from_user.id not in ADMIN_IDS: return
    usernames = re.findall(r"@\w+", message.text)
    if len(usernames) < 2:
        bot.reply_to(message, "يرجى ذكر يوزر شخصين لزيادة نقاطهما.")
        return
    success_list = []
    for uname in usernames[:2]:
        uid = get_user_by_username(uname)
        if uid:
            update_user(uid, points_add=3, with_m_add=1)
            success_list.append(uname)
    if success_list: bot.reply_to(message, f"تم إضافة 3 نقاط وساطة لكل من: {', '.join(success_list)}")
    else: bot.reply_to(message, "لم يتم العثور على المستخدمين في قاعدة بيانات البوت.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("زيد نقاط بيع بدون وساطة"))
def add_points_no_middleman_text(message):
    if message.from_user.id not in ADMIN_IDS: return
    usernames = re.findall(r"@\w+", message.text)
    if not usernames:
        bot.reply_to(message, "يرجى ذكر يوزر شخص لزيادة نقاطه.")
        return
    uname = usernames[0]
    uid = get_user_by_username(uname)
    if uid:
        update_user(uid, points_add=10, without_m_add=1)
        bot.reply_to(message, f"تم إضافة 10 نقاط بيع بدون وساطة للمستخدم {uname}")
    else: bot.reply_to(message, "لم يتم العثور على المستخدم في قاعدة بيانات البوت.")

@bot.message_handler(commands=['حظر_عام'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS: return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    update_user(target_id, ban=1)
    bot.reply_to(message, "تم تصفير النقاط وحظر المستخدم نهائياً من البوت.")

@bot.message_handler(func=lambda m: m.text and any(x in m.text.lower() for x in ["$", "تون", "ton", "ريال"]))
def currency_trigger_msg(message):
    currency_trigger(message)

@bot.message_handler(func=lambda m: True)
def auto_update_username(message):
    if message.from_user.username:
        update_user(message.from_user.id, message.from_user.username)

if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True, allowed_updates=['message', 'callback_query', 'chat_join_request'])
