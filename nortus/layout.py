from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
# from kivy.uix.dropdown import DropDown
from kivy.uix.spinner import Spinner
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

from kivy.properties import ObjectProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.metrics import sp
from kivy.core.clipboard import Clipboard

import datetime as dt
import calendar
import functools as ft
import threading as td
import bs4
import webbrowser
import os

from itertools import zip_longest
from . import configm, lecturesm, scrap_lectures, req_post, req_get, limit_text_size, DT_FORMAT, DAYS, scrap_subjects


# On phone showed all as empty days in november (calendar).


CURRENT_LECTURE_BD = [127/255, 200/255, 84/255, 1]
NEXT_LECTURE_BD = [200/255, 154/255, 84/255, 1]


class WindowManager(ScreenManager): pass


class RoundedLabel(Label): pass


class RoundedDropDown(Button):
    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)
        self.master = master
        self.widgets = []
        self.hidding = True
        self.bind(on_release=self.show_hide)

    def add_to_list(self, widget):
        self.widgets.append(widget)

    def show_hide(self, _=None):
        self.hidding = not self.hidding
        command = self.master.remove_widget if self.hidding else self.master.add_widget
        for widget in self.widgets:
            command(widget)


class RoundedBoxButton(Button): pass


class CSpinner(Spinner): pass


class SideLabel(Label): pass


class MenuButton(Button): pass


class RoundedButton(Button): pass


class MenuItem(BoxLayout): pass


class SpinBox(BoxLayout): pass


class LectureElement(BoxLayout):
    border_color = ListProperty([.15, .15, .15, 1])


class LectureScreen(Screen):
    lecture_list = ObjectProperty(None)
    current_day = BooleanProperty(False)
    one_day_timedelta = dt.timedelta(days=1)
    x_swipe = sp(15)
    street_addresses = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh_layout = LoadingLayout(self)
        self.calendar_layout = CalendarLayout(self, self.custom_date, self.refresh_layout)
        self.enable_touch = True

        self.street_addresses_menu = MenuLayout(self)
        self.hidden_lectures_menu = MenuLayout(self)

        self.menu = MenuLayout(self)
        self.menu.add_btn("----->")
        self.menu.add_btn("Change course", self.screen_to_courses)
        self.menu.add_btn("Street addresses", self.show_street_addresses)
        self.menu.add_btn("Shown lectures", self.show_hidden_lectures)
        self.menu.add_btn("ORTUS", self.open_ortus)
        self.menu.add_btn("E-studies", self.open_eortus)

    def date_select(self):
        self.calendar_layout.show(self.date.day, self.date.month, self.date.year)

    def hide_subject(self, name:str, subject_id:int):
        hidden_subjects = configm.get("hiddenSubjects")
        if name in hidden_subjects:
            hidden_subjects.remove(name)
            color = 1
        else:
            hidden_subjects.append(name)
            color = 0.5

        for child in self.hidden_lectures_menu.ids.menu_items.children:
            if child.id == str(subject_id):
                child.opacity = color
                break

        configm.write(configm.config)

    def show_hidden_lectures(self):
        self.hidden_lectures_menu.ids.menu_items.clear_widgets()
        self.hidden_lectures_menu.add_btn("----->", lambda: (self.menu.show(), self.refresh()))
        hidden_subjects = configm.get("hiddenSubjects")

        for subject in configm.get("subjects"):
            sub_id = subject["subjectId"]
            sub_title = subject["titleLV"]
            btn = self.hidden_lectures_menu.add_btn(sub_title, lambda _title=sub_title, s_id=sub_id: self.hide_subject(_title, s_id), auto_hide=False)
            if sub_title in hidden_subjects:
                btn.opacity = 0.5
            btn.id = str(sub_id)

        self.hidden_lectures_menu.show()

    def open_menu(self):
        self.menu.show()

    def touched_up(self):
        self.enable_touch = True

    def touched_moved(self, instance, touch=None):
        if self.enable_touch:
            if touch.dx > self.x_swipe:
                self.minus_day()
                self.enable_touch = False
            elif touch.dx < -self.x_swipe:
                self.plus_day()
                self.enable_touch = False

    def on_enter(self):
        self.auto_refresh_clock = Clock.schedule_once(self.full_refresh)

    def screen_to_courses(self):
        self.manager.current = "courses"
        self.manager.transition.direction = "right"
        self.remove_old_clock()

    def open_ortus(self):
        webbrowser.open("https://ortus.rtu.lv")

    def open_eortus(self):
        webbrowser.open("https://estudijas.rtu.lv")

    def remove_old_clock(self):
        self.auto_refresh_clock.cancel()

    def read_last_scrap_date(self):
        last_scrap = lecturesm.get("lastScrap")
        match last_scrap:
            case None:
                self.last_scrap = None
            case _:
                self.last_scrap = dt.datetime.strptime(last_scrap, DT_FORMAT)

    def show_street_addresses(self):
        self.street_addresses_menu.ids.menu_items.clear_widgets()
        self.street_addresses_menu.add_btn("----->", self.menu.show)

        for short_name, long_name in self.street_addresses.items():
            self.street_addresses_menu.add_btn(long_name, lambda: Clipboard.copy(long_name), auto_hide=False)

        self.street_addresses_menu.show()

    def free_day_box(self):
        lec_box = LectureElement()

        lec_box.name.text = "--- FREE DAY ---"
        lec_box.room.text = "\( ^o^)/"
        lec_box.time.text = "\(^o^ )/"

        if self.current_day:
            lec_box.border_color = CURRENT_LECTURE_BD

        return lec_box

    def refresh(self, _=None):
        self.lecture_list.opacity = 0
        self.remove_old_clock()
        self.lecture_list.clear_widgets()
        self.street_addresses.clear()

        if self.last_scrap is not None:
            scraped_time = (dt.datetime.now() - self.last_scrap).total_seconds()
            after_input = ""
            if scraped_time >= 2628000:
                after_input = f"{(scraped_time / 31536000)} months"
            elif scraped_time >= 86400:
                after_input = f"{round(scraped_time / 86400)} days"
            elif scraped_time >= 3600:
                after_input = f"{round(scraped_time / 3600)} hours"
            else:
                after_input = f"{round(scraped_time / 60)} minutes"
        else:
            after_input = "NEVER"

        self.ids.last_update.text = f"Updated ~{after_input} ago"
        self.day.text = f"{self.date.strftime('%d.%m')} - {DAYS.get(dt.datetime.strftime(self.date, '%A'))}"
        
        self.current_day = not self.day_offset
        lectures = lecturesm.get(str(self.date))

        if not lectures:
            self.lecture_list.add_widget(self.free_day_box())
        else:
            prev_start_time = prev_end_time = refresh_after = 0
            hidden_lectures = []
            hidden_subjects = configm.get("hiddenSubjects")

            time_now = dt.datetime.now()
            
            time_now_time = time_now.hour * 60 + time_now.minute

            offseted_day = self.day_offset or self.offset_day
            
            for lecture in lectures:  
                lec_box = LectureElement()
                self.street_addresses[lecture["roomInfoText"]] = lecture["room"]["roomName"]

                # converting to minutes
                start, end = lecture["customStart"], lecture["customEnd"]
                start_time, end_time = start['hour'] * 60 + start['minute'], end['hour'] * 60 + end['minute']

                lec_box.name.text = lecture["eventTempName"]
                lec_box.room.text = lecture["roomInfoText"]
                lec_box.time.text = f"{start['hour']}:{str(start['minute']).rjust(2, '0')} - {end['hour']}:{str(end['minute']).rjust(2, '0')}"

                if any(lecture["eventTempName"].find(sub) != -1 for sub in hidden_subjects):
                    hidden_lectures.append(lec_box)
                    continue
                
                if not offseted_day:  # only if current day is selected
                    if start_time <= time_now_time < end_time:
                        lec_box.border_color = CURRENT_LECTURE_BD
                        refresh_after = end_time - time_now_time
                    elif prev_end_time <= time_now_time <= start_time or prev_start_time == start_time:
                        lec_box.border_color = NEXT_LECTURE_BD
                        refresh_after = start_time - time_now_time
                        prev_start_time = start_time

                    prev_end_time = end_time

                self.lecture_list.add_widget(lec_box)
            
            if hidden_lectures:
                total_hidden = len(hidden_lectures)
                if len(lectures) == total_hidden:
                    self.lecture_list.add_widget(self.free_day_box())
                # message_box = RoundedLabel()
                message_box = RoundedDropDown(self.lecture_list)
                message_box.text = f"Hidden {total_hidden} lecture{'' if total_hidden == 1 else 's'}"
                self.lecture_list.add_widget(message_box)

                for lecture in hidden_lectures:
                    lecture.opacity = 0.3
                    message_box.add_to_list(lecture)

                # message_box.bind(on_release=dropdown.open)
                # dropdown.bind(on_select=lambda instance, x: setattr(message_box, 'text', x))
                
                # self.lecture_list.add_widget(dropdown)

            if refresh_after:  # current lectures start/end
                self.auto_refresh_clock = Clock.schedule_once(self.refresh, refresh_after * 60 - time_now.second + 1)
            else:  # when day ends
                self.auto_refresh_clock = Clock.schedule_once(self.full_refresh, 86401 - ((time_now.hour*3600) + (time_now.minute*60) + time_now.second))
        Clock.schedule_once(self.show_lectures)
    
    def show_lectures(self, _=None):
        self.lecture_list.opacity = 1

    def full_refresh(self, _):
        self.day_offset = 0

        self.date = dt.datetime.now().date()
        self.date_copy = self.date

        if not configm.get("semesterProgramId"):
            self.screen_to_courses()
            return
        if not lecturesm.lectures:
            self.scrap_lectures()

        # if current day is Saturday or Sunday
        self.offset_day = dt.datetime.strftime(self.date, '%A') in ("Sunday", "Saturday")

        self.ids.program.text = f"{configm.get('program')} [{configm.get('courseNum')}/{configm.get('groupNum')}]"
        self.ids.semester.text = configm.get("semester")

        self.skip_if_free_day(1)
        self.read_last_scrap_date()
        self.refresh()

    def scrap_lectures(self, _=None, reset_days_in_fail=False):
        def completed(respone, success, _):
            if not success:
                if respone[0] == "OutOfSemester":
                    if reset_days_in_fail:
                        self.reset_day()
                    elif self.day_offset > 0:
                        self.minus_day()
                    elif self.day_offset < 0:
                        self.plus_day()
                return

            time_now = dt.datetime.now()
            lecturesm.update(self.date.month, self.date.year, lastScrap=time_now.strftime(DT_FORMAT))
            self.last_scrap = time_now
            self.refresh()

        self.refresh_layout.wait_req_post(completed, scrap_lectures, configm.get("semesterProgramId"), self.date.month, self.date.year)

    def skip_if_free_day(self, sign:int):
        """ 'sign' value must be -1 or 1 """
        if str(self.date) not in lecturesm.lectures:
            day = dt.datetime.strftime(self.date, '%A')
            skip_days = 0

            match day:
                case "Saturday":
                    skip_days = 1 if sign == -1 or str(self.date + self.one_day_timedelta) in lecturesm.lectures else 2
                case "Sunday":
                    skip_days = 1 if sign == 1 or str(self.date - self.one_day_timedelta) in lecturesm.lectures else 2

            if skip_days:
                self.date += dt.timedelta(days=skip_days) * sign

    def read_new_month(self, old_month, old_year, reset_days_in_fail=False):
        if self.date.month != old_month or self.date.year != old_year:
            lecturesm.read(self.date.month, self.date.year)
            if not lecturesm.lectures:
                self.scrap_lectures(reset_days_in_fail=reset_days_in_fail)
            else:
                self.read_last_scrap_date()

    def custom_date(self, value):
        old_month, old_year = self.date.month, self.date.year
        self.day_offset = (value - self.date_copy).days
        self.date = value

        self.skip_if_free_day(-1)
        self.read_new_month(old_month, old_year, reset_days_in_fail=True)
        self.refresh()

    def plus_day(self):
        old_month, old_year = self.date.month, self.date.year
        self.date += self.one_day_timedelta
        self.day_offset += 1
        
        self.skip_if_free_day(1)
        self.read_new_month(old_month, old_year)
        self.refresh()

    def minus_day(self):
        old_month, old_year = self.date.month, self.date.year
        self.date -= self.one_day_timedelta
        self.day_offset -= 1

        self.skip_if_free_day(-1)
        self.read_new_month(old_month, old_year)
        self.refresh()

    def reset_day(self):
        old_month, old_year = self.date.month, self.date.year
        self.date = self.date_copy
        self.day_offset = 0

        self.read_new_month(old_month, old_year)
        self.skip_if_free_day(1)
        self.refresh()


class CourseSelectScreen(Screen):
    course_request = {}

    def __init__(self, **kw):
        super().__init__(**kw)
        self.refresh_layout = LoadingLayout(self)

    def entry_check(self, _=None):
        if not configm.get("semesterProgramId"):
            self.ids.to_lectures_btn.opacity = 0
            self.ids.to_lectures_btn.disabled = 1
        else:
            self.ids.to_lectures_btn.opacity = 1
            self.ids.to_lectures_btn.disabled = 0
        
    def on_enter(self):
        Clock.schedule_once(self.entry_check)
        Clock.schedule_once(self.refresh)

    def screen_to_lectures(self):
        self.manager.current = "lectures"
        self.manager.transition.direction = "left"
        self.clear_values()

    def remove_text_and_values(*args):
        for spinner in args:
            spinner.text = ""
            spinner.values = []

    def clear_values(self):
        self.ids.courses_spin.text = ""
        self.remove_text_and_values(
            self.ids.program_spin,
            self.ids.course_num_spin,
            self.ids.group_spin,
        )

    def refresh(self, _=None):
        def completed(response, success, _):
            if not success: return
            
            soup = bs4.BeautifulSoup(response.text, "html.parser")

            self.semesters = soup.find(id="semester-id")
            semester_names = [semester.get_text() for semester in self.semesters.find_all("option")]
            self.semesters_short_names = {f"({num}) {limit_text_size(name)}": name for num, name in enumerate(semester_names, 1)}
            self.semester = semester_names[0]
            self.ids.semester_spin.values = self.semesters_short_names

            self.courses = soup.find(id="program-id")
            self.courses_by_label = {course.get("label"): course.find_all("option") for course in self.courses.find_all("optgroup")}
            self.courses_short_names = {f"({num}) {limit_text_size(name)}": name for num, name in enumerate(self.courses_by_label.keys(), 1)}
            self.ids.courses_spin.values = self.courses_short_names

        self.clear_values()
        self.refresh_layout.wait_req_post(completed, req_get, "https://nodarbibas.rtu.lv/")

    def selected_semester(self, selected):
        if not selected: return
        self.semester = self.semesters_short_names[selected]
        self.ids.courses_spin.text = ""

    def selected_course(self, selected):
        if not selected:
            self.ids.program_spin.text = ""
            return
        
        self.course = self.courses_short_names[selected]
        
        self.programs_short_names = {f"({num}) {limit_text_size(course.get_text())}": course.get_text() for num, course in enumerate(self.courses_by_label[self.course], 1)}
        self.ids.program_spin.values = list(self.programs_short_names.keys())

        self.ids.program_spin.text = ""

    def selected_program(self, selected):
        if not selected:
            self.ids.course_num_spin.text = ""
            return

        def completed(response, success, _):
            if success:
                self.ids.course_num_spin.values = [str(num) for num in response.json()]
            else:
                self.ids.program_spin.text = ""
            self.ids.course_num_spin.text = ""
            
        self.program = self.programs_short_names[selected]
        self.course_request = {
            "semesterId": self.semesters.find("option", string=self.semester).get("value"),
            "programId": self.courses.find("option", string=self.program).get("value")
        }
        self.refresh_layout.wait_req_post(completed, url="https://nodarbibas.rtu.lv/findCourseByProgramId", data=self.course_request)

    def selected_course_num(self, selected):
        if not selected:
            self.ids.group_spin.text = "" 
            return

        def completed(response, success, _):
            if success:
                self.group_response = response.json()
                self.groups_by_group = {group.pop("group"): group for group in self.group_response}
                self.ids.group_spin.values = list(self.groups_by_group.keys())
            else:
                self.ids.course_num_spin.text = ""
            self.ids.group_spin.text = ""

        self.course_num = selected
        self.refresh_layout.wait_req_post(completed, url="https://nodarbibas.rtu.lv/findGroupByCourseId", data=self.course_request | {"courseId": self.course_num})
        
    def selected_group(self, selected):
        if not selected: return
        self.group = selected

    def save(self):
        def scrap_completed(response, success, _):
            if success:
                self.refresh_layout.wait_req_post(completed, scrap_subjects, semesterProgramId)

        def completed(response, success, _):
            if success:
                configm.update(
                    semesterProgramId=semesterProgramId,
                    semester=self.semester,
                    course=self.course,
                    program=self.program,
                    courseNum=self.course_num,
                    groupNum=self.group
                )
                lecturesm.remove_all()
                lecturesm.update(time_now.month, time_now.year, lastScrap=time_now.strftime(DT_FORMAT))
                self.screen_to_lectures()

        time_now = dt.datetime.now()
        semesterProgramId = self.groups_by_group[self.group]["semesterProgramId"]
        self.refresh_layout.wait_req_post(scrap_completed, scrap_lectures, semesterProgramId, time_now.month, time_now.year)


class TransparentBaseLayout(RelativeLayout):
    # keep_disabled = []
    def __init__(self, **kw):
        super().__init__(**kw)
        self.keep_disabled = []

    def disable_widgets(self, disable:bool):
        for widget in self.master.walk():
            if isinstance(widget, Button) or isinstance(widget, ScrollView):
                if disable:
                    if widget.disabled:
                        self.keep_disabled.append(widget)
                elif widget in self.keep_disabled:
                    widget.disabled = True
                    continue
                widget.disabled = disable
        if not disable:
            self.keep_disabled.clear()


class CalendarDayButton(Button):
    bg_color = ListProperty([.15, .15, .15, 1])
    fg_color = ListProperty([1, 1, 1, 1])


class CalendarWeekLabel(Label):
    bg_color = ListProperty([.15, .15, .15, 1])


class CalendarLayout(TransparentBaseLayout):
    one_day_td = dt.timedelta(days=1)
    free_day_color = [112/255, 14/255, 0, 1]
    free_day_color_2 = [148/255, 0/255, 0, 1]
    current_day_color = [0/255, 84/255, 81/255, 1]
    default_day_color = [32/255, 36/255, 41/255, 1]

    def __init__(self, master, command, refresh_layout=None, **kw):
        super().__init__(**kw)
        self.master = master
        self.command = command
        self.calendar = calendar.Calendar()
        self.refresh_layout = LoadingLayout(self.master) if refresh_layout is None else refresh_layout

    def fill_calendar(self):
        self.ids.date_text.text = f"{str(self.date.month).rjust(2, '0')}-{self.date.year}"
        year, month = str(self.date.year).rjust(2, "0"), str(self.date.month).rjust(2, "0")
        lecture_days = tuple(self.lectures.keys())
        for (day_num, day_child), day in zip_longest(enumerate(self.ids.days.children[::-1], 1), self.calendar.itermonthdays(self.date.year, self.date.month), fillvalue=0):
            day_num = (day_num + 1) % 7

            if day != 0:
                free_day = f"{year}-{month}-{str(day).rjust(2, '0')}" not in lecture_days
                day_child.text = str(day)
                day_child.bg_color = self.free_day_color if free_day else self.default_day_color
                day_child.disabled = free_day and (not day_num % 7 or not (day_num - 1) % 7)
            else:
                day_child.text = ""
                day_child.disabled = True
                day_child.bg_color = self.default_day_color
        if self.date_copy.month == self.date.month and self.date_copy.year == self.date.year:
            self.current_day.bg_color = self.current_day_color
        if self.current_date.month == self.date.month and self.current_date.year == self.date.year:
            self.now_day.fg_color = self.current_day_color
        else:
            self.now_day.fg_color = [1, 1, 1, 0.3 if self.now_day.disabled else 1]
            # print(self.now_day.disabled_color)
            # self.now_day.disabled_fg_color = [1, 1, 1, 0.3]

    def show(self, day, month, year):
        self.disable_widgets(True)
        self.month = month
        self.year = year
        self.day = day
        self.lectures = lecturesm.lectures.copy()

        day_num = 0

        self.date = dt.datetime(self.year, self.month, self.day).date()
        self.date_copy = self.date
        self.current_date = dt.datetime.now()

        for day_num in range(1, 43):
            day_num = (day_num + 1) % 7
            day_box = CalendarDayButton(on_release=self.day_select)
            self.ids.days.add_widget(day_box)

        self.current_day = self.ids.days.children[::-1][tuple(self.calendar.itermonthdays(self.date.year, self.date.month)).index(self.day)]
        self.now_day = self.ids.days.children[::-1][tuple(self.calendar.itermonthdays(self.current_date.year, self.current_date.month)).index(self.current_date.day)]
        
        self.fill_calendar()
        self.master.add_widget(self)

    def scrap_lectures(self, _=None):
        def completed(respone, success, _):
            if not success:
                if respone[0] == "OutOfSemester":
                    if (self.date - self.date_copy).days > 0:
                        Clock.schedule_once(self.prev_month, 2)
                    else:
                        Clock.schedule_once(self.next_month, 2)
                return

            time_now = dt.datetime.now()
            lecturesm.update(self.date.month, self.date.year, lastScrap=time_now.strftime(DT_FORMAT))
            self.lectures = lecturesm._read(lecturesm.get_file_path(self.date.month, self.date.year))
            self.fill_calendar()

        self.refresh_layout.wait_req_post(completed, scrap_lectures, configm.get("semesterProgramId"), self.date.month, self.date.year)

    def load_month(self):
        file_path = lecturesm.get_file_path(self.date.month, self.date.year)
        if not os.path.exists(file_path):
            self.scrap_lectures()
        else:
            self.lectures = lecturesm._read(file_path)
            self.fill_calendar()

    def next_month(self, _=None):
        self.date = self.date.replace(day=calendar.monthrange(self.date.year, self.date.month)[1])
        self.date += self.one_day_td
        self.load_month()
    
    def prev_month(self, _=None):
        self.date = self.date.replace(day=1)
        self.date -= self.one_day_td
        self.load_month()

    def reset_date(self):
        self.date = self.date_copy
        self.load_month()

    def day_select(self, instance):
        self.hide()
        self.command(self.date.replace(day=int(instance.text)))

    def hide(self):
        self.disable_widgets(False)
        self.master.remove_widget(self)
        self.ids.days.clear_widgets()
        self.lectures.clear()


class MenuLayout(TransparentBaseLayout):
    def __init__(self, master, **kw):
        super().__init__(**kw)
        self.master = master

    def add_btn(self, name:str, command=lambda: None, auto_hide=True):
        # self.master = master
        btn = MenuItem()
        btn.ids.btn.text = name
        btn.ids.btn.on_release = (lambda: (self.hide(), command())) if auto_hide else command
        self.ids.menu_items.add_widget(btn)
        return btn

    def show(self):
        self.disable_widgets(True)
        self.master.add_widget(self)

    def hide(self):
        self.disable_widgets(False)
        self.master.remove_widget(self)


class LoadingLayout(TransparentBaseLayout):
    def __init__(self, master, **kw):
        super().__init__(**kw)
        self.master = master

    def show(self, info_text:str):
        self.disable_widgets(True)
        self.info.text = info_text
        self.master.add_widget(self)

    def hide(self, _=None):
        self.master.remove_widget(self)
        self.disable_widgets(False)

    def wait_req_post(self, end_func, req_func=req_post, *args, **kwargs):
        def run():
            response, success = req_func(*args, **kwargs)
            if success:
                Clock.schedule_once(self.hide)
            else:
                Clock.schedule_once(ft.partial(cancel, response[0]))
            Clock.schedule_once(ft.partial(end_func, response, success))

        def cancel(response, _=None):
            match response:
                case "ConnectionError":
                    self.info.text = f"No internet connection!"
                case "OutOfSemester":
                    self.info.text = f"Out of semester!"
                case _:
                    self.info.text = f"FAILED!\n{response}"
            Clock.schedule_once(self.hide, 2)

        self.show("Please wait...")
        thread = td.Thread(target=run)
        thread.start()
