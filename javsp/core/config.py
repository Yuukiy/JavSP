import os
import re
import sys
import getpass
import logging
import argparse
import configparser
from shutil import copyfile
from string import Template

from javsp.core.lib import re_escape

__all__ = ['cfg', 'args', 'is_url']

built_in_cfg_file = os.path.join(os.path.dirname(__file__), 'config.ini')

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


def gen_backup_path(path):
    """为给定文件生成一个备份路径（必要时增加序号以避免覆盖现有文件）"""
    abspath = os.path.abspath(path)
    backup_path = abspath + '.bak'
    i = 1
    while os.path.exists(backup_path):
        backup_path = abspath + '.' + str(i) + '.bak'
        i += 1
    return backup_path


def log_filter(record):
    """只接受JavSP自身的日志，排除所依赖的库的日志"""
    rname = record.name
    return rname in ('main', '__main__') or rname.startswith(('core.', 'web.'))


class ColoredFormatter(logging.Formatter):
    """为不同level的日志着色"""
    NO_STYLE = '\033[0m'
    COLOR_MAP = {
        logging.DEBUG:    '\033[1;30m',  # grey
        logging.WARNING:  '\033[1;33m',  # light yellow
        logging.ERROR:    '\033[1;31m',  # light red
        logging.CRITICAL: '\033[0;31m',  # red
    }

    def __init__(self, fmt='%(levelname)-8s:%(message)s',
                 datefmt='%Y-%m-%d %H:%M:%S', style='%', validate=True) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)

    def format(self, record):
        # 清除exc_info异常信息，保持终端输出的整洁
        record.exc_info = None
        record.exc_text = None
        raw = super().format(record)
        color = self.COLOR_MAP.get(record.levelno, self.NO_STYLE)
        return color + raw + self.NO_STYLE


class DetailedFormatter(logging.Formatter):
    """如果日志记录包含异常信息，则将传递给异常的参数一起记录下来"""
    def __init__(self, fmt='%(asctime)s %(name)s:%(lineno)d %(levelname)s: %(message)s',
                 datefmt='%Y-%m-%d %H:%M:%S', *args) -> None:
        super().__init__(fmt, datefmt, *args)
        username = getpass.getuser()
        self.anonymize = re.compile(r'([\\/]*)' + re_escape(username) + '([\\/]*)', flags=re.I)

    def format(self, record):
        raw = super().format(record)
        s = self.anonymize.sub(r'\1javsp\2', raw)
        return s

    def formatException(self, ei):
        s = super().formatException(ei)
        # ei[1] 是异常的实例，从中提取除了异常的message外的其他参数
        if len(ei[1].args) > 1:
            args = ei[1].args[1:]
            s += "\nArguments: \n  " + str(args).strip('(),')
        return s


# 添加到root的filter无法对root的子logger生效（真是反直觉的设计），因此将filter添加到每一个handler
# https://docs.python.org/3/library/logging.html#filter-objects
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(
    filename=rel_path_from_exe('JavSP.log'), mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.addFilter(filter=log_filter)
file_handler.setFormatter(DetailedFormatter())
root_logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.addFilter(filter=log_filter)
stream_handler.setFormatter(ColoredFormatter(fmt='%(message)s'))
root_logger.addHandler(stream_handler)

filemove_logger = logging.getLogger('filemove')
file_handler2 = logging.FileHandler(filename=rel_path_from_exe('FileMove.log'),
                                    mode='a', encoding='utf-8')
file_handler2.addFilter(filter=lambda r: r.name == 'filemove')
file_handler2.setFormatter(logging.Formatter(
    fmt='%(asctime)s\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
filemove_logger.addHandler(file_handler2)

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

    def read_cfg(self, cfg_file):
        builtin = Config()
        super(Config, builtin).read(built_in_cfg_file, 'utf-8')
        # 覆盖原生的read方法，以自动处理不同的编码
        for encoding in ('utf-8-sig', 'utf-8', None):
            try:
                super(Config, self).read(cfg_file, encoding)
                break
            except Exception:
                # 编码问题不一定报 UnicodeDecodeError, 因此要捕获所有异常
                logger.debug('解析配置文件时出错', exc_info=True)
        else:
            backup = gen_backup_path(cfg_file)
            copyfile(cfg_file, backup)
            dump_config(cfg_file)
            logger.warning('解析配置文件时出错，已重新生成配置文件')
            logger.info('原配置文件已备份到: ' + backup)
            # 直接退出，以便用户对生成的配置文件进行修改
            raise SystemExit()
        # 处理配置文件缺失特定字段的情况
        missed_items = []
        for sec in builtin.sections():
            if not self.has_section(sec):
                self.add_section(sec)
            for opt in builtin[sec]:
                if not self.has_option(sec, opt):
                    self[sec][opt] = builtin[sec][opt]
                    missed_items.append(f"'{sec}:{opt}'")
        if missed_items:
            logger.warning('使用默认配置补全缺失的配置项: ' + ', '.join(missed_items))
            self.update_cfg_file(cfg_file)

    def update_cfg_file(self, cfg_file):
        """将内置的配置文件作为模板，基于self重写cfg_file"""
        backup = gen_backup_path(cfg_file)
        copyfile(cfg_file, backup)
        # 读取内置配置文件
        with open(built_in_cfg_file, encoding='utf-8') as f:
            builtin = f.readlines()
        with open(cfg_file, 'wt', encoding='utf-8') as f:
            for line in builtin:
                # 注释行直接原样写入
                value = line.strip()
                if value.startswith(self._comment_prefixes):
                    f.write(line)
                    continue
                # 判断section和option
                mo = self.SECTCRE.match(value)
                if mo:      # section
                    sectname = mo.group('header')
                    f.write(line)
                else:
                    mo = self._optcre.match(value)
                    if mo:  # option
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        new_optval = self[sectname][optname]
                        f.write("{} {} {}\n".format(optname, vi, new_optval))
                    else:   # 空行等其他信息
                        f.write(line)
        logger.info('原配置文件已备份到: ' + backup)

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
        validate_media_servers(self)
        validate_ai_config(self)
        convert_nfo_config(self)


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
    cfg.NamingRule.max_path_len = min(cfg.getint('NamingRule', 'max_path_len'), 256)
    cfg.NamingRule.max_actress_count = max(cfg.getint('NamingRule', 'max_actress_count'), 1)
    cfg.File.ignore_video_file_less_than = int(cfg.getfloat('File', 'ignore_video_file_less_than') * 2**20)
    cfg.Crawler.sleep_after_scraping = max(cfg.getint('Crawler', 'sleep_after_scraping'), 0)


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
    # use_ai_crop_labels: 转换为元祖
    items = cfg.Picture.use_ai_crop_labels.upper().split(',')
    cfg.Picture.use_ai_crop_labels = tuple(items)


def norm_boolean(cfg: Config):
    """转换所有的布尔类型配置"""
    for sec, key in [
            ('Crawler', 'hardworking_mode'),
            ('Crawler', 'respect_site_avid'),
            ('Crawler', 'title__remove_actor'),
            ('Crawler', 'title__chinese_first'),
            ('Picture', 'use_big_cover'),
            ('Picture', 'use_ai_crop'),
            ('Picture', 'add_label_to_cover'),
            ('NFO', 'add_custom_tags'),
            ('NFO', 'add_custom_genres'),
            ('Other', 'check_update'),
            ('Other', 'auto_update'),
            ('File', 'enable_file_move'),
        ]:
        cfg._sections[sec][key] = cfg.getboolean(sec, key)
    # 特殊转换
    sec, key = 'NamingRule', 'calc_path_len_by_byte'
    try:
        cfg._sections[sec][key] = cfg.getboolean(sec, key)
    except ValueError:
        # 当配置为auto时会转换失败，此时保留auto配置以待后面根据文件系统来作更新
        cfg._sections[sec][key] = cfg._sections[sec][key].lower()


def norm_ignore_pattern(cfg: Config):
    """将配置文件中推测番号时的忽略列表转换为正则表达式"""
    words = cfg.MovieID.ignore_whole_word.replace(' ','').split(';')
    regexes = cfg.MovieID.ignore_regex.split(';')
    # \b匹配单词边界时，_连接的将视为一个单词。为了让_也作为单词的边界，需要进行额外处理
    words_pattern = R'(?:\b|_)({})(?=\b|_)'.format('|'.join(words))
    regex_patterns = '|'.join([f'({i})' for i in regexes])
    pattern_str = f'({words_pattern})|{regex_patterns}'
    ignore_pattern = re.compile(pattern_str, flags=re.I | re.A)
    cfg.MovieID.ignore_pattern = ignore_pattern


def validate_media_servers(cfg: Config):
    """获取媒体服务器配置并验证有效性"""
    supported = set(('universal', 'plex', 'emby', 'jellyfin', 'kodi', 'video_station'))
    servers = cfg.NamingRule.media_servers.lower()
    items = set(re.split(r'[^\w_]+', servers, flags=re.I))
    cfg.NamingRule.media_servers = items & supported
    invalid = items - supported
    if invalid:
        logger.error("媒体服务器无效: {}。仅支持: {}".format(','.join(invalid), ','.join(supported)))


def validate_translation(cfg: Config):
    """从环境变量和配置文件解析并初步验证翻译设置"""
    trans = cfg.Translate
    # 尝试从环境变量获取相关的访问凭据
    trans.baidu_appid = os.getenv('JAVSP_BAIDU_APPID', trans.baidu_appid)
    trans.baidu_key = os.getenv('JAVSP_BAIDU_KEY', trans.baidu_key)
    trans.bing_key = os.getenv('JAVSP_BING_KEY', trans.bing_key)
    trans.claude_key = os.getenv('JAVSP_CLAUDE_KEY', trans.claude_key)
    trans.groq_key = os.getenv('JAVSP_GROQ_KEY', trans.groq_key)
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
            logger.error('启用百度翻译时，appid和key均不能留空')
    elif engine_name == 'bing':
        if trans.bing_key:
            cfg.Translate.engine = engine_name
        else:
            logger.error('启用必应翻译时，key不能留空')
    elif engine_name == 'google':
        cfg.Translate.engine = engine_name
    elif engine_name == 'claude':
        if trans.claude_key:
            cfg.Translate.engine = engine_name
        else:
            logger.error('启用Claude时，key不能留空')
    elif engine_name == 'groq':
        if trans.groq_key:
            cfg.Translate.engine = engine_name
        else:
            logger.error('启用Groq时，key不能留空')
    else:
        logger.error('无效的翻译引擎: ' + engine_name)


def validate_ai_config(cfg: Config):
    """验证图像人脸/人体检测的相关配置是否完备"""
    piccfg = cfg.Picture
    if not piccfg.use_ai_crop:
        return
    if piccfg.ai_engine.lower() == 'baidu':
        piccfg.ai_engine = 'baidu'
        required_keys = ('aip_appid', 'aip_api_key', 'aip_secret_key')
        empty_keys = [i for i in required_keys if not piccfg[i]]
        if empty_keys:
            logger.error('使用百度人体分析时，相关设置不能为空: ' + ', '.join(empty_keys))
    else:
        logger.error('不支持的图像识别引擎: ' + piccfg.ai_engine)


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
    cfg.NamingRule.censorship_names = {
        False: cfg.NamingRule.text_for_censored,
        True: cfg.NamingRule.text_for_uncensored,
        None: cfg.NamingRule.text_for_unknown_censorship,
    }


def check_proxy_free_url(cfg: Config):
    """检查免代理URL的格式是否有效"""
    sec = cfg['ProxyFree']
    for site, url in sec.items():
        url = url.lower()
        if not url.startswith('http'):
            url = 'http://' + url
        sec[site] = url if is_url(url) else ''

def convert_nfo_config(cfg: Config):
    """NFO: 转换为字符串Template"""
    cfg.NFO.add_custom_tags_fields = Template(cfg.NFO.add_custom_tags_fields)
    cfg.NFO.add_custom_genres_fields = Template(cfg.NFO.add_custom_genres_fields)
    

def parse_args():
    """解析从命令行传入的参数并进行有效性验证"""
    parser = argparse.ArgumentParser(prog='JavSP', description='汇总多站点数据的AV元数据刮削器',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--config', help='使用指定的配置文件')
    parser.add_argument('-i', '--input', help='要扫描的文件夹')
    parser.add_argument('-o', '--output', help='保存整理结果的文件夹')
    parser.add_argument('-x', '--proxy', help='代理服务器地址')
    parser.add_argument('-m', '--manual', nargs='?', default=-1, 
                        help="由用户介入番号识别过程，可选值为：\n'all': 检查所有番号\n'failed': 仅检查无法识别的番号（默认）")
    parser.add_argument('-e', '--auto-exit', action='store_true', help='运行结束后自动退出')
    parser.add_argument('-s', '--shutdown', action='store_true', help='整理完成后关机')
    parser.add_argument('--data-cache-file', help='存储数据的缓存文件，临时文件，供进程间通信使用')
    parser.add_argument('--only-scan', action='store_true', help='仅识别，不刮削')
    parser.add_argument('--only-fetch', action='store_true', help='仅刮削data-cache-file缓存文件中的数据')
    # 忽略无法识别的参数，避免传入供pytest使用的参数时报错
    args, unknown = parser.parse_known_args()

    # 验证相关参数的有效性
    if args.config:
        cfg_file = os.path.abspath(args.config)
        if not os.path.exists(cfg_file):
            logger.error(f"找不到指定的配置文件: '{cfg_file}'")
            raise SystemExit()
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
            cfg_file = built_in_cfg_file
    # manual: 未传入选项时值为-1，仅传入选项时值为None，传入选项且有对应值时为对应值
    # 为了方便使用，仅传入选项时的默认值修改为'failed'，未传入选项时修改为None
    # raise argparse.ArgumentError('a', "invalid choice: 'aa' (choose from 1, 23)")
    if args.manual == None:
        args.manual = 'failed'
    elif args.manual == -1:
        args.manual = None
    elif args.manual.lower() in ('all', 'failed'):
        args.manual = args.manual.lower()
    else:
        # 生成与argparser类似格式的异常消息
        msg = f"{parser.prog}: error: argument -m/--manual: invalid choice: '{args.manual}' (choose from 'all', 'failed' or leave it empty)"
        # 使用SystemExit异常以避免显示traceback信息
        raise SystemExit(msg)
    if (args.only_scan == True or args.only_fetch == True) and args.data_cache_file == None:
        raise SystemExit("当仅刮削或者仅识别时，必须传入缓存文件路径")
    args.config = cfg_file
    return args


def dump_config(out_file):
    """将内置的配置文件输出到指定路径"""
    # 使用文件读写来创建配置文件，使得创建的配置文件具有与平台相适应的换行符
    with open(built_in_cfg_file, 'rt', encoding='utf-8') as f:
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
    if args.only_fetch == True:
        # 如果仅刮削，则不会整理文件
        cfg.File.enable_file_move = 'no'


cfg = Config()
args = parse_args()
cfg.read_cfg(args.config)
# 先覆盖配置，再进行配置有效性的验证
overwrite_cfg(cfg, args)
try:
    cfg.validate()
except Exception as e:
    logger.error('验证配置文件时出错: ' + repr(e))
    os.system('pause')
    sys.exit(2)


if __name__ == "__main__":
    import pretty_errors
    pretty_errors.configure(display_link=True)

    print(cfg.NamingRule.output_folder)
    print(args)
