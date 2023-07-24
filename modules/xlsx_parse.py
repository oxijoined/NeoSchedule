import pandas as pd
import requests
from io import BytesIO
from dotenv import load_dotenv
import os

load_dotenv()


url = os.getenv("SCHEDULE_FILE_LINK")


def is_schedule(df):
    # Проверка, является ли страница страницей с расписанием
    return "№ урока" in df.values.astype(str).flatten().tolist()


def get_schedule():
    # Загрузка файла Excel
    response = requests.get(url)
    xls = pd.read_excel(BytesIO(response.content), sheet_name=None)
    # xls = pd.read_excel(open("schedule2.xlsx", "rb"), sheet_name=None)

    # Создание словаря для расписания
    schedule = {}

    # Обработка каждого листа в файле
    for sheet_name, df in xls.items():
        # Проверка, является ли лист страницей с расписанием
        if not is_schedule(df):
            continue

        # Получение списка групп
        groups = df.iloc[6, 3 : df.shape[1] : 3].values

        # Парсинг расписания для каждой группы
        for i, group in enumerate(groups):
            day = None
            for j, row in df.iterrows():
                if j < 8:
                    continue
                if pd.notna(row["Unnamed: 1"]):
                    day = row["Unnamed: 1"]
                if pd.isna(day):
                    continue
                lesson_num = row["Unnamed: 2"]
                if "пара" in str(lesson_num).lower():
                    lesson_num = str(lesson_num).replace("пара", "")
                discipline = row.iloc[3 + i * 3]
                teacher = row.iloc[4 + i * 3]
                room = row.iloc[5 + i * 3]

                if pd.notna(lesson_num) and pd.notna(discipline):
                    if group not in schedule:
                        schedule[group] = {}
                    if day not in schedule[group]:
                        schedule[group][day] = {}
                    schedule[group][day][lesson_num] = {
                        "discipline": discipline,
                        "teacher": teacher,
                        "room": room,
                    }
    for group in schedule:
        new_schedule = {}
        for idx, date_str in enumerate(schedule[group].keys()):
            new_schedule[idx] = schedule[group][date_str]
        schedule[group] = new_schedule

    return schedule
