import os
import re
import sys
import logging
import argparse
import configparser
from string import Template


__all__ = ['cfg', 'args', 'is_url']


def rel_path_from_exe(path):
    """将一个相对于exe文件的路径转换为绝对路径"""
    if getattr(sys, 'frozen', False):
        # 打包后相对于exe定位
        rel_start = os.path.split(sys.executable)[0]
    else:
        # 打包前相对于config.py文件的上一层文件夹定位
        rel_start = os.path.dirname(os.path.dirname(__file__))
    # 确保返回的是绝对路径（__file__可能引入相对路径）
    abs_path = os.path.abspath(os.path.join(rel_start, path))
    return abs_path


def log_filter(record):
    """只接受JavSP自身的日志，排除所依赖的库的日志"""
    rname = record.name
    if rname in ['main', '__main__'] or rname.startswith(('core.', 'web.')):
        return True
    else:
        return False


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename=rel_path_from_exe('JavSP.log'), mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.addFilter(filter=log_filter)
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
        norm_ignore_pattern(self)
        convert_naming_rule(self)
        validate_translation(self)
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
            ('Crawler', 'title__remove_actor'),
            ('Crawler', 'title__chinese_first'),
            ('Picture', 'use_big_cover'),
            ('NFO', 'add_genre_to_tag'),
            ('Other', 'check_update')
        ]:
        cfg._sections[sec][key] = cfg.getboolean(sec, key)


def norm_ignore_pattern(cfg: Config):
    """将配置文件中推测番号时的忽略列表转换为正则表达式"""
    words = cfg.MovieID.ignore_whole_word.replace(' ','').split(';')
    regexes = cfg.MovieID.ignore_regex.split(';')
    words_pattern = R'\b({})\b'.format('|'.join(words))
    regex_patterns = '|'.join([f'({i})' for i in regexes])
    pattern_str = f'({words_pattern})|{regex_patterns}'
    ignore_pattern = re.compile(pattern_str, flags=re.I | re.A)
    cfg.MovieID.ignore_pattern = ignore_pattern


def validate_translation(cfg: Config):
    """从环境变量和配置文件解析并初步验证翻译设置"""
    trans = cfg.Translate
    # 尝试从环境变量获取相关的访问凭据
    trans.baidu_appid = os.getenv('JAVSP_BAIDU_APPID', trans.baidu_appid)
    trans.baidu_key = os.getenv('JAVSP_BAIDU_KEY', trans.baidu_key)
    trans.bing_key = os.getenv('JAVSP_BING_KEY', trans.bing_key)
    # 先获取访问凭据再判断翻译引擎，这样的话即使配置文件中未启用翻译也可以调试翻译功能
    if trans.engine == '':
        return
    # 判断不同翻译引擎所需的凭据是否齐全（默认为禁用翻译状态，仅当相关配置有效时才启用引擎）
    engine_name = trans.engine.lower()
    trans.engine = None
    if engine_name == 'baidu':
        if trans.baidu_appid and trans.baidu_key:
            cfg.Translate.engine = engine_name
        else:
            logger.error('使用百度翻译时，appid和key均不能留空')
    elif engine_name == 'bing':
        if trans.bing_key:
            cfg.Translate.engine = engine_name
        else:
            logger.error('使用必应翻译时，key不能留空')
    elif engine_name == 'google':
        cfg.Translate.engine = engine_name
    else:
        logger.error('无效的翻译引擎: ' + engine_name)


def validate_proxy(cfg: Config):
    """解析配置文件中的代理"""
    proxies = {}
    use_proxy = cfg.getboolean('Network', 'use_proxy')
    if use_proxy:
        proxy = cfg.Network.proxy.lower()
        match = re.match(r'^(socks5h?|http)://([-.a-z\d]+):(\d+)$', proxy)
        if match:
            proxies = {'http': proxy, 'https': proxy}
        else:
            logger.warning(f"配置的代理格式无效，请使用类似'http://127.0.0.1:1080'的格式")
    cfg.Network.proxy = proxies


def convert_naming_rule(cfg: Config):
    """NamingRule: 转换为字符串Template"""
    combine = cfg.NamingRule.output_folder + os.sep + cfg.NamingRule.save_dir
    cfg.NamingRule.save_dir = Template(combine)
    cfg.NamingRule.filename = Template(cfg.NamingRule.filename)
    cfg.NamingRule.nfo_title = Template(cfg.NamingRule.nfo_title)


def check_proxy_free_url(cfg: Config):
    """检查免代理URL的格式是否有效"""
    sec = cfg['ProxyFree']
    for site, url in sec.items():
        url = url.lower()
        if not url.startswith('http'):
            url = 'http://' + url
        sec[site] = url if is_url(url) else ''


def parse_args():
    """解析从命令行传入的参数并进行有效性验证"""
    parser = argparse.ArgumentParser(prog='JavSP', description='汇总多站点数据的AV元数据刮削器')
    parser.add_argument('-c', '--config', help='使用指定的配置文件')
    parser.add_argument('-i', '--input', help='要扫描的文件夹')
    parser.add_argument('-o', '--output', help='保存整理结果的文件夹')
    parser.add_argument('-x', '--proxy', help='代理服务器地址')
    parser.add_argument('-m', '--manual', action='store_true', help='手动模式：由用户输入每一部影片的番号')
    parser.add_argument('-e', '--auto-exit', action='store_true', help='运行结束后自动退出')
    parser.add_argument('-s', '--shutdown', action='store_true', help='整理完成后关机')
    # 忽略无法识别的参数，避免传入供pytest使用的参数时报错
    args, unknown = parser.parse_known_args()

    # 验证相关参数的有效性
    if args.config:
        cfg_file = os.path.abspath(args.config)
        if not os.path.exists(cfg_file):
            logger.error(f"找不到指定的配置文件: '{cfg_file}'")
        else:
            logger.debug(f"读取指定的配置文件: '{cfg_file}'")
    else:
        # 未指定配置文件时，使用默认配置文件
        if getattr(sys, 'frozen', False):
            cfg_file = os.path.join(os.path.split(sys.executable)[0], 'config.ini')
            if not os.path.exists(cfg_file):
                logger.warning(f"已创建默认配置文件: '{cfg_file}'")
                dump_config(cfg_file)
        else:
            cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')
    args.config = cfg_file
    return args


def dump_config(out_file):
    """将内置的配置文件输出到指定路径"""
    # 使用文件读写来创建配置文件，使得创建的配置文件具有与平台相适应的换行符
    internal_config = os.path.join(sys._MEIPASS, 'config.ini')
    with open(internal_config, 'rt', encoding='utf-8') as f:
        content = f.read()
    with open(out_file, 'wt', encoding='utf-8') as f:
        f.write(content)


def overwrite_cfg(cfg, args):
    """根据配置args覆盖cfg中特定的配置项"""
    if args.proxy:
        cfg.Network.proxy = 'yes'
        cfg.Network.proxy = args.proxy
    if args.input:
        cfg.File.scan_dir = args.input
    if args.output:
        cfg.NamingRule.output_folder = args.output


cfg = Config()
args = parse_args()
cfg.read(args.config)
# 先覆盖配置，再进行配置有效性的验证
overwrite_cfg(cfg, args)
cfg.validate()


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.NamingRule.output_folder)
