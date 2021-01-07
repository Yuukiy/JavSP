import os
import sys
import uuid
import pytest
from shutil import rmtree

sys.path.append('../')
from core.avid import *


@pytest.fixture
def prepare_files(files):
    """按照指定的文件列表创建对应的文件，并在测试完成后删除它们

    Args:
        files (list of tuple): 文件列表，仅接受相对路径
    """
    tmp_folder = 'tmp_' + uuid.uuid4().hex[:8]
    for i in files:
        path = os.path.join(tmp_folder, i)
        folder = os.path.split(path)[0]
        if folder and (not os.path.exists(folder)):
            os.makedirs(folder)
        with open(path, 'wt') as f:
            f.write(path)
    yield
    rmtree(tmp_folder)
    return


def test_fc2():
    assert 'FC2-123456' == get_id('(2017) [FC2-123456] 【個人撮影】')
    assert 'FC2-123456' == get_id('fc2-ppv-123456-1.delogo.mp4')
    assert 'FC2-123456' == get_id('FC2-PPV-123456.mp4')
    assert 'FC2-123456' == get_id('FC2PPV-123456 Yuukiy')
    assert 'FC2-1234567' == get_id('fc2-ppv_1234567-2.mp4')


def test_normal():
    assert '' == get_id('Yuukiy')
    assert 'ABC-12' == get_id('ABC-12_01.mkv')
    assert 'ABC-123' == get_id('Sky Angel Vol.6 月丘うさぎ(ABC-123).avi')
    assert 'ABCD-123' == get_id('ABCD-123.mp4')


@pytest.mark.parametrize('files', [('Unknown.mp4',)])
def test_by_folder_name1(prepare_files):
    assert '' == get_id('Unknown.mp4')


@pytest.mark.parametrize('files', [('FC2-123456/Unknown.mp4',)])
def test_by_folder_name2(prepare_files):
    assert 'FC2-123456' == get_id('FC2-123456/Unknown.mp4')
