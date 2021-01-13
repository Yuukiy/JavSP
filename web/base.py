"""网络请求的统一接口"""
import requests
import lxml.html


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'}


def get_html_text(url, encoding=None):
    """获取指定网页的原始html文本"""
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    r.encoding = encoding if encoding else r.apparent_encoding
    return r.text


def get_html(url, encoding=None):
    """获取指定网页经lxml解析后的document"""
    text = get_html_text(url, encoding=encoding)
    html = lxml.html.fromstring(text)
    return html


def is_connectable(url, timeout=3):
    """测试与指定url的连接"""
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


if __name__ == "__main__":
    print(is_connectable('http://www.baidu.com'))