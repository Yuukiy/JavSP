import os
import sys
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from javsp.core.func import * 


def test_remove_trail_actor_in_title():
    run = remove_trail_actor_in_title
    delimiters = list('-xX &·,;　＆・，；')
    title1 = '东风夜放花千树，更吹落、星如雨。'
    title2 = '辛弃疾 ' + title1
    names = ['辛弃疾', '牛顿', '爱因斯坦', '阿基米德', '伽利略']

    def combine(items):
        sep = random.choice(delimiters)
        new_str = sep.join(items)
        print(new_str)
        return new_str

    # 定义测试用例
    assert title1 == run(combine([title1, '辛弃疾']), names)
    assert title1 == run(combine([title1] + names), names)
    assert title1 == run(combine([title1, '辛弃疾']), names)
    assert title2 == run(combine([title2] + names), names)
