import os
import json
import datetime as dt


class ConfigManager:
    """ Responsible for selected programs' basic data writing and reading. """

    CONFIG_SAVE_NAME = "config.json"
    DEFAULT_DATA = {
        "autoUpdate": True,
        "semesterProgramId": None,
        "semester": None,
        "course": None,
        "program": None,
        "courseNum": None,
        "groupNum": None,
        "semesterStart": None,
        "semesterEnd": None,
        "hiddenSubjects": [],
        "subjects": [],
    }

    def __init__(self):
        self.config = {}
        self.read()

    def reset_save(self):
        """ Writes default config values. """
        self.write(self.DEFAULT_DATA)
        self.config = self.DEFAULT_DATA

    def get(self, key:str):
        """ Gets values from config. """
        return self.config.get(key)

    def read(self):
        """ Reads and loads config save. """
        if not os.path.isfile(self.CONFIG_SAVE_NAME):
            self.reset_save()
            return
        
        with open(self.CONFIG_SAVE_NAME, "r", encoding="utf-8") as r:
            self.config = json.load(r)

    def write(self, data:dict):
        """ Saves config. Doesn't update the already loaded file. To save and update files call the 'update' function. """
        with open(self.CONFIG_SAVE_NAME, "w", encoding="utf-8") as w:
            w.write(json.dumps(data, indent=4))

    def update(self, **kwargs):
        """" Updates config file. """
        self.config.update(kwargs)
        self.write(self.config)


class LectureSaveManager:
    """ Responsible for lecture writing and reading. """

    PATH = "saves"

    def __init__(self):
        self.lectures, self.file = {}, ""
        if not os.path.isdir(self.PATH):
            os.mkdir(self.PATH)

    def _read(self, file_path:str):
        with open(file_path, "r", encoding="utf-8") as _file:
            return json.load(_file)
        
    def _write(self, file_path:str, data:dict):
        with open(file_path, "w", encoding="utf-8") as w:
            w.write(json.dumps(data, indent=4))

    def read(self, month:int, year:int):
        """ Returns save file values. Doesn't overwrite loaded file. To load a file call the 'load_month' function. """
        return self._read(self.get_file_path(month, year))
    
    def write(self, lectures:dict, month:int, year:int):
        """ Saves lectures. Doesn't update the already loaded file. To save and update files call the 'update' function. """
        self._write(self.get_file_path(month, year), lectures)

    def remove_all(self):
        """ Deletes all saves. """
        for lecture_file in os.listdir(self.PATH):
            os.remove(os.path.join(self.PATH, lecture_file))

    def get_all_files(self):
        """ Returns all save file names. """
        return os.listdir(self.PATH)
    
    def get_file_path(self, month:int, year:int):
        """ Returns save file path. """
        return os.path.join(self.PATH, f"{month}-{year}.json")

    def get(self, key:str):
        """ Returns value from currently loaded save. """
        return self.lectures.get(key)

    def update(self, month:int, year:int, **kwargs):
        """ Updates and saves loaded save. """
        self.lectures.update(kwargs)
        self.write(self.lectures, month, year)

    def load_month(self, month:int, year:int):
        """ Loads month from saves. """
        file_path = self.get_file_path(month, year)
        if not os.path.isfile(file_path):
            self.file = ""
            self.lectures.clear()
            return

        self.file = file_path
        self.lectures = self._read(file_path)

    def load_this_month(self):
        """" Loads current month. """
        time_now = dt.datetime.now()
        self.load_month(time_now.month. time_now.year)

    def save_response(self, month:int, year:int, lectures:dict, scrap_time:str):
        """" Saves from requets post recived lectures. """
        lecture_dates = {"lastScrap": scrap_time}

        for lecture in lectures:
            date = str(dt.datetime.fromtimestamp(lecture["eventDate"] / 1e3).date())
            if date not in lecture_dates:
                lecture_dates[date] = []
            lecture_dates[date].append(lecture)

        self.write(lecture_dates, month, year)
