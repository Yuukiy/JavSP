"""与文件相关的各类功能"""
import os
from tkinter import filedialog, Tk


def select_folder(default_dir=''):
    """使用文件对话框提示用户选择一个文件夹"""
    directory_root = Tk()
    directory_root.withdraw()
    path = filedialog.askdirectory(initialdir=default_dir)
    if path != '':
        return os.path.normpath(path)


if __name__ == "__main__":
    print(select_folder())
