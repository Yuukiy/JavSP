import os
import sys
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.lib import * 


def test_detect_special_attr():
    run = detect_special_attr

    # 定义测试用例
    assert run('STARS-225_UNCENSORED_LEAKED.mp4') == 'U'
    assert run('STARS-225_UNCENSORED_LEAKED-C.mp4') == 'UC'
    assert run('STARS-225_无码.mp4') == ''
    assert run('STARS-225_无码流出.mp4') == 'U'
    assert run('STARS-225_无码破解.mp4') == 'U'
