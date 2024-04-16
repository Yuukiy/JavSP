"""网页抓取相关的异常"""
__all__ = ['CrawlerError', 'MovieNotFoundError', 'MovieDuplicateError', 'SiteBlocked',
           'SitePermissionError', 'CredentialError', 'WebsiteError', 'OtherError']


class CrawlerError(Exception):
    """所有站点抓取器相关异常的基类"""


class MovieNotFoundError(CrawlerError):
    """表示某个站点没有抓取到某部影片"""
    # 保持异常消息的简洁，同时又支持使用'logger.info(e, exc_info=True)'记录完整信息
    def __init__(self, mod, avid, *args) -> None:
        msg = f"{mod}: 未找到影片: '{avid}'"
        super().__init__(msg, *args)

    def __str__(self):
        return self.args[0]


class MovieDuplicateError(CrawlerError):
    """影片重复"""
    def __init__(self, mod, avid, dup_count, *args) -> None:
        msg = f"{mod}: '{avid}': 存在{dup_count}个完全匹配目标番号的搜索结果"
        super().__init__(msg, *args)

    def __str__(self):
        return self.args[0]


class SiteBlocked(CrawlerError):
    """由于IP段或者触发反爬机制等原因导致用户被站点封锁"""


class SitePermissionError(CrawlerError):
    """由于缺少权限而无法访问影片资源"""


class CredentialError(CrawlerError):
    """由于缺少Cookies等凭据而无法访问影片资源"""


class WebsiteError(CrawlerError):
    """非预期的状态码等网页故障"""


class OtherError(CrawlerError):
    """其他尚未分类的错误"""
