import os
import sys

from javsp.web.proxyfree import *


def test_get_url():
    assert get_proxy_free_url('javlib') != ''
    assert get_proxy_free_url('javdb') != ''


def test_get_url_with_prefer():
    prefer_url = 'https://www.baidu.com'
    assert prefer_url == get_proxy_free_url('javlib', prefer_url)
