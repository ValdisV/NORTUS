import shutil
import os
import glob
try:
    from dev_data import UBUNTU_APP_PATH, DEVICE
except ImportError:
    pass


APP_NAME = "NORTUS"
__version__ = "1.0"
COPY = (
    "main.py",
    "style.kv",
    ["build_files", "icon.png"],
    ["build_files", "buildozer.spec"],
    ["build_files", "presplash.png"],
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
            print("4 - Copy builds to bin")
            print("5 - Shutdown ubuntu")
            print("6 - Exit")

            try:
                while answer not in ("1", "2", "3", "4", "5", "6"):
                    answer = input("-> ")

                match int(answer):
                    case 1:
                        self.copy_to_ubuntu()
                    case 2:
                        self.upload_to_phone()
                    case 3:
                        self.log_phone()
                    case 4:
                        self.copy_to_bin()
                    case 5:
                        self.shut_down_ubuntu()
                    case 6:
                        self.running = False
            except KeyboardInterrupt:
                pass

    def copy_to_bin(self):
        bin_path = os.path.join(UBUNTU_APP_PATH, "bin")
        for _file in os.listdir(bin_path):
            shutil.copyfile(os.path.join(bin_path, _file), os.path.join("bin", _file))
            print(f"Copied: {_file}")

    def copy_to_ubuntu(self):
        for _file in COPY:
            if type(_file) is list or os.path.splitext(_file)[1]:
                if type(_file) is list:
                    shutil.copyfile(os.path.join(*_file), os.path.join(UBUNTU_APP_PATH, _file[1]))
                else:
                    shutil.copyfile(_file, os.path.join(UBUNTU_APP_PATH, _file))

                print(f"Copied: {_file}")
                continue
            for data in os.listdir(_file):
                if os.path.splitext(os.path.join(_file, data))[1]:
                    shutil.copyfile(os.path.join(_file, data), os.path.join(UBUNTU_APP_PATH, _file, data))
                    print(f"Copied: {_file}\\{data}")

    def upload_to_phone(self):
        files = sorted(glob.iglob(os.path.join(UBUNTU_APP_PATH, "bin", "*")), key=os.path.getctime, reverse=True)
        os.system(f"adb devices")
        os.system(f"adb -s {DEVICE} install {files[0]}")

    def log_phone(self):
        os.system(f"adb -s {DEVICE} logcat *:S python:D")

    def shut_down_ubuntu(self):
        os.system("wsl --shutdown")


if __name__ == "__main__":
    app = App()
    app.run()