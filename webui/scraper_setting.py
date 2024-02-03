import os
import re
import sys
import time
import streamlit as st
from threading import Thread
from configparser import ConfigParser
from streamlit.runtime.scriptrunner.script_run_context import add_script_run_ctx, get_script_run_ctx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from JavSP import scraper


_ = """浏览器缓存值，不随页面刷新而改变"""
if 'key' not in st.session_state:
    st.session_state.counter = 2    # 用来判断组件左右放置位置
    st.session_state.movies_found = 0
    st.session_state.movies_sorted = 0


def get_configures():

    _ = """读取配置文件"""
    file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config = ConfigParser()
    conf_dict = {}              # 参数字典
    config.read(file_path,encoding='utf-8')

    for section in config.sections():
        items = config.items(section)
        mid_conf = {}
        for key,value in items:
            if section == 'OptionAttribute':
                # 参数属性转换成列表
                attributes = value.split(',')
                if '/' in value: 
                    # 选择项转换成列表
                    attributes[2] = attributes[2].split('/')
                mid_conf[key] = list(attributes)
            else:
                mid_conf[key] = value
        conf_dict[section] = mid_conf
    options_attribute = conf_dict['OptionAttribute']

    return conf_dict, options_attribute


def get_attributes(attributes:dict,key:str):
    name = attributes[key][0]
    type = attributes[key][1]
    choices = []
    default = ''
    if len(attributes[key]) == 3:
        choices = attributes[key][2]
    elif len(attributes[key]) == 4:
        default = attributes[key][3]
        if default == 'False':
            default = False
        elif default == 'True':
            default = True

    return name,type,choices,default


def write_configures(settings:dict):
    _ = """将配置参数写入配置文件"""
    config = ConfigParser()
    file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(file_path,encoding='utf-8')

    for key in settings.keys():
        for option,value in settings[key].items():
            if type(value) == bool:
                value = 'yes' if value == True else 'no'
            elif type(value) == list:
                # 读取时将多个选项转化成了列表，这里要转换回字符串
                for i in range(len(value)):
                    if type(value[i]) == list:
                        value[i] = '/'.join(value[i])
                value = ','.join(value)
            else:
                value = str(value)
            
            if key not in config.keys():
                config.add_section(key)
            config.set(key,option,value)
                
            with open(file_path,'w',encoding='utf-8') as file:
                config.write(file)


def other_conf(settings:dict, attributes:dict, names:dict ,required_settings:list):
    for key in settings.keys():

        if key != 'OptionAttribute':    # 生成组件时排除基础配置项，在上面配置
            mid_conf = {}   
            section = names[key]

            with st.expander(section):
                sub_cols =st.columns(2)
                for option in settings[key].keys():
                    # 获取参数属性
                    option_name,option_type,option_choices,option_default = get_attributes(attributes,option)
                    option_value = settings[key][option]
                    
                    _ = """根据参数类型展示组件"""
                    if option not in required_settings:
                        if option_type == 'box':
                            if st.session_state.counter % 2 == 0:
                                mid_conf[option] = sub_cols[0].checkbox(option_name, option_default)
                            else:
                                mid_conf[option] = sub_cols[1].checkbox(option_name, option_default)
                        else:
                            if option_type == 'text':
                                mid_conf[option] = st.text_input(option_name, option_value)
                            elif option_type == 'num':
                                mid_conf[option] = st.number_input(option_name, int(option_value))
                            elif option_type == 'choice':
                                mid_conf[option] = st.selectbox(option_name, option_choices)
                            else:
                                mid_conf[option] = st.multiselect(option_name, option_choices, option_choices)
                    else:
                        if key == 'File':
                            mid_conf[option] = scan_dir
                        else:
                            if option == 'media_servers':
                                mid_conf[option] = media_servers
                            elif option == 'save_type':
                                mid_conf[option] = save_type
                            elif option == 'output_folder':
                                mid_conf[option] = output_folder

                    st.session_state.counter += 1
            settings[key] = mid_conf
    st.session_state.counter = 2


class opened(object):
    def __init__(self, filename):
        self.filename = filename
        self.handle = open(filename)
        if filename in get_read_info().keys():
            self.handle.seek(get_read_info()[filename], 0)

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc_value, exc_trackback):
        seek_num = self.handle.tell()
        set_read_info(self.filename, seek_num)
        self.handle.close()
        if exc_trackback is None:
            print(f'文件【{self.filename}】读取退出正常！')
        else:
            print(f'文件【{self.filename}】读取退出异常！')


def get_read_info():
    # 读取已读取的文件的句柄位置
    file_info = {}
    temp = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'temp')
    # 如果文件不存在则创建一个空文件
    if not os.path.exists(temp):
        with open(temp, 'w', encoding='utf-8') as f:
            pass
        return file_info

    with open(temp, 'r', encoding='utf-8') as f:
        datas = f.readlines()
        for data in datas:
            name, line = data.split('===')
            file_info[name] = int(line)
    return file_info


def set_read_info(filename, seek_num):
    '''
    设置为已经读取的文件的句柄位置
    :param filename: 文件名称
    :param seek_num: 句柄位置
    :return:
    '''
    temp = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'temp')
    flag = True
    with open(temp, 'r', encoding='utf-8') as f:
        datas = f.readlines()
        for num, data in enumerate(datas):
            if filename in data:
                flag = False
                datas[num] = f'{filename}==={seek_num}\n'
        if flag:
            datas.append(f'{filename}==={seek_num}\n')
    # print(datas)
    with open(temp, 'w', encoding='utf-8') as f:
        f.writelines(datas)


def process_dispaly():
    file = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'JavSP.log')
    end_status = ''
    file_name = ''
    main_status = ''

    while True:
        if main_status != 'next':
            with opened(file) as fp:
                for line_data in fp:
                    if re.match(r'^.*正在整理: .*$', line_data):
                        file_name = re.compile(r'^.*正在整理: (.*)$').findall(line_data)[0]
                        main_status = 'next'
                    elif re.match(r'^.*未找到影片文件$', line_data):
                        main_status = 'break'
                    elif re.match(r'^.*扫描影片文件：共找到 .*? 部影片$', line_data):
                        st.session_state.movies_found = int(re.compile(r'^.*扫描影片文件：共找到 (.*?) 部影片$').findall(line_data)[0])
                        main_status = 'continue'
                    elif re.match(r'^.*整理失败.*$', line_data):
                         main_status = 'continue'
                    elif re.match(r'^.*整理完成.*$', line_data):
                        main_status = 'continue'
                    else:
                        main_status = 'continue'

        if main_status == 'break':
            st.warning('**未找到影片！请确定扫描目录是否正确。**', icon='🚨')
            break
        elif main_status == 'continue':
            continue
        elif main_status == 'next':
            main_status = ''
            st.columns(1)
            st.markdown(f'****共找到 {st.session_state.movies_found} 部影片，正在整理第{st.session_state.movies_sorted+1}部：{file_name}****')
            with st.status(f'正在整理...', expanded=False) as status:
                while True:
                    with opened(file) as fp:  # 默认为读模式
                        for line_data in fp:
                            if re.match(r'^.*整理失败.*$', line_data):
                                st.write(line_data)
                                end_status = 'error'
                            elif re.match(r'^.*整理完成.*$', line_data):
                                st.write(line_data)
                                end_status = 'complete'
                            elif re.match(r'^.*正在整理: .*$', line_data):
                                file_name = re.compile(r'^.*正在整理: (.*)$').findall(line_data)[0]
                                main_status = 'next'
                                end_status = 'error' if end_status == 'error' and end_status != '' else 'complete'
                            else:
                                st.write(line_data)
                                end_status = 'error' if end_status == 'error' and end_status != '' else 'complete'
                                

                    if end_status != '':
                        st.session_state.movies_sorted += 1

                        if end_status == 'error':
                            status.update(label='整理失败，请查看详情。', state='error', expanded=False)
                        elif end_status == 'complete':
                            status.update(label='整理完成！', state='complete', expanded=False)
                        else:
                            status.update(label='整理完成！', state='complete', expanded=False)

                        end_status = ''
                        break
                    
                    time.sleep(3)
                    
        if st.session_state.movies_sorted == st.session_state.movies_found:
            st.session_state.movies_sorted = 0
            st.session_state.movies_found = 0
            st.balloons()
            break

        time.sleep(1)

  

_ = """获取/定义一些要用到的数据"""
settings, options_attribute = get_configures()
sections_name = {'MovieID': '番号正则', 'File': '文件识别', 'Network': '网络代理', 'CrawlerSelect': '爬虫列表', 'Crawler': '爬虫配置', 'ProxyFree': '免代理地址', 'NamingRule': '命名规则', 'Picture': '封面配置', 'Translate': '翻译配置', 'NFO': 'NFO配置', 'Other': '其他配置', 'OptionAttribute': '参数属性'}
required_settings = ['scan_dir', 'output_folder', 'save_type', 'media_servers']
# 判断必要参数是否已保存到配置文件中
saved = False if settings['File']['scan_dir'] != '' and settings['NamingRule']['output_folder']  != '' else True


_ = """以下是页面交互部分"""
# streamlit要求的页面配置
st.set_page_config(page_icon='', page_title='设置页')   


_ = """侧边栏参数设置菜单"""
with st.sidebar:
    with st.expander('基础配置',expanded=True):
        scan_dir = st.text_input('扫描目录', settings['File']['scan_dir'], placeholder = '请输入要整理的文件夹位置')
        output_folder = st.text_input('保存目录', settings['NamingRule']['output_folder'], placeholder = '最终文件的保存位置')
        save_type = st.selectbox('保存方式',options_attribute['save_type'][2])
        media_servers = st.selectbox('媒体服务器',options_attribute['media_servers'][2])

    _ = """其他参数配置组件"""
    other_conf(settings,options_attribute,sections_name,required_settings)

    _ = """保存按钮"""
    option_filled = False if settings['File']['scan_dir'] != '' and settings['NamingRule']['output_folder']  != '' else True
    save_optinons = st.button('保存参数', type='primary', disabled=option_filled, use_container_width=True)

    if save_optinons:
        # 将配置的参数写入配置文件中
        write_configures(settings)
        # 更新配置文件的状态，使主页面执行按钮可点击
        saved = False
        st.toast('保存成功', icon='😍')


_ = """主页面"""


submit = st.button('开始程序', type='primary', disabled=saved)
if submit:
    # 调用刮削程序
    jsp_thread = Thread(target=scraper)
    add_script_run_ctx(jsp_thread)
    jsp_thread.start()

    # 展示进度
    process_dispaly()
