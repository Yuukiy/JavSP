"""从JavBus抓取数据"""
import sys
from datetime import date

sys.path.append('../') 
from web.base import get_html


base_url = 'https://www.busfan.club'
permanent_url = 'https://www.javbus.com'


def parse_data(avid):
    """解析指定番号的影片数据"""
    html = get_html(f'{base_url}/{avid}')
    container = html.xpath("/html/body/div[@class='container']")[0]
    title = container.xpath("h3/text()")[0]
    cover = container.xpath("//a[@class='bigImage']/img/@src")
    avatar = container.xpath("//div[@class='star-name']/../a/img/@src")
    sample_pics = container.xpath("div[@id='sample-waterfall']/a/div/img/@src")
    info = container.xpath("//div[@class='col-md-3 info']")[0]
    dvdid = info.xpath("p/span[text()='識別碼:']")[0].getnext().text
    date_str = info.xpath("p/span[text()='發行日期:']")[0].tail.strip()
    pub_date = date.fromisoformat(date_str)
    duration = info.xpath("p/span[text()='長度:']")[0].tail.replace('分鐘', '').strip()
    director = info.xpath("p/span[text()='導演:']")[0].getnext().text.strip()
    # 制作商
    producer = info.xpath("p/span[text()='製作商:']")[0].getnext().text.strip()
    # 发行商
    publisher = info.xpath("p/span[text()='發行商:']")[0].getnext().text.strip()
    genre_tags = info.xpath("p[text()='類別:']")[0].getnext().xpath("span/a")
    genre = [i.text for i in genre_tags]
    magnets = html.xpath("//table[@id='magnet-table']/tr/td[1]/a/@href")
    return


if __name__ == "__main__":
    parse_data('ipx-177')