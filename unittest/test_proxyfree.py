import sys

sys.path.append('../')
from web.proxyfree import *


def test_get_url():
    assert get_proxy_free_url('avsox') != ''
    assert get_proxy_free_url('javbus') != ''
    assert get_proxy_free_url('javlib') != ''
    assert get_proxy_free_url('javdb') != ''