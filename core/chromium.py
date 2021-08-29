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
    user_data_dirs = {
        'Chrome':  '/Google/Chrome/User Data',
        'Edge':    '/Microsoft/Edge/User Data',
        'Vivaldi': '/Vivaldi/User Data'
    }
    LocalAppDataDir = os.getenv('LOCALAPPDATA')
    all_browser_cookies = []
    for brw, path in user_data_dirs.items():
        user_dir = LocalAppDataDir + path
        cookies_files = glob(user_dir+'/*/Cookies')
        local_state = user_dir+'/Local State'
        if os.path.exists(local_state):
            key = decrypt_key(local_state)
            decrypter = Decrypter(key)
            for file in cookies_files:
                profile = brw + ": " + os.path.split(os.path.dirname(file))[1]
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
    with open(local_state, 'rt') as file:
        encrypted_key = json.loads(file.read())['os_crypt']['encrypted_key']
    encrypted_key = base64.b64decode(encrypted_key)                                       # Base64 decoding
    encrypted_key = encrypted_key[5:]                                                     # Remove DPAPI
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]  # Decrypt key
    return decrypted_key


def get_cookies(cookies_file, decrypter, host_pattern='javdb%.com'):
    """从cookies_file文件中查找指定站点的所有Cookies"""
    # 复制Cookies文件到当前目录，避免直接操作原始的Cookies文件
    temp_cookie = './Cookies'
    copyfile(cookies_file, temp_cookie)
    # 连接数据库进行查询
    conn = sqlite3.connect(temp_cookie)
    cursor = conn.cursor()
    cursor.execute(f'SELECT host_key, name, encrypted_value, expires_utc FROM cookies WHERE host_key LIKE "{host_pattern}"')
    # 将查询结果按照host_key进行组织
    records = {}
    for host_key, name, encrypted_value, expires_utc in cursor.fetchall():
        d = records.setdefault(host_key, {})
        d[name] = decrypter.decrypt(encrypted_value)
        # d['expires'] = convert_chrome_utc(expires_utc)
    conn.close()
    os.remove(temp_cookie)
    return records


if __name__ == "__main__":
    all_cookies = get_browsers_cookies()
    # with open('cookies.json', 'wt') as f:
    #     json.dump(all_cookies, f, indent=2)
    for d in all_cookies:
        print('{:<20}{}'.format(d['profile'], d['site']))

