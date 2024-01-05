from kivy.lang import Builder
from kivy.app import App

import requests as req
import traceback as tb
import datetime as dt
import functools as ft

from .saves import ConfigManager, LectureSaveManager


CREATED_BY = "ValdisV"
__version__ = "1.0.0"


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DT_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

MAX_TEXT_SIZE = 40
DAYS = {
    "Monday": "Mon.",
    "Tuesday": "Tues.",
    "Wednesday": "Wednes.",
    "Thursday": "Thurs.",
    "Friday": "Fri.",
    "Saturday": "Satur.",
    "Sunday": "Sun.",
}

configm = ConfigManager()
configm.read()

lecturesm = LectureSaveManager()


def try_execute_req(func):
    @ft.wraps(func)
    def wrap(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            if response.status_code != 200:
                return (f"Invalid status code [{response.status_code}]", f"Got '{response.status_code}' status code!"), False
            return response, True
        except Exception as exc:
            print(tb.format_exc())
            return (type(exc).__name__, exc), False
    return wrap


def limit_text_size(text, max_size=MAX_TEXT_SIZE):
    if len(text) > max_size:
        text = text[:max_size-3] + "..."
    return text


@try_execute_req
def req_post(url, data):
    return req.post(url, data=data)


@try_execute_req
def req_get(url):
    return req.post(url)


def scrap_subjects(program_id:int):
    response, success = req_post("https://nodarbibas.rtu.lv/getSemProgSubjects", {
        "semesterProgramId": program_id
    })

    if success:
        try:
            configm.update(subjects=response.json())
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("NoSubjects", exc), False

    return response, success


def scrap_semester_start_end(semester_id):
    response, success = req_post("https://nodarbibas.rtu.lv/getChousenSemesterStartEndDate", {
        "semesterId": semester_id,
    })

    if success:
        try:
            data = response.json()
            configm.update(semesterStart=data["startDate"], semesterEnd=data["endDate"])
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("NoSemesterDates", exc), False

    return response, success


def scrap_lectures(program_id:int, month:int, year:int):
    response, success = req_post("https://nodarbibas.rtu.lv/getSemesterProgEventList", {
        "semesterProgramId": program_id,
        "year": year,
        "month": month
    })

    if success:
        lecture_dates = {"lastScrap": dt.datetime.now().strftime(DT_FORMAT)}
        
        try:
            for lecture in response.json():
                date = str(dt.datetime.fromtimestamp(lecture["eventDate"] / 1e3).date())
                if date not in lecture_dates:
                    lecture_dates[date] = []
                lecture_dates[date].append(lecture)

            lecturesm.write(lecture_dates, month, year)
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("OutOfSemester", exc), False
    
    return response, success


def scrap_multiple_lectures(program_id:int, dates:list):
    responses = []
    for month, year in dates:
        response, success = scrap_lectures(program_id, month, year)
        responses.append({"month": month, "year": year, "response": response, "success": success})
        if not success:
            break
    return responses, success


class TxtWeb:
    def __init__(self, _file:str):
        with open(_file, "r", encoding="utf-8") as w:
            self.data = w.read()

    @property
    def text(self):
        return self.data


class NORTUSApp(App):
    def build(self):
        from .layout import WindowManager
        return Builder.load_file("style.kv")
