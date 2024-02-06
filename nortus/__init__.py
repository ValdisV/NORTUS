from kivy.lang import Builder
from kivy.app import App

import requests as req
import traceback as tb
import datetime as dt
import functools as ft

from .saves import ConfigManager, LectureSaveManager


CREATED_BY = "ValdisV"
__version__ = "1.1.0"


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


def print_format_exc(exception):
    text = f" CONTROLLED ERROR - {type(exception).__name__} ".center(100, "-")
    print(text)
    print(tb.format_exc())
    print(text)


def limit_text_size(text, max_size:int=MAX_TEXT_SIZE):
    """ Limits text size if it overpasses 'max_size' value. """
    if len(text) > max_size:
        text = text[:max_size-3] + "..."
    return text


def try_execute_req(func):
    """" Tries to execute requests functions. """
    @ft.wraps(func)
    def wrap(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            if response.status_code != 200:
                return (f"Invalid status code [{response.status_code}]", f"Got '{response.status_code}' status code!"), False
            return response, True
        except Exception as exc:
            print_format_exc(exc)
            return (type(exc).__name__, exc), False
    return wrap


@try_execute_req
def req_post(url, data:dict):
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
            response = response.json()
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("NoSubjects", exc), False

    return response, success


def scrap_semester_start_end(semester_id:int):
    response, success = req_post("https://nodarbibas.rtu.lv/getChousenSemesterStartEndDate", {
        "semesterId": semester_id,
    })

    if success:
        try:
            response = response.json()
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("NoSemesterDates", exc), False

    return response, success


def scrap_semester_dates_and_subjects(program_id:int, semester_id:int):
    """ Scraps program subjects and gets semester start and end dates. Returns both in tuple - (dates, subjects). """
    dates_response, success = scrap_semester_start_end(semester_id)
    if not success:
        return dates_response, success
    
    subjects_response, success = scrap_subjects(program_id)
    if not success:
        return subjects_response, success
    
    return (dates_response, subjects_response), success


def scrap_lectures(program_id:int, month:int, year:int):
    response, success = req_post("https://nodarbibas.rtu.lv/getSemesterProgEventList", {
        "semesterProgramId": program_id,
        "year": year,
        "month": month
    })

    if success:
        try:
            response = response.json()
        except req.exceptions.JSONDecodeError as exc:
            response, success = ("OutOfSemester", exc), False
    
    return response, success


def scrap_and_save_lectures(program_id:int, month:int, year:int):
    """ Scraps and saves lectures on device. """
    response, success = scrap_lectures(program_id, month, year)
    if success:
        lecturesm.save_response(month, year, response, dt.datetime.now().strftime(DT_FORMAT))
    return response, success


def scrap_multiple_lectures(program_id:int, dates:[(int, int)]):
    """ Scraps multiple lectures. 'dates' values - [(month, year), ...]. """
    responses = []
    for month, year in dates:
        response, success = scrap_and_save_lectures(program_id, month, year)
        if not success:
            responses = response
            break
        responses.append({"month": month, "year": year, "response": response})
    return responses, success


class NORTUSApp(App):
    def build(self):
        from .layout import WindowManager
        return Builder.load_file("style.kv")
