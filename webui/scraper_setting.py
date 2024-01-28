import sys
import os
import streamlit as st
from configparser import ConfigParser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from JavSP import main as Jav
from core.config import args

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

            _ = """浏览器缓存一个值，用来判断组件左右放置位置"""
            if 'key' not in st.session_state:
                st.session_state.counter = 2
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
                            else:
                                mid_conf[option] = output_folder
                    st.session_state.counter += 1
            settings[key] = mid_conf
    st.session_state.counter = 2


_ = """获取/定义一些要用到的数据"""
settings, options_attribute = get_configures()
sections_name = {'MovieID': '番号正则', 'File': '文件识别', 'Network': '网络代理', 'CrawlerSelect': '爬虫列表', 'Crawler': '爬虫配置', 'ProxyFree': '免代理地址', 'NamingRule': '命名规则', 'Picture': '封面配置', 'Translate': '翻译配置', 'NFO': 'NFO配置', 'Other': '其他配置', 'OptionAttribute': '参数属性'}
required_settings = ['scan_dir','output_folder','media_servers']
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


_ = """主页面"""

st.subheader('执行情况')
submit = st.button('开始程序', type='primary', disabled=saved)
if submit:
    # 调用主程序按钮
    Jav()
    





