import os
import re
import pytest
from glob import glob


data_dir = os.path.join(os.path.dirname(__file__), 'data')


def pytest_addoption(parser):
    parser.addoption(
        "--only", action="store", default="", help="仅测试指定抓取器的数据"
    )


@pytest.fixture
def crawler(request):
    return request.config.getoption("--only")


def pytest_generate_tests(metafunc):
    if 'crawler_params' in metafunc.fixturenames:
        # 根据测试数据文件夹中的文件生成测试数据
        testcases = {}
        data_files = glob(data_dir + os.sep + '*.json')
        target_crawler = metafunc.config.getoption("--only")
        for file in data_files:
            basename = os.path.basename(file)
            match = re.match(r"([-\w]+) \((\w+)\)", basename, re.I)
            if match:
                avid, scraper = match.groups()
                name = f'{avid}: {scraper}'
                # 仅当未指定抓取器或者指定的抓取器与当前抓取器相同时，才实际执行抓取和比较
                if (not target_crawler) or scraper == target_crawler:
                    testcases[name] = (avid, scraper, file)
        # 生成测试用例（testcases的键名将用作测试用例ID）
        metafunc.parametrize("crawler_params", testcases.values(), ids=testcases.keys())
