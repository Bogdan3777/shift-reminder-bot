import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import calendar
import urllib.parse  # Для правильного кодування посилання

TOKEN = '8131533249:AAGZ6aLPIXXk3KsKZe1Zt4Cyw-ws4EsaLts'  # ← Замініть на свій токен!

bot = telebot.TeleBot(TOKEN)

# Графік змін
shifts = {
    0: ("ранкова", "06:00 – 14:00"),
    1: ("нічна",   "22:00 – 06:00"),
    2: ("денна",   "14:00 – 22:00")
}

base_date = datetime.date(2026, 1, 5)  # 5 січня 2026 — ранкова

def get_shift_info(date):
    if date.weekday() >= 5:  # Субота або неділя
        return "вихідний", None
    
    days_passed = (date - base_date).days
    shift_index = days_passed % 3
    name, hours = shifts[shift_index]
    return name, hours

# === Календар (без змін) ===
def create_calendar(year=None, month=None):
    now = datetime.datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    
    markup = InlineKeyboardMarkup(row_width=7)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    
    month_names = ["Січ", "Лют", "Бер", "Кві", "Тра", "Чер", "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"]
    row = [
        InlineKeyboardButton("◀", callback_data=f"cal_prev_{prev_year}_{prev_month}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton("▶", callback_data=f"cal_next_{next_year}_{next_month}")
    ]
    markup.row(*row)
    
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    markup.row(*(InlineKeyboardButton(d, callback_data="ignore") for d in week_days))
    
    month_cal = calendar.monthcalendar(year, month)
    for week in month_cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(str(day), callback_data=f"cal_select_{date_str}"))
        markup.row(*row)
    
    return markup

# === Головна магія: обробка вибору дати + посилання в Google Calendar ===
@bot.callback_query_handler(func=lambda call: True)
def calendar_handler(call):
    if call.data == "ignore":
        bot.answer_callback_query(call.id)
        return
    
    if call.data.startswith("cal_prev_") or call.data.startswith("cal_next_"):
        _, _, year, month = call.data.split("_")
        year, month = int(year), int(month)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_calendar(year, month))
        return
    
    if call.data.startswith("cal_select_"):
        _, _, date_str = call.data.split("_", 2)
        selected_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        name, hours = get_shift_info(selected_date)
        
        if hours is None:  # Вихідний
            text = f"📅 <b>{selected_date}</b>\n\n<b>Вихідний день 🎉</b>"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML")
        else:
            # Формуємо дані для події
            start_str, end_str = hours.split(" – ")
            event_date = selected_date.strftime("%Y%m%d")
            start_time = start_str.replace(":", "")
            end_time = end_str.replace(":", "")
            
            title = f"{name.capitalize()} зміна"
            details = f"Час роботи: {hours}\\nГрафік на заводі"
            location = "Завод"
            
            # Кодування для URL
            params = urllib.parse.quote_plus(f"{title}\n{details}")
            
            google_link = (
                f"https://www.google.com/calendar/render?action=TEMPLATE"
                f"&text={urllib.parse.quote(title)}"
                f"&dates={event_date}T{start_time}00/{event_date}T{end_time}00"
                f"&details={params}"
                f"&location={urllib.parse.quote(location)}"
                f"&sf=true&output=xml"
            )
            
            text = (
                f"📅 <b>{selected_date}</b>\n\n"
                f"Зміна: <b>{name.capitalize()}</b>\n"
                f"Час роботи: <b>{hours}</b>\n\n"
                f"<a href='{google_link}'>➕ Додати подію в Google Календар</a>"
            )
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                  parse_mode="HTML", disable_web_page_preview=True)
    
    bot.answer_callback_query(call.id)

# === /start, /сьогодні, /завтра, інші повідомлення — без змін ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Оберіть дату, щоб дізнатися зміну.\nСубота та неділя — вихідні.",
        reply_markup=create_calendar()
    )

@bot.message_handler(commands=['сьогодні'])
def today(message):
    name, hours = get_shift_info(datetime.date.today())
    if hours is None:
        text = f"Сьогодні <b>{datetime.date.today()}</b>\n\n<b>Вихідний день 🎉</b>"
    else:
        text = f"Сьогодні <b>{datetime.date.today()}</b>\nЗміна: <b>{name.capitalize()}</b>\nЧас роботи: <b>{hours}</b>"
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['завтра'])
def tomorrow(message):
    tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
    name, hours = get_shift_info(tomorrow_date)
    if hours is None:
        text = f"Завтра <b>{tomorrow_date}</b>\n\n<b>Вихідний день 🎉</b>"
    else:
        text = f"Завтра <b>{tomorrow_date}</b>\nЗміна: <b>{name.capitalize()}</b>\nЧас роботи: <b>{hours}</b>"
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Оберіть дату в календарі:", reply_markup=create_calendar())

# Запуск
print("Бот запущений з посиланням на Google Calendar!")
bot.polling(none_stop=True)
