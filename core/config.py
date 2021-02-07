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

    def norm_config(self):
        """对配置中必要的项目进行格式转换，以便于其他模块直接使用"""
        # 扫描所有section和key，如果某个sec/key定义了对应的'_norm_XXX'方法，则调用该方法
        methods = [name for name in dir(self) if callable(getattr(self, name))]
        norm_methods = [name for name in methods if name.startswith('_norm_')]
        for sec in self.sections():
            sec_norm_method = '_norm_' + sec
            if sec_norm_method in norm_methods:
                getattr(self, sec_norm_method)()
                continue   # 如果有sec级别的norm方法，就不再检查其下的key的norm方法
            for key, value in self[sec].items():
                key_norm_method = '_norm_' + key
                if key_norm_method in norm_methods:
                    func = getattr(self, key_norm_method)
                    self._sections[sec][key] = func(value)
        self.norm_boolean()

    def _norm_Network(self):
        """retry: 转换为数字"""
        self.Network.retry = self.getint('Network', 'retry')
        self.Network.timeout = self.getint('Network', 'timeout')

    def _norm_Priority(self):
        """Priority: 按配置的抓取器顺序转换为内部的抓取器函数列表"""
        sec = self['Priority']
        unknown_mods = []
        for typ, cfg_str in sec.items():
            mods = cfg_str.split(',')
            valid_mods = []
            for name in mods:
                try:
                    # 如果fc2fan本地镜像的路径无效，则跳过它
                    if name == 'fc2fan' and (not os.path.isdir(self.Crawler.fc2fan_local_path)):
                        logger.debug('由于未配置有效的fc2fan路径，已跳过该抓取器')
                        continue
                    mod = 'web.' + name
                    __import__(mod)
                    valid_mods.append(mod)
                except ModuleNotFoundError:
                    unknown_mods.append(name)
            self._sections['Priority'][typ] = tuple(valid_mods)
        if unknown_mods:
            logger.warning('  无效的抓取器: ' + ', '.join(unknown_mods))

    def _norm_ProxyFree(self):
        """ProxyFree: 仅接受有效的URL"""
        sec = self['ProxyFree']
        for site, url in sec.items():
            url = url.lower()
            if not url.startswith('http'):
                url = 'http://' + url
            if is_url(url):
                sec[site] = url
            else:
                sec[site] = ''

    def _norm_NamingRule(self):
        """NamingRule: 转换为字符串Template"""
        combine = self.NamingRule.output_folder + os.sep + self.NamingRule.save_dir
        path_t = Template(combine)
        file_t = Template(self.NamingRule.filename)
        self.NamingRule.save_dir = path_t
        self.NamingRule.filename = file_t

    @staticmethod
    def _norm_media_ext(cfg_str: str) -> tuple:
        """media_ext: 转换为全小写的.ext格式的元组"""
        items = cfg_str.lower().split(';')
        exts = [i if i.startswith('.') else '.'+i for i in items]
        return tuple(set(exts))

    @staticmethod
    def _norm_ignore_folder(cfg_str: str) -> tuple:
        """ignore_folder: 转换为元组"""
        return tuple(cfg_str.split(';'))

    @staticmethod
    def _norm_required_keys(cfg_str: str) -> tuple:
        """required_keys: 转换为元组"""
        return tuple(cfg_str.lower().split(','))

    def norm_boolean(self):
        """转换所有的布尔类型配置"""
        for sec, key in [
            ('Crawler', 'hardworking_mode'),
            ('Crawler', 'remove_actor_in_title'),
            ('NFO', 'add_genre_to_tag')
        ]:
            self._sections[sec][key] = self.getboolean(sec, key)


def validate_proxy(cfg: Config):
    """解析配置文件中的代理"""
    proxies = {}
    proxy = cfg.Network.proxy.lower()
    if proxy:   # 如果配置了代理
        match = re.match('^(socks5|http)://([-.a-z\d]+):(\d+)$', proxy)
        if match:
            proxies = {'http': proxy, 'https': proxy}
        else:
            logger.warning(f"配置的代理格式无效，请使用类似'http://127.0.0.1:1080'的格式")
    cfg.Network.proxy = proxies


logger.info('读取配置...')

cfg = Config()
cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
cfg.read(cfg_file)
# cfg.norm_config()
validate_proxy(cfg)


if __name__ == "__main__":
    import os
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.File.media_ext)
