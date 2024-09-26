from configparser import ConfigParser
from argparse import ArgumentParser
import re

arg_parser = ArgumentParser(
    prog='config migration',
    description='migration your javsp config to yaml')

arg_parser.add_argument('-i', '--input', help='path to config.ini')
arg_parser.add_argument('-o', '--output', help='path to output config', default="config.yml")

args, _ = arg_parser.parse_known_args()

if(args.input is None):
    print("Expecting an input config file, try `config_migration.py -h` to see help.")
    exit(1)

cfg = ConfigParser()
cfg.read(args.input)

ignore_regexes: list[str] = cfg['MovieID']['ignore_regex'].split(';')
ignore_regexes += cfg['MovieID']['ignore_whole_word'].split(';')
ignore_regexes.append('(144|240|360|480|720|1080)[Pp]')
ignore_regexes.append('[24][Kk]')

input_directory = cfg['File']['scan_dir']
input_directory = 'null' if len(input_directory) == 0 else f"'{input_directory}'"

filename_extensions = cfg['File']['media_ext'].split(';')

ignored_folders = cfg['File']['ignore_folder'].split(';')

proxy_disabled = cfg['Network']['use_proxy'] == 'no' or cfg['Network']['proxy'] == ''

def yes_to_true(s):
    return 'true' if s == 'yes' else 'false'

def use_javdb_cover(s):
    if s == 'yes': return 'no' 
    elif s == 'no': return 'yes' 
    elif s == 'auto': return 'fallback' 

def path_len_by_byte(s):
    if s == 'no': return 'false'
    else: return 'true' 

def ai_crop_pat(s):
    if s == r'\d':
        return r'^\d{6}[-_]\d{3}$'
    else:
        return '^' + s

def fix_pat(p):
    return re.sub(r'\$([a-z]+)', r'{\1}', p)

config_str = f"""# vim:foldmethod=marker 
################################
scanner:
  # 推测番号前忽略文件名中的特定字符串（忽略大小写，以英文分号;分隔）
  # 大多数情况软件能够自动识别番号，只有当文件名中特定的部分导致番号识别错误时才需要更新此设置
  # 要忽略的正则表达式（如果你不熟悉正则表达式，请不要修改此配置，否则可能严重影响番号识别效果）
  ignored_id_pattern: #请手动清除重复的pattern
{'\n'.join([f"    - '{r}'" for r in ignore_regexes])}
  # 整理哪个文件夹下的影片？（此项留空时将在运行时询问）
  input_directory: {input_directory}
  # 哪些后缀的文件应当视为影片？
  filename_extensions: [{", ".join([f".{ext}" for ext in filename_extensions])}]
  # 扫描影片文件时忽略指定的文件夹
  ignored_folder_name_pattern: ['^\\.', {", ".join([f"'^{pat}$'" for pat in ignored_folders])}]
  # 匹配番号时忽略小于指定大小的文件
  # 格式要求：https://docs.pydantic.dev/2.0/usage/types/bytesize/
  minimum_size: {cfg['File']['ignore_video_file_less_than']}MiB

################################
network:
  # 设置代理服务器地址，支持 http, socks5/socks5h 代理，比如'http://127.0.0.1:1080'
  # null表示禁用代理
  proxy_server: {'null' if proxy_disabled else f"'{cfg['Network']['proxy']}'"}
  # 各个站点的免代理地址。地址失效时软件会自动尝试获取新地址，你也可以手动设置
  proxy_free:
{'\n'.join([f"    {id}: '{url}'" for id, url in dict(cfg['ProxyFree']).items()])}
  # 网络问题导致抓取数据失败时的重试次数，通常3次就差不多了
  retry: {cfg['Network']['retry']}
  # https://en.wikipedia.org/wiki/ISO_8601#Durations
  timeout: PT{cfg['Network']['timeout']}S

################################
crawler:
  # 要使用的爬虫列表（汇总数据时从前到后进行）
  # airav avsox avwiki fanza fc2 fc2fan javbus javdb javlib javmenu jav321 mgstage prestige
  selection:
    normal: [{', '.join(cfg['CrawlerSelect']['normal'].split(','))}]
    fc2: [{', '.join(cfg['CrawlerSelect']['fc2'].split(','))}]
    cid: [{', '.join(cfg['CrawlerSelect']['cid'].split(','))}]
    getchu: [{', '.join(cfg['CrawlerSelect']['getchu'].split(','))}]
    gyutto: [{', '.join(cfg['CrawlerSelect']['gyutto'].split(','))}]
  # 爬虫至少要获取到哪些字段才可以视为抓取成功？
  required_keys: [{', '.join(cfg['Crawler']['required_keys'].split(','))}]
  # 努力爬取更准确更丰富的信息（会略微增加部分站点的爬取耗时）
  hardworking: {yes_to_true(cfg['Crawler']['hardworking_mode'])}
  # 使用网页番号作为最终番号（启用时会对番号大小写等进行更正）
  respect_site_avid: {yes_to_true(cfg['Crawler']['respect_site_avid'])}
  # fc2fan已关站。如果你有镜像，请设置本地镜像文件夹的路径，此文件夹内要有类似'FC2-12345.html'的网页文件
  fc2fan_local_path: '{cfg['Crawler']['fc2fan_local_path']}'
  # 刮削一部电影后的等待时间（设置为0禁用此功能）
  # https://en.wikipedia.org/wiki/ISO_8601#Durations
  sleep_after_scraping: PT{cfg['Crawler']['sleep_after_scraping']}S
  # 是否使用javdb的封面（fallback/yes/no, 默认fallback: 如果能从别的站点获得封面则不用javdb的以避免水印）
  use_javdb_cover: {use_javdb_cover(cfg['Crawler']['ignore_javdb_cover'])}
  # 是否统一女优艺名。启用时会尝试将女优的多个艺名统一成一个
  normalize_actress_name: {yes_to_true(cfg['Crawler']['unify_actress_name'])}

################################
# 配置整理时的命名规则
# path_pattern, nfo_title_pattern和name_pattern中可以使用变量来引用影片的数据，支持的变量列表见下面的地址:
# https://github.com/Yuukiy/JavSP/wiki/NamingRule-%7C-%E5%91%BD%E5%90%8D%E8%A7%84%E5%88%99
summarizer:
  # 整理时是否移动文件: true-移动所有文件到新文件夹; false-数据保存到同级文件夹，不移动文件
  move_files: {yes_to_true(cfg['File']['enable_file_move'])}

  # 路径相关的选项
  path: 
    # 存放影片、封面等文件的文件夹路径
    output_folder_pattern: '{cfg['NamingRule']['output_folder'] + '/' + fix_pat(cfg['NamingRule']['save_dir'])}'
    # 影片、封面、nfo信息文件等的文件名将基于下面的规则来创建
    basename_pattern: '{fix_pat(cfg['NamingRule']['filename'])}'
    # 允许的最长文件路径（路径过长时将据此自动截短标题）
    length_maximum: {cfg['NamingRule']['max_path_len']}
    # 是否以字节数来计算文件路径长度
    length_by_byte: {path_len_by_byte(cfg['NamingRule']['calc_path_len_by_byte'])}
    # 路径中的{{actress}}字段最多包含多少名女优？
    max_actress_count: {cfg['NamingRule']['max_actress_count']}
    # 是否用硬链接方式整理文件？硬链接可以节省空间，但不是所有文件系统都支持
    hard_link: {yes_to_true(cfg['File']['use_hardlink']) if 'use_hardlink' in cfg['File'] else 'false'}

  #标题处理
  title:
    # 删除尾部可能存在的女优名
    remove_trailing_actor_name: {yes_to_true(cfg['Crawler']['title__remove_actor'])}

  # 下面这些项用来设置对应变量为空时的替代信息
  default:
    title: '{cfg['NamingRule']['null_for_title']}'
    actress: '{cfg['NamingRule']['null_for_actress']}'
    series: '{cfg['NamingRule']['null_for_serial']}'
    director: '{cfg['NamingRule']['null_for_director']}'
    producer: '{cfg['NamingRule']['null_for_producer']}'
    publisher: '{cfg['NamingRule']['null_for_publisher']}'

  # NFO文件生成相关的选项
  nfo:
    # nfo文件中的影片标题（即媒体管理工具中显示的标题）
    title_pattern: '{fix_pat(cfg['NamingRule']['nfo_title'])}'
    # 要添加到自定义分类的字段，空列表表示不添加
    custom_genres_fields: [{
      ", ".join(["'" + fix_pat(f) + "'" for f in cfg['NFO']['add_custom_genres_fields'].split(',')])
}]
    # 要添加到自定义标签的字段，空列表表示不添加
    custom_tags_fields: [{
      ", ".join(["'" + fix_pat(f) + "'" for f in cfg['NFO']['add_custom_tags_fields'].split(',')])
}]
  # 依次设置 已知无码/已知有码/不确定 这三种情况下 $censor 对应的文本(可以利用此变量将有码/无码影片整理到不同文件夹)
  censor_options_representation: ['{cfg['NamingRule']['text_for_uncensored']}', '{cfg['NamingRule']['text_for_censored']}', '{cfg['NamingRule']['text_for_unknown_censorship']}']


################################
media_sanitizer:
  # 尽可能下载高清封面？（高清封面大小约 8-10 MiB，远大于普通封面，如果你的网络条件不佳，会降低整理速度）
  highres_covers: {yes_to_true(cfg['Picture']['use_big_cover'])}
  extra_fanarts:
    # 是否下载剧照？
    enabled: {yes_to_true(cfg['Picture']['use_extra_fanarts'])}
    # 间隔的两次封面爬取请求之间应该间隔多久
    scrap_interval: PT{cfg['Picture']['extra_fanarts_scrap_interval']}S
  crop:
    # 要使用图像识别来裁剪的番号系列需要匹配的正则表达式
    on_id_pattern:
{'\n'.join([f"      - '{ai_crop_pat(r)}'" for r in cfg['Picture']['use_ai_crop_labels'].split(',')])}
    # 要使用的图像识别引擎，详细配置见文档 https://github.com/Yuukiy/JavSP/wiki/AI-%7C-%E4%BA%BA%E8%84%B8%E8%AF%86%E5%88%AB
    # NOTE: 此处无法直接对应，请参照注释手动填入
    engine: null #null表示禁用图像剪裁
    ## 使用百度人体分析应用: {{{{{{
    # engine: 
    #   name: baidu_aip
    #   # 百度人体分析应用的AppID
    #   app_id: ''
    #   # 百度人体分析应用的API Key
    #   api_key: ''
    #   # 百度人体分析应用的Secret Key
    #   secret_key: ''
    ## }}}}}}
  # 在封面图上添加水印（标签），例如“字幕”
  add_label_to_cover: false

################################
translator:
  # NOTE: 此处无法直接对应，请参照注释手动填入
  # 翻译引擎，可选: google, bing, baidu, claude(haiku), openai （Google可以直接免费使用。留空表示禁用翻译功能）
  # 进阶功能的文档 https://github.com/Yuukiy/JavSP/wiki/Translation-%7C-%E7%BF%BB%E8%AF%91
  engine: null
  ## 使用百度翻译: {{{{{{
  # engine: 
  #   name: baidu
  #   # 百度翻译的APP ID和密钥
  #   app_id: ''
  #   api_key: ''
  ## }}}}}}
  ## 使用必应翻译: {{{{{{
  # engine: 
  #   name: bing
  #   # 微软必应翻译（Azure 认知服务 → 翻译）的密钥
  #   api_key: ''
  ## }}}}}}
  ## 使用Claude翻译: {{{{{{
  # engine: 
  #   name: claude
  #   # Claude的密钥 (使用haiku模型)
  #   api_key: ''
  ## }}}}}}
  ## 使用OpenAI翻译: {{{{{{
  # engine: 
  #   name: openai
  #   # OpenAI API（默认使用 Groq，可替换成任何兼容 OpenAI 的第三方 API）
  #   url: 'https://api.groq.com/openai/v1/chat/completions'
  #   api_key: ''
  #   # 要使用的模型（默认使用 Groq 的 llama-3.1-70b-versatile 模型，若使用 OpenAI 官方 API 的话一般模型为 gpt-3.5-turbo）
  #   model: llama-3.1-70b-versatile
  ## }}}}}}
  
  # 是否翻译各个字段
  fields: 
    # 是否翻译标题
    title: {yes_to_true(cfg['Translate']['translate_title'])}
    # 是否翻译剧情简介
    plot: {yes_to_true(cfg['Translate']['translate_plot'])}
  
################################
other:
  # 是否允许检查更新。如果允许，在有新版本时会显示提示信息和新版功能
  check_update: {yes_to_true(cfg['Other']['check_update'])}
  # 是否允许检查到新版本时自动下载
  auto_update: {yes_to_true(cfg['Other']['auto_update'])}"""

with open(args.output, mode ="w") as file:
    file.write(config_str)

