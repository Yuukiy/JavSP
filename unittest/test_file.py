import os
import sys
import uuid
import pytest
from shutil import rmtree


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.file import *


tmp_folder = 'tmp_' + uuid.uuid4().hex[:8]


@pytest.fixture
def prepare_files(files):
    """按照指定的文件列表创建对应的文件，并在测试完成后删除它们

    Args:
        files (list of tuple): 文件列表，仅接受相对路径
    """
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


# 根文件夹下的单个影片文件
@pytest.mark.parametrize('files', [('ABC-123.mp4',)])
def test_single_movie(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 1
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123.mp4'


# 多个分片以数字排序: 012
@pytest.mark.parametrize('files', [('ABC-123-0.mp4','ABC-123-1.mp4','ABC-123- 2.mp4')])
def test_scan_movies__012(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123-0.mp4'
    assert basenames[1] == 'ABC-123-1.mp4'
    assert basenames[2] == 'ABC-123- 2.mp4'


# 多个分片以数字排序: 123
@pytest.mark.parametrize('files', [('ABC-123.1.mp4','ABC-123. 2.mp4','ABC-123.3.mp4')])
def test_scan_movies__123(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123.1.mp4'
    assert basenames[1] == 'ABC-123. 2.mp4'
    assert basenames[2] == 'ABC-123.3.mp4'


# 多个分片以字母排序
@pytest.mark.parametrize('files', [('ABC-123-A.mp4','ABC-123-B.mp4','ABC-123- C .mp4')])
def test_scan_movies__abc(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123-A.mp4'
    assert basenames[1] == 'ABC-123-B.mp4'
    assert basenames[2] == 'ABC-123- C .mp4'


# 多个分片以.CDx编号
@pytest.mark.parametrize('files', [('ABC-123.CD1.mp4','ABC-123.CD2 .mp4','ABC-123.CD3.mp4')])
def test_scan_movies__cdx(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123.CD1.mp4'
    assert basenames[1] == 'ABC-123.CD2 .mp4'
    assert basenames[2] == 'ABC-123.CD3.mp4'


# 文件夹以番号命名，分片位于文件夹内且无番号信息
@pytest.mark.parametrize('files', [('ABC-123/CD1.mp4','ABC-123/CD2 .mp4','ABC-123/CD3.mp4')])
def test_scan_movies__from_folder(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'CD1.mp4'
    assert basenames[1] == 'CD2 .mp4'
    assert basenames[2] == 'CD3.mp4'


# 分片以多位数字编号
@pytest.mark.parametrize('files', [('ABC-123.01.mp4','ABC-123.02.mp4','ABC-123.03.mp4')])
def test_scan_movies__0x123(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'ABC-123'
    assert len(movies[0].files) == 3
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'ABC-123.01.mp4'
    assert basenames[1] == 'ABC-123.02.mp4'
    assert basenames[2] == 'ABC-123.03.mp4'


# 无效：多个分片位于不同文件夹
@pytest.mark.parametrize('files', [('ABC-123.CD1.mp4','sub/ABC-123.CD2.mp4','ABC-123.CD3.mp4')])
def test_scan_movies__wrong_structure(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 0


# 无效：分片的起始编号不合法
@pytest.mark.parametrize('files', [('ABC-123.CD2.mp4','ABC-123.CD3.mp4','ABC-123.CD4.mp4')])
def test_scan_movies__wrong_initial_id(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 0


# 无效：分片的编号不连续
@pytest.mark.parametrize('files', [('ABC-123.CD1.mp4','ABC-123.CD3.mp4','ABC-123.CD4.mp4')])
def test_scan_movies__not_consecutive(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 0


# 无效：分片的编号重复
@pytest.mark.parametrize('files', [('ABC-123-1.mp4','ABC-123-1 .mp4','ABC-123-3.mp4')])
def test_scan_movies__duplicate_index(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 0


# 混合有效和无效数据
@pytest.mark.parametrize('files', [('DEF-456/movie.mp4', 'ABC-123.1.mp4','sub/ABC-123.2.mp4','ABC-123.3.mp4')])
def test_scan_movies__mix_data(prepare_files):
    movies = scan_movies(tmp_folder)
    assert len(movies) == 1
    assert movies[0].dvdid == 'DEF-456'
    assert len(movies[0].files) == 1
    basenames = [os.path.basename(i) for i in movies[0].files]
    assert basenames[0] == 'movie.mp4'

