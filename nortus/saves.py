import os
import json
import datetime as dt


class ConfigManager:
    CONFIG_SAVE_NAME = "config.json"
    DEFAULT_DATA = {
        "semesterProgramId": None,
        "semester": None,
        "course": None,
        "program": None,
        "courseNum": None,
        "groupNum": None,
        "hiddenSubjects": [],
        "semesterStart": None,
        "semesterEnd": None,
        "subjects": [],
    }

    def __init__(self):
        self.config = {}
        self.read()

    def get(self, key):
        return self.config.get(key)

    def read(self):
        if not os.path.isfile(self.CONFIG_SAVE_NAME):
            self.write(self.DEFAULT_DATA)
            self.config = self.DEFAULT_DATA
            return
        
        with open(self.CONFIG_SAVE_NAME, "r", encoding="utf-8") as r:
            self.config = json.load(r)

    def write(self, data:dict):
        with open(self.CONFIG_SAVE_NAME, "w", encoding="utf-8") as w:
            w.write(json.dumps(data, indent=4))

    def update(self, **kw):
        self.config.update(kw)
        self.write(self.config)

    def clear_semesters_and_holidays(self):
        for dict_name in ("semesters", "holidays"):
            for key in self.config[dict_name]:
                self.config[dict_name][key] = None


class LectureSaveManager:
    PATH = "saves"

    def get_file_path(self, month, year):
        return os.path.join(self.PATH, f"{month}-{year}.json")

    def __init__(self):
        self.lectures = {}
        self.file = ""
        if not os.path.isdir(self.PATH):
            os.mkdir(self.PATH)

    def remove_all(self):
        for lecture_file in os.listdir(self.PATH):
            os.remove(os.path.join(self.PATH, lecture_file))

    def get_all_files(self):
        return os.listdir(self.PATH)

    def get(self, date:str):
        return self.lectures.get(date)
    
    def write(self, lectures:dict, month, year):
        self._write(self.get_file_path(month, year), lectures)

    def update(self, month, year, **kwargs):
        self.lectures.update(kwargs)
        self.write(self.lectures, month, year)

    def _read(self, file_path:str):
        with open(file_path, "r", encoding="utf-8") as _file:
            return json.load(_file)
        
    def _write(self, path, data):
        with open(path, "w", encoding="utf-8") as w:
            w.write(json.dumps(data, indent=4))

    def load_month(self, month, year):
        file_path = self.get_file_path(month, year)
        if not os.path.isfile(file_path):
            self.file = ""
            self.lectures.clear()
            return

        self.file = file_path
        self.lectures = self._read(file_path)

    def read(self, month, year):
        return self._read(self.get_file_path(month, year))

    def load_this_month(self):
        dt_now = dt.datetime.now()
        self.read(dt_now.month, dt_now.year)
