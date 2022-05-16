"""获取airav指定关键词的所有搜索结果"""
import os
import sys
import json


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web.base import Request

request = Request()
request.headers['Accept-Language'] = 'zh-TW,zh;q=0.9'

base_url = 'https://www.airav.wiki'


def search(keyword):
    """搜索指定影片的所有结果"""
    all_results = []
    page = 1
    data = {'offset': 0, 'count': 1, 'result': []}
    while (data['offset'] + len(data['result']) < data['count']):
        url = f'{base_url}/api/video/list?lang=zh-TW&lng=zh-TW&search={keyword}&page={page}'
        data = request.get(url).json()
        all_results.extend(data['result'])
        print(f"Get page {page}: {len(data['result'])} movie(s)")
        page += 1
    for i in all_results:
        if not i['url']:
            i['url'] = f"{base_url}/video/{i['barcode']}"
    return all_results


if __name__ == "__main__":
    keyword = '版'
    results = search(keyword)
    with open(f'airav_search_{keyword}.json', 'wt', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
