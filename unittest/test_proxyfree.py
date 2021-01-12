import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.proxyfree import *


def test_get_url():
    assert get_proxy_free_url('avsox') != ''
    assert get_proxy_free_url('javbus') != ''
    assert get_proxy_free_url('javlib') != ''
    assert get_proxy_free_url('javdb') != ''