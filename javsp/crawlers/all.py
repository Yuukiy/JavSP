from collections.abc import Coroutine
from typing import Any, Dict
from javsp.config import CrawlerID
from javsp.crawlers.interface import Crawler
from javsp.crawlers.sites import \
    airav, arzon, arzon_iv, avsox, avwiki, dl_getchu, fanza, fc2, fc2ppvdb, \
    gyutto, jav321, javbus, javdb, javlib, javmenu, mgstage, njav, prestige

__all__ = ['crawlers']

crawlers: Dict[CrawlerID, type[Crawler]] = {
    CrawlerID.airav:     airav.    AiravCrawler,
    CrawlerID.arzon:     arzon.    ArzonCrawler,
    CrawlerID.arzon_iv:  arzon_iv. ArzonIvCrawler,
    CrawlerID.avsox:     avsox.    AvsoxCrawler,
    CrawlerID.avwiki:    avwiki.   AvWikiCrawler,
    CrawlerID.dl_getchu: dl_getchu.DlGetchuCrawler,
    CrawlerID.fanza:     fanza.    FanzaCrawler,
    CrawlerID.fc2:       fc2.      Fc2Crawler,
    CrawlerID.fc2ppvdb:  fc2ppvdb. Fc2PpvDbCrawler,
    CrawlerID.gyutto:    gyutto.   GyuttoCrawler,
    CrawlerID.jav321:    jav321.   Jav321Crawler,
    CrawlerID.javbus:    javbus.   JavbusCrawler,
    CrawlerID.javdb:     javdb.    JavDbCrawler,
    CrawlerID.javlib:    javlib.   JavLibCrawler,
    CrawlerID.javmenu:   javmenu.  JavMenuCrawler,
    CrawlerID.mgstage:   mgstage.  MgstageCrawler,
    CrawlerID.njav:      njav.     NjavCrawler,
    CrawlerID.prestige:  prestige. PrestigeCrawler,
}
