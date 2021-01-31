import os
import sys
import logging
import configparser
from string import Template

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import is_url
from web.proxyfree import get_proxy_free_url


logger = logging.getLogger(__name__)
logger.info('读取配置文件...')


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

    def _norm_Network(self):
        """retry: 转换为数字"""
        self.Network.retry = self.getint('Network', 'retry')

    def _norm_Priority(self):
        """Priority: 按配置的抓取器顺序转换为内部的抓取器函数列表"""
        sec = self['Priority']
        unknown_mods = []
        for typ, cfg_str in sec.items():
            mods = cfg_str.split(',')
            valid_mods = []
            for name in mods:
                try:
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

    def update_ProxyFree_urls(self):
        """验证和更新各个站点的免代理地址"""
        need_update = False
        for site, url in self['ProxyFree'].items():
            new_url = get_proxy_free_url(site, prefer_url=url)
            if new_url != '' and new_url != url:
                self['ProxyFree'][site] = new_url
                need_update = True
        if need_update:
            # TODO: 待改进：写入时会丢失注释，而且部分字段的值需要先进行格式化（如元组）
            with open(cfg_file, 'wt', encoding='utf-8') as f:
                self.write(f)


cfg = Config()
cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
cfg.read(cfg_file)
cfg.norm_config()


if __name__ == "__main__":
    import os
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.File.media_ext)
