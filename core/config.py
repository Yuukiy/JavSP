import os
import re
import logging
import configparser
from string import Template


__all__ = ['cfg', 'is_url']


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename='JavSP.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
root_logger.addHandler(file_handler)


logger = logging.getLogger(__name__)


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

    def read(self, filenames, encoding='utf-8'):
        # 覆盖原生的read方法，以自动处理不同的编码
        try:
            super(Config, self).read(filenames, encoding)
        except UnicodeDecodeError:
            try:
                super(Config, self).read(filenames, 'utf-8-sig')
            except:
                super(Config, self).read(filenames)

    def validate(self):
        """对配置中必要的项目进行验证和转换，以便于其他模块直接使用"""
        # norm_config需要作为类的方法公开，以方便调用
        # 由norm_config间接调用的那些实际进行转换的函数并不应当被公开，所以它们组织为模块内的函数而不是类的方法
        norm_int(self)
        norm_tuples(self)
        norm_boolean(self)
        validate_proxy(self)
        convert_naming_rule(self)
        # 作为配置模块，始终检查免代理地址；由各个抓取器中根据代理情况选择是否启用免代理地址
        check_proxy_free_url(self)


def is_url(url: str):
    """判断给定的字符串是否是有效的带协议字段的URL"""
    # https://stackoverflow.com/a/7160778/6415337
    pattern = re.compile(
        r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|'     #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'      # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(pattern, url) is not None


def norm_int(cfg: Config):
    """转换所有的整数类型配置"""
    cfg.Network.retry = cfg.getint('Network', 'retry')
    cfg.Network.timeout = cfg.getint('Network', 'timeout')


def norm_tuples(cfg: Config):
    """将特定的配置转换为元组类型，便于迭代的同时也防止误修改"""
    # media_ext: 转换为全小写的.ext格式的元组
    items = cfg.File.media_ext.lower().split(';')
    exts = [i if i.startswith('.') else '.'+i for i in items]
    cfg.File.media_ext = tuple(exts)
    # ignore_folder: 转换为元组
    items = cfg.File.ignore_folder.split(';')
    cfg.File.ignore_folder = tuple(items)
    # required_keys: 转换为元组
    items = cfg.Crawler.required_keys.split(',')
    cfg.Crawler.required_keys = tuple(items)


def norm_boolean(cfg: Config):
    """转换所有的布尔类型配置"""
    for sec, key in [
            ('Crawler', 'hardworking_mode'),
            ('Crawler', 'remove_actor_in_title'),
            ('Picture', 'use_big_cover'),
            ('NFO', 'add_genre_to_tag')
        ]:
        cfg._sections[sec][key] = cfg.getboolean(sec, key)


def validate_proxy(cfg: Config):
    """解析配置文件中的代理"""
    proxies = {}
    use_proxy = cfg.getboolean('Network', 'use_proxy')
    if use_proxy:
        proxy = cfg.Network.proxy.lower()
        match = re.match('^(socks5h?|http)://([-.a-z\d]+):(\d+)$', proxy)
        if match:
            proxies = {'http': proxy, 'https': proxy}
        else:
            logger.warning(f"配置的代理格式无效，请使用类似'http://127.0.0.1:1080'的格式")
    cfg.Network.proxy = proxies


def convert_naming_rule(cfg: Config):
    """NamingRule: 转换为字符串Template"""
    combine = cfg.NamingRule.output_folder + os.sep + cfg.NamingRule.save_dir
    path_t = Template(combine)
    file_t = Template(cfg.NamingRule.filename)
    cfg.NamingRule.save_dir = path_t
    cfg.NamingRule.filename = file_t


def check_proxy_free_url(cfg: Config):
    """检查免代理URL的格式是否有效"""
    sec = cfg['ProxyFree']
    for site, url in sec.items():
        url = url.lower()
        if not url.startswith('http'):
            url = 'http://' + url
        sec[site] = url if is_url(url) else ''


cfg = Config()
logger.info('读取配置...')
cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
cfg.read(cfg_file)
cfg.validate()


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.File.media_ext)
