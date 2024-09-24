import os
import sys

from javsp.core.lib import * 


def test_detect_special_attr():
    run = detect_special_attr

    # 定义测试用例
    assert run('STARS-225_UNCENSORED_LEAKED.mp4') == 'U'
    assert run('STARS-225_UNCENSORED_LEAKED-C.mp4') == 'UC'
    assert run('STARS-225_无码.mp4') == ''
    assert run('STARS-225_无码流出.mp4') == 'U'
    assert run('STARS-225_无码破解.mp4') == 'U'
    assert run('STARS-225_UNCEN.mp4') == 'U'
    assert run('STARS-225_UNCEN-C.mp4') == 'UC'
    assert run('STARS-225u.mp4', 'STARS-225') == 'U'
    assert run('STARS-225C.mp4', 'STARS-225') == 'C'
    assert run('STARS-225uC.mp4', 'STARS-225') == 'UC'
    assert run('STARS225u.mp4', 'STARS-225') == 'U'
    assert run('STARS225C.mp4', 'STARS-225') == 'C'
    assert run('STARS225uC.mp4', 'STARS-225') == 'UC'
    assert run('STARS-225CD1.mp4', 'STARS-225') == ''
    assert run('stars225cd2.mp4', 'STARS-225') == ''
