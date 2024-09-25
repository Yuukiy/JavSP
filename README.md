![JavSP](./image/JavSP.svg)

# Jav Scraper Package

**汇总多站点数据的AV元数据刮削器**

提取影片文件名中的番号信息，自动抓取并汇总多个站点数据的 AV 元数据，按照指定的规则分类整理影片文件，并创建供 Emby、Jellyfin、Kodi 等软件使用的元数据文件

**WebUI**: UI界面不是[此项目的目标](https://github.com/Yuukiy/JavSP/issues/148)。如果你需要这个功能，可以试试[@tetato/JavSP-Docker](https://github.com/tetato/JavSP-Docker)

**i18n**: This project currently supports only Chinese. However, if you're willing, you can [vote here](https://github.com/Yuukiy/JavSP/discussions/157) for the language you'd like to see added

![License](https://img.shields.io/github/license/Yuukiy/JavSP)
[![LICENSE](https://img.shields.io/badge/license-Anti%20996-blue.svg)](https://github.com/996icu/996.ICU/blob/master/LICENSE)
![Python 3.9](https://img.shields.io/badge/python-3.9-green.svg)
[![Crawlers test](https://img.shields.io/github/actions/workflow/status/Yuukiy/JavSP/test-web-funcs.yml?label=crawlers%20test)](https://github.com/Yuukiy/JavSP/actions/workflows/test-web-funcs.yml)
[![Latest release](https://img.shields.io/github/v/release/Yuukiy/JavSP)](https://github.com/Yuukiy/JavSP/releases/latest)
[![996.icu](https://img.shields.io/badge/link-996.icu-red.svg)](https://996.icu)

功能修改日志：[ChangeLog](./CHANGELOG.md)

## 功能特点

下面这些是一些已实现或待实现的功能，在逐渐实现和完善，如果想到新的功能点也会加进来。

- [x] 自动识别影片番号
- [x] 支持处理影片分片
- [x] 汇总多个站点的数据生成NFO数据文件
- [x] 每天自动对站点抓取器进行测试
- [x] 多线程并行抓取
- [x] 下载高清封面
- [x] 基于AI人体分析裁剪素人等非常规封面的海报
- [x] 自动检查和更新新版本
- [x] 翻译标题和剧情简介
- [ ] 匹配本地字幕
- [ ] 使用小缩略图创建文件夹封面
- [ ] 保持不同站点间 genre 分类的统一
- [ ] 不同的运行模式（抓取数据+整理，仅抓取数据）
- [ ] 可选：所有站点均抓取失败时由人工介入

## 安装

#### 想要快速上手？

前往[软件发布页](https://github.com/Yuukiy/JavSP/releases/latest)下载最新版本的软件，无需安装额外工具，开箱即用

#### 更喜欢源代码？
1. 请先确保您已经安装[Poetry](https://python-poetry.org/)构建系统。

```
pipx install poetry
#安装poetry-dynamic-versioning以动态生成版本号。
poetry self add poetry-dynamic-versioning
```
2. 克隆本项目：
```
git clone https://github.com/Yuukiy/JavSP.git
cd JavSP
```

4. 使用poetry构建
```
poetry install
poetry run javsp
```

#### 更喜欢Docker？

请确保已安装Docker

- 直接运行
```
docker run -it --rm -v <YOUR_VIDEO_DIR_PATH>:/video ghcr.io/yuukiy/javsp:latest
```

- 带命令行参数
```
docker run -it --rm -v <YOUR_VIDEO_DIR_PATH>:/video ghcr.io/yuukiy/javsp:latest -h
```

- 使用自己的配置文件

> 注意配置文件中的`scan_dir`配置要和挂载的`/video`目录一致，也可以根据自己的需要进行修改。

```
docker run -it --rm -v <YOUR_VIDEO_DIR_PATH>:/video -v <YOUR_CONFIG_FILE_PATH>:/app/config.ini ghcr.io/yuukiy/javsp:latest
```

## 使用

软件开箱即用，首次运行时会在软件目录下生成默认的配置文件 ```config.ini```。如果想让软件更符合你的使用需求，也许你需要更改配置文件:

> 以任意文本编辑器打开 ```config.ini```，根据各个配置项的说明选择你需要的配置即可。

此外软件也支持从命令行指定运行参数（命令行参数的优先级高于配置文件）。运行 ```JavSP -h``` 查看支持的参数列表

更详细的使用说明请前往 [JavSP Wiki](https://github.com/Yuukiy/JavSP/wiki) 查看

如果使用的时候遇到问题也欢迎给我反馈😊

## 问题反馈

如果使用中遇到了 Bug，请[前往 Issue 区反馈](https://github.com/Yuukiy/JavSP/issues)（提问前请先搜索是否已有类似问题）


## 参与贡献

此项目不需要捐赠。如果你想要帮助改进这个项目，欢迎通过以下方式参与进来（并不仅局限于代码）：

- 帮助撰写和改进Wiki

- 帮助完善单元测试数据（不必非要写代码，例如如果你发现有某系列的番号识别不准确，总结一下提issue也是很好的）

- 帮助翻译 genre

- Bugfix / 新功能？欢迎发 Pull Request

- 要不考虑点个 Star ?（我会很开心的）


## 许可

此项目的所有权利与许可受 GPL-3.0 License 与 [Anti 996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE_CN) 共同限制。此外，如果你使用此项目，表明你还额外接受以下条款：

- 本软件仅供学习 Python 和技术交流使用

- 请勿在微博、微信等墙内的公共社交平台上宣传此项目

- 用户在使用本软件时，请遵守当地法律法规

- 禁止将本软件用于商业用途


---

![Star History Chart](https://api.star-history.com/svg?repos=Yuukiy/JavSP&type=Date)
