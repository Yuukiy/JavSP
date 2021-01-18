import os
import configparser


class DotDict(dict):
    """Access dict value with 'dict.key' grammar"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Config(configparser.ConfigParser):
    def __init__(self, **kwargs):
        # 使用ConfigParser的__init__方法来创建配置实例
        super().__init__(dict_type=DotDict, **kwargs)

    def __getattr__(self, name: str) -> None:
        if name not in self._sections:
            raise KeyError(name)
        return self._sections.get(name)

    def read(self, filenames, encoding=None):
        # 覆盖原生的read方法，以自动处理不同的编码
        # TODO: filenames参数实际上可以为多个文件的列表，因此可以直接支持此前设想的多配置文件功能
        try:
            super(Config, self).read(filenames, encoding)
        except UnicodeDecodeError:
            try:
                super(Config, self).read(filenames, 'utf-8')
            except:
                super(Config, self).read(filenames, 'utf-8-sig')

    def norm_config(self):
        """对配置中必要的项目进行格式转换，以便于其他模块直接使用"""
        self.File.media_ext = _norm_media_ext(self.File.media_ext)
        self.File.ignore_folder = _norm_ignore_folder(self.File.ignore_folder)
        


def _norm_media_ext(cfg_str: str) -> tuple:
    # media_ext: 转换为全小写的.ext格式的元组
    items = cfg_str.lower().split(';')
    exts = [i if i.startswith('.') else '.'+i for i in items]
    return tuple(set(exts))


def _norm_ignore_folder(cfg_str: str) -> tuple:
    # ignore_folder: 转换为元组
    return cfg_str.split(';')


cfg = Config()
cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
cfg.read(cfg_file)
cfg.norm_config()


if __name__ == "__main__":
    import os
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.File.media_ext)
