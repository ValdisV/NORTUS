from kivy.lang import Builder
from kivy.app import App

import requests as req
import traceback as tb
import datetime as dt
import bs4

from .saves import ConfigManager, LectureSaveManager

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DT_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

MAX_TEXT_SIZE = 40
DAYS = {
    "Monday": "Pirmd.",
    "Tuesday": "Otrd.",
    "Wednesday": "Trešd.",
    "Thursday": "Ceturd.",
    "Friday": "Piektd.",
    "Saturday": "Sestd.",
    "Sunday": "Svētd.",
}

configm = ConfigManager()
configm.read()

lecturesm = LectureSaveManager()
lecturesm.read_this_month()


def try_execute_req(func):
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



def scrap_lectures(program_id:int, month:int, year:int):
    response, success = req_post("https://nodarbibas.rtu.lv/getSemesterProgEventList", {
        "semesterProgramId": program_id,
        "year": year,
        "month": month
    })

    if success:
        lecture_dates = {"lastScrap": None}
        
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


class TxtWeb:
    def __init__(self, _file:str):
        with open(_file, "r", encoding="utf-8") as w:
            self.data = w.read()

    @property
    def text(self):
        return self.data


def get_semesters():
    # response, success = req_get("https://www.rtu.lv/lv/studijas/akademiska-gada-kalendars")
    
    success = True
    response = TxtWeb("web.txt")

    if success:
        semesters = configm.get("semesters")
        holidays = configm.get("holidays")

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        event_list = soup.find(class_="highlight_contents uce-iframe-content-container").find_all("p")

        for events in event_list:
            for event in events.text.split("\n"):
                event_splited = event.split(" ")

                match event_splited[0]:
                    case "t.sk.":
                        for holiday in holidays.keys():
                            if event.find(holiday) != -1 and holidays.get(holiday) is None:
                                holidays[holiday] = [str(dt.datetime.strptime(date, "%d.%m.%Y.").strftime(DT_FORMAT).date()) for date in event_splited[-1].split(",")[0].split("\u2013")]
                                break
                    case _:
                        for semester in semesters.keys():
                            if event.find(semester) != -1 and semesters.get(semester) is None:
                                semesters[semester] = [str(dt.datetime.strptime(date, "%d.%m.%Y.").strftime(DT_FORMAT).date()) for date in event_splited[-1].split(",")[0].split("\u2013")]
                                break

        configm.update(semesters=semesters, holidays=holidays)

    return response, success


class NortusApp(App):
    def build(self):
        from .layout import WindowManager
        return Builder.load_file("style.kv")
