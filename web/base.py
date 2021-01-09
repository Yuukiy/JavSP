"""网络请求的统一接口"""
import requests


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'}


def get_html(url):
    """获取指定网页的html并作为文本返回"""
    r = requests.get(url)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def is_connectable(url, timeout=3):
    """测试与指定url的连接"""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return True
    except:
        return False


if __name__ == "__main__":
    print(is_connectable('http://www.baidu.com'))