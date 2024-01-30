import subprocess
from multiprocessing import Process
from JavSP import main


def cmd_popen():
    # 给前端页面另起一个进程
    subprocess.Popen(['streamlit', 'run', 'webui/scraper_setting.py'])


def scraper_process():
    # 前端页面发起抓取指令时调用此进程
    scraper = Process(main())
    scraper.start()
    scraper.join()


if __name__ == '__main__':
    webui = Process(target=cmd_popen)
    webui.start()
    webui.join()
    print('Started!')
