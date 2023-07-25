import os
from io import BytesIO

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

CACHE = {}

url1 = os.getenv("SCHEDULE1")
url2 = os.getenv("SCHEDULE2")
url3 = os.getenv("SCHEDULE3")


def load_schedule(url):
    etag = CACHE.get(url, {}).get("etag")
    headers = {"If-None-Match": etag} if etag else {}
    response = requests.get(url, headers=headers)

    # Если данные не изменились, возвращаем сохраненный DataFrame
    if response.status_code == 304:
        print("CACHED")
        return CACHE[url]["data"]

    # Иначе обновляем кэш и возвращаем новые данные
    CACHE[url] = {
        "etag": response.headers.get("ETag"),
        "data": pd.read_excel(BytesIO(response.content), sheet_name=None),
    }
    print("NEW")
    return CACHE[url]["data"]


def is_schedule(df):
    # Проверка, является ли страница страницей с расписанием
    return "№ урока" in df.values.astype(str).flatten().tolist()


def merge_schedules(*schedules):
    # Объединяем все расписания в одно
    merged_schedule = schedules[0].copy()
    for schedule in schedules[1:]:
        for group, days in schedule.items():
            if group not in merged_schedule:
                merged_schedule[group] = days
            else:
                for day, lessons in days.items():
                    if day not in merged_schedule[group]:
                        merged_schedule[group][day] = lessons
                    else:
                        merged_schedule[group][day].update(lessons)
    return merged_schedule


def get_schedule():
    xls1 = load_schedule(url1)
    xls2 = load_schedule(url2)
    xls3 = load_schedule(url3)
    schedule1 = parse_schedule(xls1)
    schedule2 = parse_schedule(xls2)
    schedule3 = parse_schedule(xls3)
    return merge_schedules(schedule1, schedule2, schedule3)


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
            schedule = update_schedule(
                group, day, lesson_num, discipline, teacher, room, schedule
            )
    return reorder_schedule(group, schedule)


def get_lesson_data(row, i):
    lesson_num = row["Unnamed: 2"]
    if "пара" in str(lesson_num).lower():
        lesson_num = str(lesson_num).replace("пара", "")
    discipline = row.iloc[3 + i * 3] if 3 + i * 3 < len(row) else None
    teacher = row.iloc[4 + i * 3] if 4 + i * 3 < len(row) else None
    room = row.iloc[5 + i * 3] if 5 + i * 3 < len(row) else None
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
            idx: schedule[group][date_str] for idx, date_str in enumerate(value.keys())
        }
        schedule[group] = new_schedule
    return schedule
