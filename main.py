# Импорт необходимых модулей
import os
import telebot
from dotenv import load_dotenv
from telebot.util import quick_markup
from modules.xlsx_parse import get_schedule
from modules.days import dayNames, lessonTime, dayEmojis
from pysondb import getDb
import asyncio

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение BOT_TOKEN из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация экземпляра TeleBot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Создайте каталог "chats", если он не существует
if not os.path.exists("chats"):
    os.makedirs("chats")


# Function to send the private schedule
def send_private_schedule(message: telebot.types.Message):
    groups = get_schedule().keys()
    bot.reply_to(
        message,
        "Выберите группу:\n\nТакже вы можете добавить этого бота в чат и использовать его для учета и выбора дежурных студентов",
        reply_markup=quick_markup(
            {
                f"{group}": {"callback_data": f"choose_group|{group}"}
                for group in groups
            },
            row_width=4,
        ),
    )


# Функция для проверки того, является ли пользователь администратором чата
def is_chat_admin(chat_id):
    ids = []
    admins = bot.get_chat_administrators(chat_id=chat_id)
    for admin in admins:
        ids.append(admin.user.id)
    return ids


# Функция форматирования расписания для заданной группы и дня
def format_schedule(group, day):
    schedule_data = get_schedule()[group]
    msg = f"<b>Расписание для группы {group}</b>\n\n"
    msg += f"<b>{dayNames[day]}</b>\n"
    for lesson, data in schedule_data[day].items():
        if data:
            if int(lesson) == 7:
                break
            discipline = data["discipline"]
            teacher = data["teacher"]
            room = data["room"]
            msg += f"<pre>\t\t{dayEmojis[int(lesson)]}: {discipline}\n\t\t\t\t\t\t\t{room}\n\t\t\t\t\t\t\t{lessonTime[int(lesson)] if teacher != ' ' else ''}</pre>\n\n\n"
    return msg


# Обработчик коллбека для выбора дня
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "choose_day")
def choose_day(call: telebot.types.CallbackQuery):
    day = int(call.data.split("|")[1])
    group = call.data.split("|")[2]
    markup = days_markup(group, day)
    msg = format_schedule(group, int(day))
    try:
        bot.edit_message_text(
            msg, call.from_user.id, call.message.id, reply_markup=markup
        )
        bot.answer_callback_query(call.id, text=f"{group} | {dayNames[day]}")
    except telebot.apihelper.ApiTelegramException:
        bot.answer_callback_query(call.id, text=f"Ничего не изменилось")


# Обработчик события добавления бота в новый чат
@bot.message_handler(content_types=["new_chat_members"])
def added_to_chat(message: telebot.types.Message):
    bot_id = bot.get_me().id
    for user in message.new_chat_members:
        if user.id == bot_id:
            return chat_processer(message)


# Обработчик обратного вызова для возврата к выбору группы
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "back")
def back_handler(call: telebot.types.CallbackQuery):
    groups = get_schedule().keys()
    bot.edit_message_text(
        text="Выберите группу:",
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=quick_markup(
            {
                f"{group}": {"callback_data": f"choose_group|{group}"}
                for group in groups
            },
            row_width=4,
        ),
    )
    bot.answer_callback_query(call.id, text=f"◀️ Возвращаемся обратно")


# Обработчик коллбека для выбора группы
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "choose_group")
def change_group(call: telebot.types.CallbackQuery):
    group = call.data.split("|")[1]
    day = 0
    markup = days_markup(group, day)
    msg = format_schedule(group, 0)
    bot.edit_message_text(
        text=msg,
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id, text=f"{group}")


# Функция для создания разметки с кнопками выбора дней недели
def days_markup(group, day):
    return quick_markup(
        {
            "✅ Понедельник"
            if day == 0
            else "Понедельник": {"callback_data": f"choose_day|0|{group}"},
            "✅ Вторник"
            if day == 1
            else "Вторник": {"callback_data": f"choose_day|1|{group}"},
            "✅ Среда"
            if day == 2
            else "Среда": {"callback_data": f"choose_day|2|{group}"},
            "✅ Четверг"
            if day == 3
            else "Четверг": {"callback_data": f"choose_day|3|{group}"},
            "✅ Пятница"
            if day == 4
            else "Пятница": {"callback_data": f"choose_day|4|{group}"},
            "◀️": {"callback_data": f"back"},
        },
        row_width=5,
    )


# Функция для обновления порядка дежурств студентов в базе данных
def update_order(database):
    # Получаем все записи из базы данных
    students = database.getAll()

    # Сортируем студентов по обязанностям
    sorted_students = sorted(students, key=lambda x: x["duties"])

    # Обновляем значение 'order' для каждого студента
    for i, student in enumerate(sorted_students):
        database.updateById(student["id"], {"order": i + 1})


# Функция для поиска студентов с минимальным числом обязанностей
def find_min_duties_students(group, chat_db):
    update_order(chat_db)
    data = chat_db.getAll()
    if group == 0:
        students_list = data
    else:
        students_list = [student for student in data if student["group"] == group]

    sorted_students = sorted(students_list, key=lambda student: student["duties"])
    return sorted_students[:2]


# Обработчик для назначения студента на выбранную группу через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "student_set")
def student_set(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    student_id = call.data.split("|")[1]
    group = call.data.split("|")[2]
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    chat_db.updateByQuery(
        {"id": int(student_id)}, {"id": int(student_id), "group": int(group)}
    )
    markup = quick_markup(
        {
            "➕ Добавить еще": {"callback_data": "add_new"},
            "◀️ Назад": {"callback_data": "edit"},
        },
        row_width=1,
    )
    return edit(call)


# Обработчик для добавления нового студента через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "add_new")
def add_new(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")

    def process_name(message: telebot.types.Message):
        name = message.text
        id = chat_db.add({"name": name, "order": 0, "group": None, "duties": 0})
        markup = quick_markup(
            {
                "1": {"callback_data": f"student_set|{id}|1"},
                "2": {"callback_data": f"student_set|{id}|2"},
            }
        )
        bot.reply_to(
            message,
            f"Студент {name} добавлен, выберите его группу",
            reply_markup=markup,
        )

    name_msg = bot.send_message(call.message.chat.id, "Введите имя и фамилию студента")
    bot.register_next_step_handler(name_msg, process_name)


# Функция для проверки, является ли строка целым числом
def is_integer(s):
    if s.startswith("-"):
        return s[1:].isdigit()
    else:
        return s.isdigit()


# Обработчик для редактирования числа дежурств студента через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "edit_duties")
def edit_duties(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    student_id = int(call.data.split("|")[1])

    def change_duties_count(message: telebot.types.Message):
        if not is_integer(message.text):
            return bot.reply_to(message, "Это не число")

        new_count = int(message.text)

        chat_db.updateById(student_id, {"duties": new_count})
        return edit(call)

    msg = bot.send_message(call.message.chat.id, "Введите кол-во дежурств для студента")

    bot.register_next_step_handler(msg, change_duties_count)


# Обработчик для удаления студента через коллбэк
@bot.callback_query_handler(
    func=lambda call: call.data.split("|")[0] == "delete_student"
)
def delete_student(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    student_id = int(call.data.split("|")[1])

    chat_db.deleteById(student_id)
    return edit(call)


# Обработчик для редактирования имени студента через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "edit_name")
def edit_duties(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    student_id = int(call.data.split("|")[1])

    def change_name(message: telebot.types.Message):
        new_name = message.text

        chat_db.updateById(student_id, {"name": new_name})
        return edit(call)

    msg = bot.send_message(call.message.chat.id, "Введите новое имя студента")

    bot.register_next_step_handler(msg, change_name)


# Обработчик для назначения группы студента через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "set_group")
def set_group(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    group = int(call.data.split("|")[2])
    student_id = int(call.data.split("|")[1])
    chat_db.updateById(student_id, {"group": group})
    return edit(call)


# Обработчик для редактирования группы студента через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "edit_group")
def edit_group(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    student_id = int(call.data.split("|")[1])
    markup = quick_markup(
        {
            "1": {"callback_data": f"set_group|{student_id}|1"},
            "2": {"callback_data": f"set_group|{student_id}|2"},
        }
    )
    bot.send_message(
        call.message.chat.id,
        f"Выберите новую группу студента {chat_db.getById(student_id)['name']}",
        reply_markup=markup,
    )


# Обработчик для редактирования списка студентов через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "edit")
def edit(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    markup = quick_markup({"➕ Добавить нового студента": {"callback_data": "add_new"}})
    if chat_db.getAll() == []:
        bot.edit_message_text(
            "Список студентов пуст",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup,
        )
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row_width = 4
        markup.add(
            telebot.types.InlineKeyboardButton("Имя", callback_data="NONE"),
            telebot.types.InlineKeyboardButton("Группа", callback_data="NONE"),
            telebot.types.InlineKeyboardButton("Дежурства", callback_data="NONE"),
            telebot.types.InlineKeyboardButton("Удаление", callback_data="NONE"),
        )
        for student in chat_db.getAll():
            markup.add(
                telebot.types.InlineKeyboardButton(
                    student["name"], callback_data=f"edit_name|{student['id']}"
                ),
                telebot.types.InlineKeyboardButton(
                    f'{student["group"]}', callback_data=f"edit_group|{student['id']}"
                ),
                telebot.types.InlineKeyboardButton(
                    f'{student["duties"]}', callback_data=f"edit_duties|{student['id']}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌", callback_data=f"delete_student|{student['id']}"
                ),
            )
        markup.add(
            telebot.types.InlineKeyboardButton(
                "➕ Добавить нового студента", callback_data="add_new"
            )
        )
        bot.edit_message_text(
            "Список студентов:",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup,
        )


# Обработчик для выбора дежурных студентов через коллбэк
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "choose")
def choose(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    group = int(call.data.split("|")[1])

    if chat_db.getAll() == []:
        bot.answer_callback_query(
            call.id,
            text="🙅‍♂️ Сначала вам нужно настроить список студентов",
            show_alert=True,
        )
    else:
        # Проверяем, чтобы у всех студентов была указана группа
        for student in chat_db.getAll():
            if student["group"] is None:
                return bot.send_message(
                    call.message.chat.id,
                    f"Сначала установите для студента {student['name']} группу",
                )

        # Находим двух студентов с минимальным числом дежурств
        students = find_min_duties_students(group, chat_db)
        chosen = students[:2]
        first, second = chosen[0], chosen[1]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                text=f"{first['name']} | {first['duties']}",
                callback_data=f"success|{first['id']}",
            ),
            telebot.types.InlineKeyboardButton(
                text=f"{second['name']} | {second['duties']}",
                callback_data=f"success|{second['id']}",
            ),
        )
        markup.add(
            telebot.types.InlineKeyboardButton(
                text="♻️",
                callback_data=f"reroll|{first['id']}|{second['id']}|0|{group}",
            ),
            telebot.types.InlineKeyboardButton(
                text="♻️",
                callback_data=f"reroll|{first['id']}|{second['id']}|1|{group}",
            ),
        )
        bot.edit_message_text(
            f"{first['name']} | {second['name']}",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup,
        )


# Функция для получения новых дежурных студентов
def get_new_students(database, list_of_students, index_to_replace, group):
    data = database.getAll()

    if group != 0:
        # Фильтруем студентов по указанной группе
        data = [student for student in data if student["group"] == group]
        # Сортируем студентов по значению 'order'
        sorted_students = sorted(data, key=lambda student: student["order"])
    else:
        # Если group равен 0, работаем со всеми студентами
        sorted_students = sorted(data, key=lambda student: student["order"])

    id_for_replace = list_of_students[index_to_replace]
    second_student_id = (
        list_of_students[1] if index_to_replace == 0 else list_of_students[0]
    )
    student_for_replace = database.getById(id_for_replace)
    second_student = database.getById(second_student_id)
    current_index = sorted_students.index(student_for_replace)

    if current_index == len(sorted_students) - 1:
        new_duty_student = sorted_students[0]
    else:
        new_duty_student = sorted_students[current_index + 1]

    other_duty_student_id = list_of_students[1 - index_to_replace]
    while new_duty_student["id"] == other_duty_student_id:
        current_index = next(
            (
                index
                for index, student in enumerate(sorted_students)
                if student["id"] == new_duty_student["id"]
            ),
            None,
        )
        if current_index is None or current_index == len(sorted_students) - 1:
            new_duty_student = sorted_students[0]
        else:
            new_duty_student = sorted_students[current_index + 1]

        other_duty_student_id = list_of_students[1 - index_to_replace]

    # Заменяем старого дежурного новым
    list_of_students[index_to_replace] = new_duty_student["id"]

    return list_of_students


@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "success")
def success(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")

    id_ = int(call.data.split("|")[1])
    chat_db = getDb(f"chats/{call.message.chat.id}.json")

    student = chat_db.getById(id_)

    # Увеличиваем количество дежурств у студента на 1
    chat_db.updateById(id_, {"duties": student["duties"] + 1})

    bot.send_message(
        call.message.chat.id,
        f"Студент {student['name']} успешно подежурил, его кол-во дежурств - {student['duties']+1}",
    )
    return bot.answer_callback_query(
        call.id, f"Студент {student['name']} успешно подежурил"
    )


# Обработчик для перерозыгрыша дежурных студентов
@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "reroll")
def reroll(call: telebot.types.CallbackQuery):
    if call.from_user.id not in is_chat_admin(call.message.chat.id):
        return bot.answer_callback_query(call.id, "Вы не администратор 😄")

    markup = telebot.types.InlineKeyboardMarkup()
    chat_db = getDb(f"chats/{call.message.chat.id}.json")
    first, second, index_to_replace, group = (
        int(call.data.split("|")[1]),
        int(call.data.split("|")[2]),
        int(call.data.split("|")[3]),
        int(call.data.split("|")[4]),
    )

    # Получаем новых дежурных студентов
    new_students = get_new_students(chat_db, [first, second], index_to_replace, group)

    first, second = chat_db.getById(new_students[0]), chat_db.getById(new_students[1])

    markup.add(
        telebot.types.InlineKeyboardButton(
            text=f"{first['name']} | {first['duties']}",
            callback_data=f"success|{first['id']}",
        ),
        telebot.types.InlineKeyboardButton(
            text=f"{second['name']} | {second['duties']}",
            callback_data=f"success|{second['id']}",
        ),
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            text="♻️", callback_data=f"reroll|{first['id']}|{second['id']}|0|{group}"
        ),
        telebot.types.InlineKeyboardButton(
            text="♻️", callback_data=f"reroll|{first['id']}|{second['id']}|1|{group}"
        ),
    )
    bot.edit_message_text(
        f"{first['name']} | {second['name']}",
        call.message.chat.id,
        call.message.id,
        reply_markup=markup,
    )


def chat_processer(message: telebot.types.Message):
    bot_id = bot.get_me().id
    isAdmin = False
    for item in bot.get_chat_administrators(message.chat.id):
        if item.user.id == bot_id:
            isAdmin = True
            break
    if isAdmin:
        chat_db = getDb(f"chats/{message.chat.id}.json")
        markup = quick_markup(
            {
                "Общая": {"callback_data": "choose|0"},
                "1 подгруппа": {"callback_data": "choose|1"},
                "2 подгруппа": {"callback_data": "choose|2"},
                "✏️ Редактировать группу": {"callback_data": "edit"},
            }
        )
        bot.reply_to(
            message, "Бот готов к работе, доп. информация - /faq", reply_markup=markup
        )
    else:
        bot.reply_to(
            message,
            "Для начала работы выдайте мне права администратора, затем пропишите /start",
        )


@bot.message_handler(commands=["log"])
def log(message: telebot.types.Message):
    chat_db = getDb(f"chats/{message.chat.id}.json")
    update_order(chat_db)
    data = chat_db.getAll()
    sorted_students = sorted(data, key=lambda x: x["name"])
    msg = "Список студентов: \n"
    for student in sorted_students:
        msg += f"<pre>\t\t{student['duties']} - {student['name']}\n</pre>"
    bot.reply_to(message, msg)


# Обработчик для команды /start
@bot.message_handler(commands=["start"])
def start_handler(message: telebot.types.Message):
    print(message.chat.type)
    if message.chat.type == "supergroup" or message.chat.type == "group":
        return chat_processer(message)
    elif message.chat.type == "private":
        return send_private_schedule(message)


bot.infinity_polling()
