"""网页翻译接口"""
# 由于翻译服务不走代理，而且需要自己的错误处理机制，因此不通过base.py来管理网络请求
import os
import sys
import uuid
import random
import logging
import requests
from hashlib import md5


__all__ = ['translate', 'translate_movie_info']


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import cfg
from core.datatype import MovieInfo


logger = logging.getLogger(__name__)


def translate_movie_info(info: MovieInfo):
    """根据配置翻译影片信息"""
    # 由于百度标准版限制QPS为1，连续翻译标题和简介会超限，只好把它们合成为一次请求来翻译
    if cfg.Translate.engine == 'baidu':
        if info.title and cfg.Translate.translate_title and info.plot and cfg.Translate.translate_plot:
            orig_texts = info.title + '\n' + info.plot
            result = translate(orig_texts, cfg.Translate.engine)
            if 'trans' in result:
                trans_groups = result['trans'].split('\n')
                info.ori_title = info.title
                info.title = trans_groups[0]
                info.plot = trans_groups[1]
                return True
            else:
                logger.error('翻译标题和简介时出错: ' + result['error'])
                return False
    # 其他情况下分两次翻译标题和简介
    if info.title and cfg.Translate.translate_title:
        result = translate(info.title, cfg.Translate.engine)
        if 'trans' in result:
            info.ori_title = info.title
            info.title = result['trans']
        else:
            logger.error('翻译标题时出错: ' + result['error'])
            return False
    if info.plot and cfg.Translate.translate_plot:
        result = translate(info.plot, cfg.Translate.engine)
        if 'trans' in result:
            # 只有翻译过plot的影片才可能需要ori_plot属性，因此在运行时动态添加，而不添加到类型定义里
            setattr(info, 'ori_plot', info.plot)
            info.plot = result['trans']
        else:
            logger.error('翻译简介时出错: ' + result['error'])
            return False
    return True


# 不同的翻译引擎支持的功能不同。Bing额外支持断句和动态词典功能，前者可以用于识别句子位置，在需要截短标题时使用；
# 后者可以用来保护原文中的女优名等字段，防止翻译后认不出来
def translate(texts, engine='baidu'):
    """
    翻译入口：对错误进行处理并且统一返回格式

    Returns:
        dict: 翻译正常: {'trans': '译文', 'sentences': ['子句1', ...]}, 仅在能判断分句时有sentences字段，子句末尾可能有换行符
              翻译出错: {'error': 'baidu: 54000: PARAM_FROM_TO_OR_Q_EMPTY'}
    """
    err_msg = ''
    if engine == 'baidu':
        result = baidu_translate(texts)
        if 'error_code' not in result:
            # 百度翻译的结果中的组表示的是不同段落，而非不同句子
            paragraphs = [i['dst'] for i in result['trans_result']]
            rtn = {'trans': '\n'.join(paragraphs)}
        else:
            err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
    elif engine == 'bing':
        # https://docs.microsoft.com/zh-cn/azure/cognitive-services/translator/reference/v3-0-reference#errors
        result = bing_translate(texts)
        if 'error' not in result:
            trans = result[0]['translations'][0]['text']
            sentences = []
            remaining = trans
            # 根据断句结果（各句子的长度）生成各子句
            for i in result[0]['translations'][0]['sentLen']['transSentLen']:
                # Bing会在每个句子末尾添加一个空格，但这并不符合中文的标点习惯，所以去掉这个空格
                sentences.append(remaining[:i].rstrip(' '))
                remaining = remaining[i:]
            rtn = {'trans': ''.join(sentences), 'sentences': sentences}
        else:
            err_msg = "{}: {}: {}".format(engine, result['error']['code'], result['error']['message'])
    elif engine == 'google':
        try:
            result = google_trans(texts)
            # 经测试，翻译成功时会带有'sentences'字段；失败时不带，也没有故障码
            if 'sentences' in result:
                # Google会对句子分组，完整的译文需要自行拼接
                sentences = [i['trans'] for i in result['sentences']]
                trans = ''.join(sentences)
                rtn = {'trans': trans, 'sentences': sentences}
            else:
                err_msg = "{}: {}: {}".format(engine, result['error_code'], result['error_msg'])
        except Exception as e:
            err_msg = "{}: {}: Exception: {}".format(engine, -2, repr(e))
    # else:
        # 配置文件中已经检查过翻译引擎，这里不再检查，因此如果使用不在列表中的翻译引擎，会出错
    # 如果err_msg非空，说明发生了错误，返回错误消息
    if err_msg != '':
        rtn = {'error': err_msg}
    return rtn


def bing_translate(texts, to='zh-Hans'):
    """使用Bing翻译文本（默认翻译为简体中文）"""
    api_url = "https://api.cognitive.microsofttranslator.com/translate"
    params = {'api-version': '3.0', 'to': to, 'includeSentenceLength': True}
    headers = {
        'Ocp-Apim-Subscription-Key': cfg.Translate.bing_key,
        'Ocp-Apim-Subscription-Region': 'global',
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    body = [{'text': texts}]
    r = requests.post(api_url, params=params, headers=headers, json=body)
    result = r.json()
    return result


def baidu_translate(texts, to='zh'):
    """使用百度翻译文本（默认翻译为简体中文）"""
    api_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    appid = cfg.Translate.baidu_appid
    appkey = cfg.Translate.baidu_key
    salt = random.randint(0, 0x7FFFFFFF)
    sign_input = appid + texts + str(salt) + appkey
    sign = md5(sign_input.encode('utf-8')).hexdigest()
    payload = {'appid': appid, 'q': texts, 'from': 'auto', 'to': to, 'salt': salt, 'sign': sign}
    r = requests.post(api_url, params=payload, headers=headers)
    result = r.json()
    return result


def google_trans(texts, to='zh_CN'):
    """使用Google翻译文本（默认翻译为简体中文）"""
    # API: https://www.jianshu.com/p/ce35d89c25c3
    # client参数的选择: https://github.com/lmk123/crx-selection-translate/issues/223#issue-184432017
    url = f"http://translate.google.cn/translate_a/single?client=at&dt=t&dj=1&ie=UTF-8&sl=auto&tl={to}&q=" + texts
    r = requests.get(url)
    if r.status_code == 200:
        result = r.json()
    else:
        result = {'error_code': r.status_code, 'error_msg': r.reason}
    return result


if __name__ == "__main__":
    orig = 'Hello World!'
    print(translate(orig, 'bing'))
    print(translate(orig, 'baidu'))
    print(translate(orig, 'google'))
