"""网页翻译接口"""
# 由于翻译服务不走代理，而且需要自己的错误处理机制，因此不通过base.py来管理网络请求
import time
from typing import Union
import uuid
import random
import logging
from pydantic_core import Url
import requests
from hashlib import md5


__all__ = ['translate', 'translate_movie_info']


from javsp.config import BaiduTranslateEngine, BingTranslateEngine, Cfg, ClaudeTranslateEngine, GoogleTranslateEngine, OpenAITranslateEngine, TranslateEngine
from javsp.datatype import MovieInfo
from javsp.web.base import read_proxy


logger = logging.getLogger(__name__)


def translate_movie_info(info: MovieInfo):
    """根据配置翻译影片信息"""
    # 翻译标题
    if info.title and Cfg().translator.fields.title and info.ori_title is None:
        result = translate(info.title, Cfg().translator.engine, info.actress)
        if 'trans' in result:
            info.ori_title = info.title
            info.title = result['trans']
            # 如果有的话，附加断句信息
            if 'orig_break' in result:
                setattr(info, 'ori_title_break', result['orig_break'])
            if 'trans_break' in result:
                setattr(info, 'title_break', result['trans_break'])
        else:
            logger.error('翻译标题时出错: ' + result['error'])
            return False
    # 翻译简介
    if info.plot and Cfg().translator.fields.plot:
        result = translate(info.plot, Cfg().translator.engine, info.actress)
        if 'trans' in result:
            # 只有翻译过plot的影片才可能需要ori_plot属性，因此在运行时动态添加，而不添加到类型定义里
            setattr(info, 'ori_plot', info.plot)
            info.plot = result['trans']
        else:
            logger.error('翻译简介时出错: ' + result['error'])
            return False
    return True

def translate(texts, engine: Union[
        BaiduTranslateEngine,
        BingTranslateEngine,
        ClaudeTranslateEngine,
        OpenAITranslateEngine,
        None
    ], actress=[]):
    """
    翻译入口：对错误进行处理并且统一返回格式

    Returns:
        dict: 翻译正常: {'trans': '译文', 'orig_break':['原句1', ...], 'trans_break': ['译句1', ...]}
              仅在能判断分句时有breaks字段，子句末尾可能有换行符\n
              翻译出错: {'error': 'baidu: 54000: PARAM_FROM_TO_OR_Q_EMPTY'}
    """
    rtn = {}
    err_msg = ''
    if engine.name == 'baidu':
        result = baidu_translate(texts, engine.app_id, engine.api_key)
        if 'error_code' not in result:
            # 百度翻译的结果中的组表示的是按换行符分隔的不同段落，而不是句子
            paragraphs = [i['dst'] for i in result['trans_result']]
            rtn = {'trans': '\n'.join(paragraphs)}
        else:
            err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
    elif engine.name == 'bing':
        # 使用动态词典保护原文中的女优名，防止翻译后认不出来
        for i in actress:
            texts = texts.replace(i, f'<mstrans:dictionary translation="{i}">{i}</mstrans:dictionary>')
        result = bing_translate(texts, api_key=engine.api_key)
        if 'error' not in result:
            sentLen = result[0]['translations'][0]['sentLen']
            orig_break, trans_break = [], []
            # 对原文进行断句
            remaining = texts
            for i in sentLen['srcSentLen']:
                orig_break.append(remaining[:i])
                remaining = remaining[i:]
            # 对译文进行断句
            remaining = result[0]['translations'][0]['text']
            for i in sentLen['transSentLen']:
                # Bing会在译文的每个句尾添加一个空格，这并不符合中文的标点习惯，所以去掉这个空格
                trans_break.append(remaining[:i].rstrip(' '))
                remaining = remaining[i:]
            trans = ''.join(trans_break)
            rtn = {'trans': trans, 'orig_break': orig_break, 'trans_break': trans_break}
        else:
            err_msg = "{}: {}: {}".format(engine, result['error']['code'], result['error']['message'])
    elif engine.name == 'claude':
        try:
            result = claude_translate(texts, engine.api_key)
            if 'error_code' not in result:
                rtn = {'trans': result}
            else:
                err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
        except Exception as e:
            err_msg = "{}: {}: Exception: {}".format(engine, -2, repr(e))
    elif engine.name == 'openai':
        try:
            result = openai_translate(texts, engine.url, engine.api_key, engine.model)
            if 'error_code' not in result:
                rtn = {'trans': result}
            else:
                err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
        except Exception as e:
            err_msg = "{}: {}: Exception: {}".format(engine, -2, repr(e))
    elif engine.name == 'google':
        try:
            result = google_trans(texts)
            # 经测试，翻译成功时会带有'sentences'字段；失败时不带，也没有故障码
            if 'sentences' in result:
                # Google会对句子分组，完整的译文需要自行拼接
                orig_break = [i['orig'] for i in result['sentences']]
                trans_break = [i['trans'] for i in result['sentences']]
                trans = ''.join(trans_break)
                rtn = {'trans': trans, 'orig_break': orig_break, 'trans_break': trans_break}
            else:
                err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
        except Exception as e:
            err_msg = "{}: {}: Exception: {}".format(engine, -2, repr(e))
    else:
        return {'trans': texts}

def baidu_translate(texts, app_id, api_key, to='zh'):
    """使用百度翻译文本（默认翻译为简体中文）"""
    api_url = "https://api.fanyi.baidu.com/api/trans/vip/translate"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    salt = random.randint(0, 0x7FFFFFFF)
    sign_input = app_id + texts + str(salt) + api_key
    sign = md5(sign_input.encode('utf-8')).hexdigest()
    payload = {'appid': app_id, 'q': texts, 'from': 'auto', 'to': to, 'salt': salt, 'sign': sign}
    # 由于百度标准版限制QPS为1，连续翻译标题和简介会超限，因此需要添加延时
    now = time.perf_counter()
    last_access = getattr(baidu_translate, '_last_access', -1)
    wait = 1.0 - (now - last_access)
    if wait > 0:
        time.sleep(wait)
    r = requests.post(api_url, params=payload, headers=headers)
    result = r.json()
    baidu_translate._last_access = time.perf_counter()
    return result


def bing_translate(texts, api_key, to='zh-Hans'):
    """使用Bing翻译文本（默认翻译为简体中文）"""
    api_url = "https://api.cognitive.microsofttranslator.com/translate"
    params = {'api-version': '3.0', 'to': to, 'includeSentenceLength': True}
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Ocp-Apim-Subscription-Region': 'global',
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    body = [{'text': texts}]
    r = requests.post(api_url, params=params, headers=headers, json=body)
    result = r.json()
    return result


_google_trans_wait = 60
def google_trans(texts, to='zh_CN'):
    """使用Google翻译文本（默认翻译为简体中文）"""
    # API: https://www.jianshu.com/p/ce35d89c25c3
    # client参数的选择: https://github.com/lmk123/crx-selection-translate/issues/223#issue-184432017
    global _google_trans_wait
    url = f"https://translate.google.com.hk/translate_a/single?client=gtx&dt=t&dj=1&ie=UTF-8&sl=auto&tl={to}&q={texts}"
    proxies = read_proxy()
    r = requests.get(url, proxies=proxies)
    while r.status_code == 429:
        logger.warning(f"HTTP {r.status_code}: {r.reason}: Google翻译请求超限，将等待{_google_trans_wait}秒后重试")
        time.sleep(_google_trans_wait)
        r = requests.get(url, proxies=proxies)
        if r.status_code == 429:
            _google_trans_wait += random.randint(60, 90)
    if r.status_code == 200:
        result = r.json()
    else:
        result = {'error_code': r.status_code, 'error_msg': r.reason}
    time.sleep(4) # Google翻译的API有QPS限制，因此需要等待一段时间
    return result

def claude_translate(texts, api_key, to="zh_CN"):
    """使用Claude翻译文本（默认翻译为简体中文）"""
    api_url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "context-type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    data = {
        "model": "claude-3-haiku-20240307",
        "system": f"Translate the following Japanese paragraph into {to}, while leaving non-Japanese text, names, or text that does not look like Japanese untranslated. Reply with the translated text only, do not add any text that is not in the original content.",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": texts}],
    }
    r = requests.post(api_url, headers=headers, json=data)
    if r.status_code == 200:
        result = r.json().get("content", [{}])[0].get("text", "").strip()
    else:
        result = {
            "error_code": r.status_code,
            "error_msg": r.json().get("error", {}).get("message", r.reason),
        }
    return result

def openai_translate(texts, url: Url, api_key: str, model: str, to="zh_CN"):
    """使用 OpenAI 翻译文本（默认翻译为简体中文）"""
    api_url = str(url)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = {
         "messages": [
           {
             "role": "system",
             "content": f"Translate the following Japanese paragraph into {to}, while leaving non-Japanese text, names, or text that does not look like Japanese untranslated. Reply with the translated text only, do not add any text that is not in the original content."
           },
           {
             "role": "user",
             "content": texts
           }
         ],
         "model": model,
         "temperature": 0,
         "max_tokens": 1024,
    }
    r = requests.post(api_url, headers=headers, json=data)
    if r.status_code == 200:
        if 'error' in r.json():
            result = {
                "error_code": r.status_code,
                "error_msg": r.json().get("error", {}).get("message", ""),
            }
        else:
            result = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    else:
        result = {
            "error_code": r.status_code,
            "error_msg": r.reason,
        }
    return result
