"""改写内置的print函数，将其输出重定向到tqdm"""
import tqdm
import inspect


__all__ = ['TqdmOut']


# 普通输出和tqdm的输出混在一起会导致显示错乱，故在使用tqdm时要使用tqdm.write方法。
# 但是不希望又每个模块都使用tqdm.write方法，这样会显得混乱而且会导致与tqdm强耦合。
# 这个模块被设计来解决上面的问题：导入此模块后，全局覆盖内置的print，将输出都重定向到tqdm。
# 导入只在项目入口执行，这将改写所有后续导入的模块中的print的行为；
# 在单个模块内，不执行导入，这样的话在各个模块内仍然可以直接使用print

builtin_print = print
def flex_print(*args, **kwargs):
    try:
        tqdm.tqdm.write(*args, **kwargs)
    except:
        builtin_print(*args, ** kwargs)
# 替换内置的print
inspect.builtins.print = flex_print


class TqdmOut:
    """用于将logging的stream输出重定向到tqdm"""
    @classmethod
    def write(cls, s, file=None, nolock=False):
        tqdm.tqdm.write(s, file=file, end='', nolock=nolock)
