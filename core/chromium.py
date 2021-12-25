"""解析Chromium系浏览器Cookies的相关函数"""
import os
import json
import base64
import sqlite3
from glob import glob
from shutil import copyfile
from datetime import datetime

import win32crypt
from Crypto.Cipher import AES


__all__ = ['get_browsers_cookies']


class Decrypter():
    def __init__(self, key):
        self.key = key
    def decrypt(self, encrypted_value):
        nonce = encrypted_value[3:3+12]
        ciphertext = encrypted_value[3+12:-16]
        tag = encrypted_value[-16:]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
        return plaintext


def get_browsers_cookies():
    """获取系统上的所有Chromium系浏览器的JavDB的Cookies"""
    # 不予支持: Opera, 360安全&极速, 搜狗使用非标的用户目录或数据格式; QQ浏览器屏蔽站点
    user_data_dirs = {
        'Chrome':        '/Google/Chrome/User Data',
        'Chrome Beta':   '/Google/Chrome Beta/User Data',
        'Chrome Canary': '/Google/Chrome SxS/User Data',
        'Chromium':      '/Google/Chromium/User Data',
        'Edge':          '/Microsoft/Edge/User Data',
        'Vivaldi':       '/Vivaldi/User Data'
    }
    LocalAppDataDir = os.getenv('LOCALAPPDATA')
    all_browser_cookies = []
    for brw, path in user_data_dirs.items():
        user_dir = LocalAppDataDir + path
        cookies_files = glob(user_dir+'/*/Cookies') + glob(user_dir+'/*/Network/Cookies')
        local_state = user_dir+'/Local State'
        if os.path.exists(local_state):
            key = decrypt_key(local_state)
            decrypter = Decrypter(key)
            for file in cookies_files:
                profile = brw + ": " + file.split('User Data')[1].split(os.sep)[1]
                records = get_cookies(file, decrypter)
                if records:
                    # 将records转换为便于使用的格式
                    for site, cookies in records.items():
                        entry = {'profile': profile, 'site': site, 'cookies': cookies}
                        all_browser_cookies.append(entry)
    return all_browser_cookies


def convert_chrome_utc(chrome_utc):
    """将Chrome存储的UTC时间转换为UNIX的UTC时间格式"""
    # Chrome's cookies timestamp's epoch starts 1601-01-01T00:00:00Z
    second = int(chrome_utc / 1e6)
    unix_utc = datetime.fromtimestamp(second - 11644473600)
    return unix_utc


def decrypt_key(local_state):
    """从Local State文件中提取并解密出Cookies文件的密钥"""
    # Chrome 80+ 的Cookies解密方法参考自: https://stackoverflow.com/a/60423699/6415337
    with open(local_state, 'rt', encoding='utf-8') as file:
        encrypted_key = json.loads(file.read())['os_crypt']['encrypted_key']
    encrypted_key = base64.b64decode(encrypted_key)                                       # Base64 decoding
    encrypted_key = encrypted_key[5:]                                                     # Remove DPAPI
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]  # Decrypt key
    return decrypted_key


def get_cookies(cookies_file, decrypter, host_pattern='javdb%.com'):
    """从cookies_file文件中查找指定站点的所有Cookies"""
    # 复制Cookies文件到临时目录，避免直接操作原始的Cookies文件
    temp_dir = os.getenv('TMPDIR', os.getenv('TEMP', os.getenv('TMP', '.')))
    temp_cookie = os.path.join(temp_dir, 'Cookies')
    copyfile(cookies_file, temp_cookie)
    # 连接数据库进行查询
    conn = sqlite3.connect(temp_cookie)
    cursor = conn.cursor()
    cursor.execute(f'SELECT host_key, name, encrypted_value, expires_utc FROM cookies WHERE host_key LIKE "{host_pattern}"')
    # 将查询结果按照host_key进行组织
    now = datetime.now()
    records = {}
    for host_key, name, encrypted_value, expires_utc in cursor.fetchall():
        d = records.setdefault(host_key, {})
        # 只提取尚在有效期内的Cookies
        expires = convert_chrome_utc(expires_utc)
        if expires > now:
            d[name] = decrypter.decrypt(encrypted_value)
    # Cookies的核心字段是'_jdb_session'，因此如果records中缺失此字段（说明已过期），则对应的Cookies不再有效
    valid_records = {k: v for k, v in records.items() if '_jdb_session' in v}
    conn.close()
    os.remove(temp_cookie)
    return valid_records


if __name__ == "__main__":
    all_cookies = get_browsers_cookies()
    for d in all_cookies:
        print('{:<20}{}'.format(d['profile'], d['site']))

