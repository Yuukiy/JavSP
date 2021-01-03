import sys
sys.path.append('../')
from core.avid import *

def test_fc2():
    assert 'FC2-123456' == get_id('(2017) [FC2-123456] 【個人撮影】')
    assert 'FC2-123456' == get_id('fc2-ppv-123456-1.delogo.mp4')
    assert 'FC2-123456' == get_id('FC2-PPV-123456.mp4')
    assert 'FC2-123456' == get_id('FC2PPV-123456 Riku')
    assert 'FC2-1234567' == get_id('fc2-ppv_1234567-2.mp4')
