from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
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
import functools as ft

from itertools import zip_longest
from . import configm, lecturesm, scrap_semester_start_end, scrap_lectures, req_post, req_get, limit_text_size, DT_FORMAT, DAYS, scrap_subjects, scrap_multiple_lectures, CREATED_BY, __version__


class MenuEmptyBlock(BoxLayout): pass


class WindowManager(ScreenManager): pass


class RoundedLabel(Label): pass


class RoundedBoxButton(Button): pass


class CSpinner(Spinner): pass


class SideLabel(Label): pass


class MenuButton(Button): pass


class RoundedButton(Button): pass


class MenuItem(Button):
    image_path = ObjectProperty(None)

class MenuItemLabel(Label):
    pass


class SpinBox(BoxLayout): pass


class RoundedDropDown(Button):
    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)
        self.master = master
        self.added_widgets = []
        self.hidding = True
        self.bind(on_release=self.show_hide)

    def show_hide(self, _=None):
        self.hidding = not self.hidding
        command = self.master.remove_widget if self.hidding else self.master.add_widget
        for widget in self.added_widgets:
            command(widget)


class LectureElement(BoxLayout):
    border_color = ListProperty([.15, .15, .15, 1])


class LectureScreen(Screen):
    lecture_list = ObjectProperty(None)
    current_day = BooleanProperty(False)
    one_day_timedelta = dt.timedelta(days=1)

    HIDDEN_SUBJECT_OPACITY = 0.5
    X_SWIPE = sp(15)
    CURRENT_LECTURE_BD = [127/255, 200/255, 84/255, 1]
    NEXT_LECTURE_BD = [200/255, 154/255, 84/255, 1]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loading_layout = LoadingLayout(self)
        self.calendar_layout = CalendarLayout(self, self.custom_date, self.loading_layout)

        self.enable_touch = True
        self.street_addresses = set()

        self.street_addresses_menu = MenuLayout(self)
        self.hidden_lectures_menu = MenuLayout(self)
        self.all_month_menu = MenuLayout(self)
        self.about_menu = MenuLayout(self)

        self.menu = MenuLayout(self)
        self.menu.add_btn_nr("----->", image="images/close.png")
        
        self.menu.add_empty_block()
        self.menu.add_btn_nr("All saved months", self.show_all_months, "images/save.png")
        self.menu.add_btn_nr("Street addresses", self.show_street_addresses, "images/street.png")
        self.menu.add_btn_nr("Shown lectures", self.show_hidden_lectures, "images/list.png")
        self.menu.add_empty_block()
        self.menu.add_btn_nr("ORTUS", ft.partial(webbrowser.open, "https://ortus.rtu.lv"), "images/internet.png")
        self.menu.add_btn_nr("E-studies", ft.partial(webbrowser.open, "https://estudijas.rtu.lv"), "images/internet.png")
        self.menu.add_btn_nr("Sports", ft.partial(webbrowser.open, "https://www.rtu.lv/lv/sports/sporta-nodarbibas/pieteikties-nodarbibam"), "images/internet.png")
        self.menu.add_empty_block()
        self.menu.add_btn_nr("Change course", self.screen_to_courses, "images/back-3.png")
        self.menu.add_btn_nr("About", self.about_menu.show, "images/info.png")

    def show_all_months(self):
        def _exit():
            self.menu.show()
            self.all_month_menu.ids.menu_items.clear_widgets()

        def update():
            _exit()
            self.scrap_multiple_lectures(existing_saves)

        def scrap_missing():
            _exit()
            self.scrap_multiple_lectures(missing_saves)

        def scrap_one_missing(instance):
            _exit()
            self.scrap_multiple_lectures([missing_saves[-int(instance.id[1:])]])
            
        def update_one(instance):
            _exit()
            self.scrap_multiple_lectures([existing_saves[-int(instance.id[1:])]])
            
        self.all_month_menu.add_btn_nr("----->", _exit, "images/close.png")
        self.all_month_menu.add_btn_nr("Update all", update, "images/refresh.png")
        download_btn = self.all_month_menu.add_btn_nr("Download missing", scrap_missing, "images/download.png")
        self.all_month_menu.add_empty_block()
        self.all_month_menu.add_empty_block()
        
        missing_saves, existing_saves = [], []
        month, year = self.semester_start_date.month, self.semester_start_date.year
        save_files = os.listdir(lecturesm.PATH)
        total_saves = abs((self.semester_start_date.year - self.semester_end_date.year) * 12 + self.semester_start_date.month - self.semester_end_date.month) + 1

        for _ in range(total_saves):
            month_text = str(month).rjust(2, '0')

            if os.path.basename(lecturesm.get_file_path(month, year)) not in save_files:
                btn = self.all_month_menu.add_btn(f"{month_text}.{year}\n(Not downloaded!)", scrap_one_missing, "images/small-download.png")
                btn.id = f"m{len(missing_saves)}"
                missing_saves.append((month, year))
            else:
                file_data = lecturesm.read(month, year)
                last_update = dt.datetime.strptime(file_data['lastScrap'], DT_FORMAT)

                btn = self.all_month_menu.add_btn(f"{month_text}.{year}\n(Updated ~{self.get_last_update(last_update)} ago)", update_one, "images/small-refresh-2.png")
                btn.id = f"e{len(existing_saves)}"
                existing_saves.append((month, year))

            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            
        if not missing_saves:
            download_btn.disabled = True
            download_btn.opacity = self.HIDDEN_SUBJECT_OPACITY     

        self.all_month_menu.show()

    def select_date(self):
        self.calendar_layout.show(self.date, self.semester_start_date, self.semester_end_date)

    def hide_show_subject(self, name:str, subject_id:int):
        for child in self.hidden_lectures_menu.ids.menu_items.children:
            if child.id == str(subject_id):
                hidden_subjects = configm.get("hiddenSubjects")
                if name in hidden_subjects:
                    child.opacity = 1
                    hidden_subjects.remove(name)
                else:
                    child.opacity = self.HIDDEN_SUBJECT_OPACITY
                    hidden_subjects.append(name)  
                break

        configm.update()

    def show_hidden_lectures(self):
        def _exit():
            self.menu.show()
            self.refresh()
            self.hidden_lectures_menu.ids.menu_items.clear_widgets()

        def update():
            self.scrap_subjects()
            self.hidden_lectures_menu.ids.menu_items.clear_widgets()
            show_list()

        def show_list():
            hidden_subjects = configm.get("hiddenSubjects")

            self.hidden_lectures_menu.add_btn_nr("----->", _exit, "images/close.png")
            self.hidden_lectures_menu.add_btn_nr("Update", update, "images/refresh-2.png", auto_hide=False)
            self.hidden_lectures_menu.add_empty_block()
            for subject in configm.get("subjects"):
                _id, title = subject["subjectId"], subject["titleLV"]
                btn = self.hidden_lectures_menu.add_btn_nr(title, lambda sub_title=title, sub_id=_id: self.hide_show_subject(sub_title, sub_id), auto_hide=False)
                if title in hidden_subjects:
                    btn.opacity = self.HIDDEN_SUBJECT_OPACITY
                btn.id = str(_id)

        show_list()
        self.hidden_lectures_menu.show()

    def open_menu(self):
        self.menu.show()

    def touched_up(self):
        self.enable_touch = True

    def touched_moved(self, instance, touch=None):
        if self.enable_touch:
            if touch.dx > self.X_SWIPE:
                self.change_day(-1)
                self.enable_touch = False
            elif touch.dx < -self.X_SWIPE:
                self.change_day(1)
                self.enable_touch = False

    def on_enter(self):
        self.auto_refresh_clock = Clock.schedule_once(self.full_refresh)

    def screen_to_courses(self):
        self.manager.current = "courses"
        self.manager.transition.direction = "right"
        self.remove_old_clock()

    def remove_old_clock(self):
        self.auto_refresh_clock.cancel()

    def read_last_scrap_date(self):
        last_scrap_str = lecturesm.get("lastScrap")
        self.last_scrap = None if last_scrap_str is None else dt.datetime.strptime(last_scrap_str, DT_FORMAT)

    def show_street_addresses(self):
        def copy(instance):
            Clipboard.copy(instance.text)

        self.street_addresses_menu.ids.menu_items.clear_widgets()

        self.street_addresses_menu.add_btn_nr("----->", self.menu.show, "images/close.png")
        self.street_addresses_menu.add_empty_block()

        if not self.street_addresses:
            btn = self.street_addresses_menu.add_btn_nr("Nowhere to go...")
            btn.disabled = True
        else:
            for address in self.street_addresses:
                self.street_addresses_menu.add_btn(address, copy, "images/small-street.png", auto_hide=False)

        self.street_addresses_menu.show()

    def free_day_box(self):
        lec_box = LectureElement()

        lec_box.name.text = "--- FREE DAY ---"
        lec_box.room.text = "\( ^o^)/"
        lec_box.time.text = "\(^o^ )/"

        if self.current_day:
            lec_box.border_color = self.CURRENT_LECTURE_BD

        return lec_box
    
    def get_last_update(self, last_time:dt.datetime):
        scraped_time = (dt.datetime.now() - last_time).total_seconds()
        if scraped_time >= 2628000:
            return f"{(scraped_time / 2628000)} months"
        elif scraped_time >= 86400:
            return f"{round(scraped_time / 86400)} days"
        elif scraped_time >= 3600:
            return f"{round(scraped_time / 3600)} hours"
        else:
            return f"{round(scraped_time / 60)} minutes"

    def refresh(self, _=None):
        self.lecture_list.opacity = 0
        self.remove_old_clock()
        self.lecture_list.clear_widgets()
        self.street_addresses.clear()

        if self.last_scrap is not None:
            after_input = self.get_last_update(self.last_scrap)
        else:
            after_input = "NEVER"

        self.ids.last_update.text = f"Updated ~{after_input} ago"
        day_name = dt.datetime.strftime(self.date, '%A')
        self.day.text = f"{self.date.strftime('%d.%m')} - {DAYS.get(day_name)}"
        
        self.current_day = not self.day_offset
        lectures = lecturesm.get(str(self.date))

        self.ids.prev_day.disabled = (self.date - self.semester_start_date).days - (2 * (day_name == "Monday")) <= 0
        self.ids.next_day.disabled = (self.semester_end_date - self.date).days - (2 * (day_name == "Friday")) <= 0

        if not lectures:
            self.lecture_list.add_widget(self.free_day_box())
        else:
            prev_start_time = prev_end_time = refresh_after = 0
            hidden_lectures = []
            hidden_subjects = configm.get("hiddenSubjects")

            time_now = dt.datetime.now()
            
            time_now_time = time_now.hour * 60 + time_now.minute

            is_offseted_day = self.day_offset or self.offset_day
            
            for lecture in lectures:  
                lec_box = LectureElement()
                self.street_addresses.add(lecture["room"]["roomName"])

                # converting to minutes
                start, end = lecture["customStart"], lecture["customEnd"]
                start_time, end_time = start['hour'] * 60 + start['minute'], end['hour'] * 60 + end['minute']

                lec_box.name.text = lecture["eventTempName"]
                lec_box.room.text = lecture["roomInfoText"]
                lec_box.time.text = f"{start['hour']}:{str(start['minute']).rjust(2, '0')} - {end['hour']}:{str(end['minute']).rjust(2, '0')}"

                if any(lecture["eventTempName"].find(sub) != -1 for sub in hidden_subjects):
                    lec_box.opacity = 0.3
                    hidden_lectures.append(lec_box)
                    continue
                
                if not is_offseted_day:  # only if current day is selected
                    if start_time <= time_now_time < end_time:
                        lec_box.border_color = self.CURRENT_LECTURE_BD
                        refresh_after = end_time - time_now_time
                    elif prev_end_time <= time_now_time <= start_time or prev_start_time == start_time:
                        lec_box.border_color = self.NEXT_LECTURE_BD
                        refresh_after = start_time - time_now_time
                        prev_start_time = start_time
                    prev_end_time = end_time

                self.lecture_list.add_widget(lec_box)
            
            if hidden_lectures:
                total_hidden = len(hidden_lectures)
                if len(lectures) == total_hidden:
                    self.lecture_list.add_widget(self.free_day_box())

                message_box = RoundedDropDown(self.lecture_list)
                message_box.text = f"Hidden {total_hidden} lecture{'' if total_hidden == 1 else 's'}"
                message_box.added_widgets = hidden_lectures

                self.lecture_list.add_widget(message_box)

            if refresh_after:  # current lectures start/end
                self.auto_refresh_clock = Clock.schedule_once(self.refresh, refresh_after * 60 - time_now.second + 1)
            else:  # when day ends
                self.auto_refresh_clock = Clock.schedule_once(self.full_refresh, 86401 - ((time_now.hour*3600) + (time_now.minute*60) + time_now.second))
        Clock.schedule_once(self.show_lectures)
    
    def show_lectures(self, _=None):
        self.lecture_list.opacity = 1

    def full_refresh(self, _):
        if not configm.get("semesterProgramId"):
            self.screen_to_courses()
            return

        self.about_menu.ids.menu_items.clear_widgets()
        self.about_menu.add_btn_nr("----->", self.menu.show, "images/close.png")
        self.about_menu.add_empty_block()
        self.about_menu.add_label(f"{configm.get('semester')}")
        self.about_menu.add_label(f"{configm.get('course')}")
        self.about_menu.add_label(f"{configm.get('program')}")
        self.about_menu.add_label(f"Course: {configm.get('courseNum')}  |  Group: {configm.get('groupNum')}")

        self.about_menu.add_empty_block()
        secrete_btn = self.about_menu.add_btn_nr(f"|  App created by: {CREATED_BY}  |", ft.partial(webbrowser.open, "https://www.yout-ube.com/watch?v=j1ArKz8knAU"), auto_hide=False)
        secrete_btn.color = (1, 1 ,1, 0.35)
        secrete_btn.halign = "center"
        self.about_menu.add_label(f"|  Version: {__version__}  |")

        
        self.semester_start_date = dt.datetime.fromtimestamp(configm.get("semesterStart") / 1e3).date()
        self.semester_end_date = dt.datetime.fromtimestamp(configm.get("semesterEnd") / 1e3).date()
        
        self.day_offset = 0
        self.date = dt.datetime.now().date()
        
        if self.semester_start_date > self.date:
            self.date = self.semester_start_date
        elif self.semester_end_date < self.date:
            self.date = self.semester_end_date
        
        self.offset_day = dt.datetime.strftime(self.date, '%A') in ("Sunday", "Saturday")

        self.ids.program.text = f"{configm.get('program')} [{configm.get('courseNum')}/{configm.get('groupNum')}]"
        self.ids.semester.text = configm.get("semester")

        self.skip_if_free_day(1)
        self.date_copy = self.date

        lecturesm.load_month(self.date.month, self.date.year)
        
        if not lecturesm.lectures:
            self.scrap_lectures()
        else:
            self.read_last_scrap_date()
            self.refresh()

    def scrap_lectures(self, _=None, reset_date_in_fail=False):
        def completed(respone, success, _):
            if not success:
                if respone[0] == "OutOfSemester":
                    if reset_date_in_fail:
                        self.reset_date()
                    elif self.day_offset > 0:
                        self.change_day(-1)
                    elif self.day_offset < 0:
                        self.change_day(1)
                return

            lecturesm.load_month(self.date.month, self.date.year)
            self.last_scrap = dt.datetime.strptime(lecturesm.get("lastScrap"), DT_FORMAT)
            self.refresh()

        self.loading_layout.wait_req_post(completed, scrap_lectures, configm.get("semesterProgramId"), self.date.month, self.date.year)

    def scrap_multiple_lectures(self, dates:[(any, any)]):
        def completed(responses, success, _):
            # TODO: if response has error it will take first vlaue of list
            for response in responses:
                if response["success"] and self.date.month == response["month"] and self.date.year == response["year"]:
                    self.last_scrap = dt.datetime.now()
            lecturesm.load_month(self.date.month, self.date.year)
            self.refresh()

        self.loading_layout.wait_req_post(completed, scrap_multiple_lectures, configm.get("semesterProgramId"), dates)

    def scrap_subjects(self):
        def completed(response, success, _):
            pass

        self.loading_layout.wait_req_post(completed, scrap_subjects, configm.get("semesterProgramId"))

    def skip_if_free_day(self, sign:int):
        """ 'sign' value must be -1 or 1 """
        if str(self.date) not in lecturesm.lectures:
            day = dt.datetime.strftime(self.date, '%A')

            match day:
                case "Saturday":
                    skip_days = 1 if sign == -1 or str(self.date + self.one_day_timedelta) in lecturesm.lectures else 2
                case "Sunday":
                    skip_days = 1 if sign == 1 or str(self.date - self.one_day_timedelta) in lecturesm.lectures else 2
                case _:
                    return
                
            self.date += dt.timedelta(days=skip_days) * sign

    def read_new_month(self, old_month, old_year, reset_date_in_fail=False):
        if self.date.month != old_month or self.date.year != old_year:
            lecturesm.load_month(self.date.month, self.date.year)
            if not lecturesm.lectures:
                self.scrap_lectures(reset_date_in_fail=reset_date_in_fail)
            else:
                self.read_last_scrap_date()

    def reset_date(self):
        old_month, old_year = self.date.month, self.date.year
        self.date = self.date_copy
        self.day_offset = 0

        self.read_new_month(old_month, old_year)
        self.skip_if_free_day(1)
        self.refresh()

    def custom_date(self, value):
        old_month, old_year = self.date.month, self.date.year
        self.date = value
        self.day_offset = (value - self.date_copy).days

        self.skip_if_free_day(-1)
        self.read_new_month(old_month, old_year, reset_date_in_fail=True)
        self.refresh()

    def change_day(self, sign):
        old_month, old_year = self.date.month, self.date.year
        self.date += self.one_day_timedelta * sign
        self.day_offset += sign

        self.skip_if_free_day(sign)
        self.read_new_month(old_month, old_year)
        self.refresh()


class CourseSelectScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.loading_layout = LoadingLayout(self)
        self.course_request = {}

    def entry_check(self, _=None):
        if configm.get("semesterProgramId"):
            self.ids.to_lectures_btn.opacity = 1
            self.ids.to_lectures_btn.disabled = 0
        else:
            self.ids.to_lectures_btn.opacity = 0
            self.ids.to_lectures_btn.disabled = 1
        self.refresh()

    def on_enter(self):
        Clock.schedule_once(self.entry_check)

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
        self.loading_layout.wait_req_post(completed, req_get, "https://nodarbibas.rtu.lv/")

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
        self.loading_layout.wait_req_post(completed, url="https://nodarbibas.rtu.lv/findCourseByProgramId", data=self.course_request)

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
        self.loading_layout.wait_req_post(completed, url="https://nodarbibas.rtu.lv/findGroupByCourseId", data=self.course_request | {"courseId": self.course_num})
        
    def selected_group(self, selected):
        if not selected: return
        self.group = selected

    def save(self):
        def semester_start_end_scrap_end(response, success, _):
            if success:
                self.loading_layout.wait_req_post(completed, scrap_semester_start_end, self.semesters.find("option", string=self.semester).get("value"))

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
                # lecturesm.update(time_now.month, time_now.year, lastScrap=time_now.strftime(DT_FORMAT))
                self.screen_to_lectures()

        lecturesm.remove_all()
        time_now = dt.datetime.now()
        semesterProgramId = self.groups_by_group[self.group]["semesterProgramId"]
        self.loading_layout.wait_req_post(semester_start_end_scrap_end, scrap_subjects, semesterProgramId)


class TransparentBaseLayout(RelativeLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.keep_disabled = []

    def disable(self):
        for widget in self.master.walk():
            if isinstance(widget, Button) or isinstance(widget, ScrollView):
                if widget.disabled:
                    self.keep_disabled.append(widget)
                else:
                    widget.disabled = True
    
    def enable(self):
        for widget in self.master.walk():
            if isinstance(widget, Button) or isinstance(widget, ScrollView):
                if widget not in self.keep_disabled:
                    widget.disabled = False

        self.keep_disabled.clear()

    def disable_widgets(self, disable:bool):
        if disable: self.disable()
        else: self.enable()

    # def disable_widgets(self, disable:bool):
    #     for widget in self.master.walk():
    #         if isinstance(widget, Button) or isinstance(widget, ScrollView):
    #             if disable:
    #                 if widget.disabled:
    #                     self.keep_disabled.append(widget)
    #             elif widget in self.keep_disabled:
    #                 widget.disabled = True
    #                 continue
    #             widget.disabled = disable
    #     if not disable:
    #         self.keep_disabled.clear()


class CalendarDayButton(Button):
    bg_color = ListProperty([.15, .15, .15, 1])
    fg_color = ListProperty([1, 1, 1, 1])


class CalendarWeekLabel(Label):
    bg_color = ListProperty([.15, .15, .15, 1])


class CalendarLayout(TransparentBaseLayout):
    one_day_td = dt.timedelta(days=1)
    FREE_DAY_COLOR = [112/255, 14/255, 0, 1]
    CURRENT_DAY_COLOR = [0/255, 84/255, 81/255, 1]
    DEFAULT_DAY_COLOR = [32/255, 36/255, 41/255, 1]

    def __init__(self, master, command, refresh_layout=None, **kw):
        super().__init__(**kw)
        self.master = master
        self.command = command
        self.calendar = calendar.Calendar()
        self.loading_layout = LoadingLayout(self.master) if refresh_layout is None else refresh_layout

    def fill_calendar(self):
        self.ids.date_text.text = f"{str(self.date.month).rjust(2, '0')}-{self.date.year}"
        year, month = str(self.date.year).rjust(2, "0"), str(self.date.month).rjust(2, "0")
        lecture_days = tuple(self.lectures.keys())

        self.ids.prev_month.disabled = self.start_date and self.start_date.month == self.date.month and self.start_date.year == self.date.year
        self.ids.next_month.disabled = self.end_date and self.end_date.month == self.date.month and self.end_date.year == self.date.year

        for (day_num, day_child), day in zip_longest(enumerate(self.ids.days.children[::-1], 1), self.calendar.itermonthdays(self.date.year, self.date.month), fillvalue=0):
            day_num = (day_num + 1) % 7

            if day != 0:
                free_day = f"{year}-{month}-{str(day).rjust(2, '0')}" not in lecture_days
                day_child.text = str(day)
                day_child.bg_color = self.FREE_DAY_COLOR if free_day else self.DEFAULT_DAY_COLOR
                day_child.disabled = (free_day and (not day_num % 7 or not (day_num - 1) % 7)) or (self.ids.prev_month.disabled and day < self.start_date.day) or (self.ids.next_month.disabled and day > self.end_date.day)
            else:
                day_child.text = ""
                day_child.disabled = True
                day_child.bg_color = self.DEFAULT_DAY_COLOR

        if self.date_copy.month == self.date.month and self.date_copy.year == self.date.year:
            self.current_day.bg_color = self.CURRENT_DAY_COLOR
        if self.current_date.month == self.date.month and self.current_date.year == self.date.year:
            self.now_day.fg_color = self.CURRENT_DAY_COLOR
        else:
            self.now_day.fg_color = [1, 1, 1, 0.3 if self.now_day.disabled else 1]

    def show(self, date, start_date=None, end_date=None):
        self.disable_widgets(True)

        self.date = date
        self.date_copy = date
        self.lectures = lecturesm.lectures.copy()
        self.start_date, self.end_date = start_date, end_date

        self.current_date = dt.datetime.now()

        for day_num in range(1, 43):
            day_num = (day_num + 1) % 7
            day_box = CalendarDayButton(on_release=self.day_select)
            self.ids.days.add_widget(day_box)

        self.current_day = self.ids.days.children[::-1][tuple(self.calendar.itermonthdays(self.date.year, self.date.month)).index(self.date.day)]
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

            self.lectures = lecturesm.read(self.date.month, self.date.year)
            self.fill_calendar()

        self.loading_layout.wait_req_post(completed, scrap_lectures, configm.get("semesterProgramId"), self.date.month, self.date.year)

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

    def btn_press_auto_hide(self, command, instance):
        self.hide()
        command(instance)

    def btn_press_auto_hide_nr(self, command):
        self.hide()
        command()

    def add_label(self, name:str):
        btn = MenuItemLabel(text=name)
        self.menu.add_widget(btn)
        return btn
        
    def add_btn(self, name:str, command=lambda: None, image=None, auto_hide=True):
        com = ft.partial(self.btn_press_auto_hide, command) if auto_hide else command
        btn = MenuItem(text=name, image_path=image, on_release=com)
        self.menu.add_widget(btn)
        return btn
    
    def add_btn_nr(self, name:str, command=lambda: None, image=None, auto_hide=True):
        btn = MenuItem(text=name, image_path=image)
        btn.on_release = ft.partial(self.btn_press_auto_hide_nr, command) if auto_hide else command
        self.menu.add_widget(btn)
        return btn
    
    def add_to_menu(self, widget):
        self.menu.add_widget(widget)
    
    def add_empty_block(self):
        block = MenuEmptyBlock()
        self.add_to_menu(block)

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
