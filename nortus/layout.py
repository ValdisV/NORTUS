from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

# from kivymd.uix.pickers import MDDatePicker

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

from itertools import zip_longest
from . import configm, lecturesm, scrap_lectures, req_post, req_get, limit_text_size, DT_FORMAT, DAYS, scrap_subjects



# Atslēdz swipe tad kad logs ir disabled (LectureScreen)
# when auto refresh check if calendar is not open and isn't already refreshing



CURRENT_LECTURE_BD = [127/255, 200/255, 84/255, 1]
NEXT_LECTURE_BD = [200/255, 154/255, 84/255, 1]


class WindowManager(ScreenManager): pass


class RoundedLabel(Label): pass


class RoundedBoxButton(Button): pass


class CSpinner(Spinner): pass


class SideLabel(Label): pass


class MenuButton(Button): pass


class RoundedButton(Button): pass


class MenuItem(BoxLayout): pass


class SpinBox(BoxLayout): pass


class LectureElement(BoxLayout):
    border_color = ListProperty([.15, .15, .15, 1])


class LectureElementBtn(BoxLayout):
    border_color = ListProperty([.15, .15, .15, 1])


class LectureScreen(Screen):
    lecture_list = ObjectProperty(None)
    current_day = BooleanProperty(False)
    one_day_timedelta = dt.timedelta(days=1)
    x_swipe = sp(10)
    street_addresses = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calendar_layout = CalendarLayout(self, self.custom_date)
        self.refresh_layout = LoadingLayout(self)
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
        
    def custom_date(self, value):
        old_month, old_year = self.date.month, self.date.year
        self.day_offset = (value - self.date).days
        self.date = value
        
        self.skip_if_free_day(-1)
        self.read_new_month(old_month, old_year, reset_days_in_fail=True)
        self.refresh()

    def date_select(self):
        # calendar = MDDatePicker(year=self.date.year, month=self.date.month, day=self.date.day)
        # calendar.bind(on_save=self.custom_date)
        # calendar.open()
        self.calendar_layout.show(self.date.day, self.date.month, self.date.year)

    def hide_subject(self, name:str, subject_id:int):
        hidden_subjects = configm.get("hiddenSubjects")
        # print(subject_id)
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
            self.street_addresses_menu.add_btn(f"{short_name}  :  {long_name}", lambda: Clipboard.copy(long_name), auto_hide=False)

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

        if self.current_day and self.date_copy.month == 11 and self.date_copy.day == 29:
            lec_box = LectureElementBtn()
            lec_box.name.text = "STINKY BOYS BIRTHDAY!!!"
            lec_box.room.text = "NIPAAAAAA"
            lec_box.time.text = "NOW HE'S OLD"
            lec_box.ids.name.on_release = lambda: webbrowser.open("https://www.youtube.com/watch?v=fkF23cuqW08")
            lec_box.border_color = [1, 0, 0, 1]
            self.lecture_list.add_widget(lec_box)

        if not lectures:
            self.lecture_list.add_widget(self.free_day_box())
        else:
            prev_start_time = prev_end_time = refresh_after = hidden = 0
            hidden_subjects = configm.get("hiddenSubjects")

            time_now = dt.datetime.now()
            
            time_now_time = time_now.hour * 60 + time_now.minute
            # time_now_time = time_now_time - 90

            offseted_day = self.day_offset or self.offset_day
            
            for lecture in lectures:
                if any(lecture["eventTempName"].find(sub) != -1 for sub in hidden_subjects):
                    hidden += 1
                    continue
                
                lec_box = LectureElement()
                self.street_addresses[lecture["roomInfoText"]] = lecture["room"]["roomName"]

                # converting to minutes
                start, end = lecture["customStart"], lecture["customEnd"]
                start_time, end_time = start['hour'] * 60 + start['minute'], end['hour'] * 60 + end['minute']

                lec_box.name.text = lecture["eventTempName"]
                lec_box.room.text = lecture["roomInfoText"]
                lec_box.time.text = f"{start['hour']}:{str(start['minute']).rjust(2, '0')} - {end['hour']}:{str(end['minute']).rjust(2, '0')}"

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
            
            if hidden:
                if len(lectures) == hidden:
                    self.lecture_list.add_widget(self.free_day_box())
                message_box = RoundedLabel()
                message_box.text = f"Hidden {hidden} lecture{'' if hidden == 1 else 's'}"
                self.lecture_list.add_widget(message_box)

            if refresh_after:  # current lectures start/end
                self.auto_refresh_clock = Clock.schedule_once(self.refresh, refresh_after * 60 - time_now.second + 1)
            else:  # when day ends
                self.auto_refresh_clock = Clock.schedule_once(self.full_refresh, 86401 - ((time_now.hour*3600) + (time_now.minute*60) + time_now.second))

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
        # self.date_select()
        # self.refresh_layout.show("Hmmmmm")

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
        if str(self.date) not in lecturesm.lectures:
            day = dt.datetime.strftime(self.date, '%A')
            skip_days = 0

            match day:
                case "Sunday":
                    skip_days = 1 if sign == 1 else 2
                case "Saturday":
                    skip_days = 2 if sign == 1 else 1
                    
            if skip_days:
                self.date += dt.timedelta(days=skip_days) * sign

    def read_new_month(self, old_month, old_year, reset_days_in_fail=False):
        if self.date.month != old_month or self.date.year != old_year:
            lecturesm.read(self.date.month, self.date.year)
            if not lecturesm.lectures:
                self.scrap_lectures(reset_days_in_fail=reset_days_in_fail)
            else:
                self.read_last_scrap_date()

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
        # self.selected_data.clear()
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
        # self.master.disabled = True
        # self.disabled = False
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


class CalendarWeekLabel(Label):
    bg_color = ListProperty([.15, .15, .15, 1])


class CalendarLayout(TransparentBaseLayout):
    # keep_disabled = []
    one_day_td = dt.timedelta(days=1)
    free_day_color = [255/255, 70/255, 25/255, 1]
    current_day_color = [50/255, 131/255, 50/255, 1]
    default_day_color = [32/255, 36/255, 41/255, 1]

    # def on_touch_down(self, touch):
    #     print(touch)

    def __init__(self, master, command, **kw):
        super().__init__(**kw)
        self.master = master
        self.command = command
        self.calendar = calendar.Calendar()

    # def disable_widgets(self, disable:bool):
    #     # self.master.disabled = True
    #     # self.disabled = False
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

    def fill_calendar(self):
        self.ids.date_text.text = f"{str(self.date.month).rjust(2, '0')}-{self.date.year}"
        for day_child, day in zip_longest(self.ids.days.children[::-1], self.calendar.itermonthdays(self.date.year, self.date.month), fillvalue=0):
            if day != 0:
                day_child.text = str(day)
                day_child.disabled = False
            #     if self.date_copy.day == day:
            #         day_child.background_color = (0, 1, 0) if self.date_copy.month == self.date.month and self.date_copy.year == self.date.year else (0.5, 0.5, 0.)
            else:
                day_child.text = ""
                day_child.disabled = True

        self.current_day.bg_color = self.current_day_color if self.date_copy.month == self.date.month and self.date_copy.year == self.date.year else self.default_day_color
            
            
    def show(self, day, month, year):
        self.disable_widgets(True)
        self.month = month
        self.year = year
        self.day = day

        day_num = 0

        self.date = dt.datetime(self.year, self.month, self.day).date()
        self.date_copy = self.date

        # for day_num, day in enumerate(self.calendar.itermonthdays(year, month), 1):
        for day_num in range(1, 43):
            day_num = (day_num + 1) % 7
            day_box = CalendarDayButton(on_release=self.day_select)
            
            self.ids.days.add_widget(day_box)
            
            day_box.bg_color = self.free_day_color if not day_num % 7 or not (day_num - 1) % 7 else self.default_day_color

        self.current_day = self.ids.days.children[::-1][tuple(self.calendar.itermonthdays(self.date.year, self.date.month)).index(self.day)]

        self.fill_calendar()
        self.master.add_widget(self)

    def next_month(self):
        # print(calendar.monthrange(self.date.year, self.date.month))
        self.date = self.date.replace(day=calendar.monthrange(self.date.year, self.date.month)[1])
        self.date += self.one_day_td
        self.fill_calendar()
    
    def prev_month(self):
        self.date = self.date.replace(day=1)
        self.date -= self.one_day_td
        self.fill_calendar()

    def reset_date(self):
        self.date = self.date_copy
        self.fill_calendar()

    def day_select(self, instance):
        
        self.hide()
        self.command(self.date.replace(day=int(instance.text)))

    def hide(self):
        self.disable_widgets(False)
        self.master.remove_widget(self)
        self.ids.days.clear_widgets()


class MenuLayout(TransparentBaseLayout):
    # keep_disabled = []

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

    # def disable_widgets(self, disable:bool):
    #     for widget in self.master.walk():
    #         if isinstance(widget, Button):
    #             if disable:
    #                 if widget.disabled:
    #                     self.keep_disabled.append(widget)
    #             elif widget in self.keep_disabled:
    #                 widget.disabled = True
    #                 continue
    #             widget.disabled = disable
    #     if not disable:
    #         self.keep_disabled.clear()

    def show(self):
        self.disable_widgets(True)
        self.master.add_widget(self)

    def hide(self):
        self.disable_widgets(False)
        self.master.remove_widget(self)


class LoadingLayout(TransparentBaseLayout):
    # keep_disabled = []

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
        # self.master.update()

    # def disable_widgets(self, disable:bool):
    #     for widget in self.master.walk():
    #         if isinstance(widget, Button):
    #             if disable:
    #                 if widget.disabled:
    #                     self.keep_disabled.append(widget)
    #             elif widget in self.keep_disabled:
    #                 widget.disabled = True
    #                 continue
    #             widget.disabled = disable
    #     if not disable:
    #         self.keep_disabled.clear()

    def wait_req_post(self, end_func, req_func=req_post, *args, **kwargs):
        def run():
            response, success = req_func(*args, **kwargs)
            if success:
                Clock.schedule_once(self.hide)
            else:
                Clock.schedule_once(ft.partial(cancel, response[0]))
            Clock.schedule_once(ft.partial(end_func, response, success))

        def cancel(response, _=None):
            if response[0] == "ConnectionError":
                self.info.text = f"No internet\nconnection!"
            else:
                self.info.text = f"FAILED!\n{response}"
            Clock.schedule_once(self.hide, 2)

        self.show("Please wait...")
        thread = td.Thread(target=run)
        thread.start()
