from argparse import ArgumentParser, RawTextHelpFormatter
from enum import Enum
from typing import Dict, List
from confz import BaseConfig, CLArgSource, EnvSource, FileSource
from pydantic import ByteSize, NonNegativeInt, PositiveInt, ValidationError
from pydantic_extra_types.pendulum_dt import Duration
from pydantic_core import Url
from pathlib import Path

from javsp.core.lib import resource_path
# from argparse import ArgumentParser, RawTextHelpFormatter

class IDSanitizer(BaseConfig):
    ignore_regexes: List[str]

class Scanner(BaseConfig):
    input_directory: Path | None = None
    filename_extensions: List[str]
    ignore_folder: List[Path]
    minimum_size: ByteSize
    move_files: bool = True

class CrawlerID(str, Enum):
    airav = 'airav'
    avsox = 'avsox'
    javbus = 'javbus'
    javdb = 'javdb'
    javlib = 'javlib'
    jav321 = 'jav321'
    mgstage = 'mgstage'
    prestige = 'prestige'
    fc2 = 'fc2'
    fc2ppvdb = 'fc2ppvdb'
    javmenu = 'javmenu'
    fanza = 'fanza'
    dl_getchu = 'dl_getchu'
    gyutto = 'gyutto'

class Network(BaseConfig):
    proxy_server: Url | None
    retry: NonNegativeInt = 3
    timeout: Duration
    proxy_free: Dict[CrawlerID, Url]

class CrawlerSelect(BaseConfig):
    def items(self) -> List[tuple[str, list[CrawlerID]]]:
        return [
            ('normal', self.normal),
            ('fc2', self.fc2),
            ('cid', self.num_id),
            ('getchu', self.getchu),
            ('gyutto', self.gyutto),
        ]

    def __getitem__(self, index) -> list[CrawlerID]:
        match index:
            case 'normal':
                return self.normal
            case 'fc2':
                return self.fc2
            case 'cid':
                return self.num_id
            case 'getchu':
                return self.getchu
            case 'gyutto':
                return self.gyutto
        raise Exception("Unknown crawler type")

    normal: list[CrawlerID]
    fc2: list[CrawlerID]
    num_id: list[CrawlerID]
    getchu: list[CrawlerID]
    gyutto: list[CrawlerID]

class MovieInfoField(str, Enum):
    dvdid = 'dvdid'
    cid = 'cid'
    url = 'url'
    plot = 'plot'
    cover = 'cover'
    big_cover = 'big_cover'
    genre = 'genre'
    genre_id = 'genre_id'
    genre_norm = 'genre_norm'
    score = 'score'
    title = 'title'
    ori_title = 'ori_title'
    magnet = 'magnet'
    serial = 'serial'
    actress = 'actress'
    actress_pics = 'actress_pics'
    director = 'director'
    duration = 'duration'
    producer = 'producer'
    publisher = 'publisher'
    uncensored = 'uncensored'
    publish_date = 'publish_date'
    preview_pics = 'preview_pics'
    preview_video = 'preview_video'

class UseJavDBCover(str, Enum):
    yes = "yes"
    no = "no"
    fallback = "fallback"

class Crawler(BaseConfig):
    required_keys: list[MovieInfoField]
    hardworking: bool
    respect_site_avid: bool
    fc2fan_local_path: Path | None
    title_remove_actor: bool
    title_chinese_first: bool
    sleep_after_scraping: Duration
    use_javdb_cover: UseJavDBCover
    unify_actress_name: bool

class Summarizer(BaseConfig):
    output_root: Path
    path_pattern: str
    name_pattern: str
    max_path_length: PositiveInt
    path_length_by_byte: bool
    max_actress_count: PositiveInt = 10
    nfo_title_pattern: str
    censor_texts: list[str]
    null_for_title: str
    null_for_actress: str
    null_for_series: str
    null_for_director: str
    null_for_producer: str
    null_for_publisher: str

class MediaSanitizer(BaseConfig):
    prefer_big_covers: bool
    store_extra_fanarts: bool
    extra_fanarts_scrap_interval: Duration
    use_ai_crop: bool
    ai_crop_match_regexes: list[str]
    ai_engine: str
    aip_appid: str
    aip_api_key: str
    aip_secret_key: str
    add_label_to_cover: bool

class Translator(BaseConfig):
    engine: str
    translate_title: bool
    translate_plot: bool
    baidu_appid: str
    baidu_key: str
    bing_key: str
    claude_key: str
    openai_url: Url
    openai_key: str
    openai_model: str

class NFO(BaseConfig):
    add_custom_genres: bool
    add_custom_genres_fields: list[str]
    add_custom_tags: bool
    add_custom_tags_fields: list[str]


class Other(BaseConfig):
    check_update: bool
    auto_update: bool

def get_config_source():
    parser = ArgumentParser(prog='JavSP', description='汇总多站点数据的AV元数据刮削器', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-c', '--config', help='使用指定的配置文件')
    args, _ = parser.parse_known_args()
    sources = []
    if args.config == '' or args.config is None:
        args.config = resource_path('config.yml')
    sources.append(FileSource(file=args.config))
    sources.append(EnvSource(prefix='JAVSP_', allow_all=True))
    sources.append(CLArgSource(prefix='o'))
    return sources

class Cfg(BaseConfig):
    id_sanitizer: IDSanitizer
    scanner: Scanner
    network: Network
    crawler_select: CrawlerSelect
    crawler: Crawler
    summarizer: Summarizer
    media_sanitizer: MediaSanitizer
    translator: Translator
    nfo: NFO
    other: Other
    CONFIG_SOURCES=get_config_source()
