import os
from io import BytesIO

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


url = os.getenv("SCHEDULE_FILE_LINK")


def is_schedule(df):
    # Проверка, является ли страница страницей с расписанием
    return "№ урока" in df.values.astype(str).flatten().tolist()



def get_schedule():
    xls = load_schedule()
    return parse_schedule(xls)

def load_schedule():
    response = requests.get(url)
    return pd.read_excel(BytesIO(response.content), sheet_name=None)

def parse_schedule(xls):
    schedule = {}
    for sheet_name, df in xls.items():
        if not is_schedule(df):
            continue
        groups = df.iloc[6, 3 : df.shape[1] : 3].values
        for i, group in enumerate(groups):
            schedule = parse_group_schedule(df, i, group, schedule)
    return schedule

def parse_group_schedule(df, i, group, schedule):
    day = None
    for j, row in df.iterrows():
        if j < 8:
            continue
        if pd.notna(row["Unnamed: 1"]):
            day = row["Unnamed: 1"]
        if pd.isna(day):
            continue
        if lesson_data := get_lesson_data(row, i):
            lesson_num, discipline, teacher, room = lesson_data
            schedule = update_schedule(group, day, lesson_num, discipline, teacher, room, schedule)
    return reorder_schedule(group, schedule)

def get_lesson_data(row, i):
    lesson_num = row["Unnamed: 2"]
    if "пара" in str(lesson_num).lower():
        lesson_num = str(lesson_num).replace("пара", "")
    discipline = row.iloc[3 + i * 3]
    teacher = row.iloc[4 + i * 3]
    room = row.iloc[5 + i * 3]
    if pd.notna(lesson_num) and pd.notna(discipline):
        return lesson_num, discipline, teacher, room

def update_schedule(group, day, lesson_num, discipline, teacher, room, schedule):
    if group not in schedule:
        schedule[group] = {}
    if day not in schedule[group]:
        schedule[group][day] = {}
    schedule[group][day][lesson_num] = {
        "discipline": discipline,
        "teacher": teacher,
        "room": room,
    }
    return schedule

def reorder_schedule(group, schedule):
    for group, value in schedule.items():
        new_schedule = {
            idx: schedule[group][date_str]
            for idx, date_str in enumerate(value.keys())
        }
        schedule[group] = new_schedule
    return schedule