# Описание
Бот предназначен для удобного просмотра расписания и организации дежурств студентов в учебных группах. 

* Он работает с Telegram и предоставляет два режима использования:
    - Личные сообщения с ботом - просмотр расписания.
    - Групповой чат с ботом - управление дежурствами студентов.

# Как это работает?
**Личные сообщения:** 
  - Пользователи отправляют боту команду /start в личные сообщения.
  - Пользователь выбирает интересующую группу и просматривает расписание на неделю.

**Учет дежурств:**
  -  Администратор добавляет бота в группу и предоставляет ему права администратора.
  -  В группе администратор добавляет студентов, указывая их имя, фамилию, группу и количество дежурств.
  -  Администратор активирует бота, отправив команду /start в групповой чат.
  -  Бот предоставляет администратору список доступных функций для управления дежурствами.
  -  Администратор может назначать группы студентам, устанавливать количество дежурств и выбирать дежурных студентов.
  
# Основные функции бота:
* **Добавление студента:** Администратор может добавить нового студента в список, указав его имя и фамилию.
* **Редактирование группы студента:** Администратор может назначить группу студента.
* **Установка количества дежурств:** Администратор может вручную установить количество дежурств для каждого студента.
* **Выбор дежурных студентов:** Бот автоматически выбирает двух студентов для дежурства, учитывая их количество дежурств и исключая тех, кто уже дежурил.
* **Перевыбор дежурных:** Администратор может провести перевыбор дежурных, если это необходимо.


# Как запустить бота:
   - Создайте нового бота через @BotFather в Telegram и получите его токен.
   - Установите все необходимые зависимости, указанные в requirements.txt.
   - В файле .env укажите токен своего бота: BOT_TOKEN=ваш_токен.
   - Запустите бота, используя команду python3 main.py.

# Важное примечание:
* Бот должен быть администратором в группе, чтобы иметь доступ к списку студентов и проводить выбор дежурных.
* Необходимо установить данные о студентах, их группах и количество дежурств перед началом использования бота.
* Внимательно следите за качеством данных о студентах, чтобы избежать ошибок в процессе выбора дежурных.
* Если возникнут проблемы или вопросы по использованию бота, обратитесь к документации или свяжитесь с разработчиками для получения помощи.