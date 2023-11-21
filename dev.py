import shutil
import os
import glob

APP_NAME = "NORTUS"
__version__ = "1.0"
PATH = r"\\wsl.localhost\Ubuntu\home\valdisv\nortus"
DEVICE = "R58RA2H4D4H"
# DEVICE = "f0bd383e"

COPY = (
    "main.py",
    "style.kv",
    "icon.png",
    "nortus",
    "images"
)

class App:
    def __init__(self):
        self.running = True

    def run(self):
        while self.running:
            answer = ""
            print(f" '{APP_NAME}' - DEV TOOL - v.{__version__}  ".center(100, "-"))
            print("1 - Copy files to ubuntu")
            print("2 - Upload app to phone")
            print("3 - Show logs")
            print("4 - Shutdown ubuntu")
            print("5 - Exit")
            while answer not in ("1", "2", "3", "4", "5"):
                answer = input("-> ")
            
            try:
                match int(answer):
                    case 1:
                        self.copy_to_ubuntu()
                    case 2:
                        self.upload_to_phone()
                    case 3:
                        self.log_phone()
                    case 4:
                        self.shut_down_ubuntu()
                    case 5:
                        self.running = False
            except KeyboardInterrupt:
                pass   

    def copy_to_ubuntu(self):
        for _file in COPY:
            if os.path.splitext(_file)[1]:
                shutil.copyfile(_file, os.path.join(PATH, _file))
                print(f"Copied: {_file}")
                continue
            for data in os.listdir(_file):
                if os.path.splitext(os.path.join(_file, data))[1]:
                    shutil.copyfile(os.path.join(_file, data), os.path.join(PATH, _file, data))
                    print(f"Copied: {_file}\\{data}")

    def upload_to_phone(self):
        files = sorted(glob.iglob(os.path.join(PATH, "bin", "*")), key=os.path.getctime, reverse=True)
        os.system(f"adb devices")
        os.system(f"adb -s {DEVICE} install {files[0]}")

    def log_phone(self):
        os.system(f"adb -s {DEVICE} logcat *:S python:D")

    def shut_down_ubuntu(self):
        os.system("wsl --shutdown")


# def ask_y_n(text:str):
#     while True:
#         answer = input(f"{text} [y/n]: ")
#         if answer in ("y", "n"):
#             return answer

if __name__ == "__main__":
    app = App()
    app.run()