import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--only", action="store", default="", help="仅测试指定抓取器的数据"
    )


@pytest.fixture
def crawler(request):
    return request.config.getoption("--only")