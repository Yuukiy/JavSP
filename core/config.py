import configparser


class DotDict(dict):
    """Access dict value with 'dict.key' grammar"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Config(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        # 使用ConfigParser的__init__方法来创建配置实例
        super(Config, self).__init__(*args, **kwargs)

    def __getattr__(self, sec: str) -> None:
        if sec not in self._sections:
            raise KeyError(sec)
        return DotDict(self._sections.get(sec))

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


if __name__ == "__main__":
    import os
    import pretty_errors
    pretty_errors.configure(display_link=True)

    cfg = Config()
    cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_file)
    print(cfg.MovieID.media_ext)
