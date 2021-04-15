"""网页翻译接口"""
import os
import sys
import uuid
import requests


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg


def bing_translate(texts, to='zh-Hans'):
    """使用Bing翻译文本（默认翻译为简体中文）"""
    api_url = "https://api.cognitive.microsofttranslator.com/translate"
    params = {'api-version': '3.0', 'to': to}
    headers = {
        'Ocp-Apim-Subscription-Key': cfg.Translate.bing_key,
        'Ocp-Apim-Subscription-Region': cfg.Translate.bing_region,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    body = [{'text': texts}]
    # https://docs.microsoft.com/zh-cn/azure/cognitive-services/translator/reference/v3-0-reference#errors
    request = requests.post(api_url, params=params, headers=headers, json=body)
    response = request.json()

    return response[0]['translations']


if __name__ == "__main__":
    print(bing_translate('Hello world~'))
