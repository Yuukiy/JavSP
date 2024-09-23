![JavSP](https://github.com/Yuukiy/JavSP/blob/master/image/javsp_logo.png?raw=true)

# Jav Scraper Package

**A Jav (Japanese Adult Video) Scraper that collects and summarizes metadata from multiple websites**

By grabbing the bangou in the file name, JavSP can pull data from multiple websites and summarize them, classify them according to a predefined rule and create metadata for softwares like Emby, Jellyfin and Kodi.

**Docker & WebUI**: Due to limited spare time, there's no Docker support yet. Additionally, a GUI is not [the focus of this project](https://github.com/Yuukiy/JavSP/issues/148). If you need Docker support, maybe you can give [JavSP-Docker](https://github.com/tetato/JavSP-Docker) a try.

**i18n**: This project currently supports only Chinese. [Vote here](https://github.com/Yuukiy/JavSP/discussions/157) for i18n support.

![License](https://img.shields.io/github/license/Yuukiy/JavSP)
[![LICENSE](https://img.shields.io/badge/license-Anti%20996-blue.svg)](https://github.com/996icu/996.ICU/blob/master/LICENSE)
![Python 3.8](https://img.shields.io/badge/python-3.8-green.svg)
[![Crawlers test](https://img.shields.io/github/actions/workflow/status/Yuukiy/JavSP/test-web-funcs.yml?label=crawlers%20test)](https://github.com/Yuukiy/JavSP/actions/workflows/test-web-funcs.yml)
[![Latest release](https://img.shields.io/github/v/release/Yuukiy/JavSP)](https://github.com/Yuukiy/JavSP/releases/latest)
[![996.icu](https://img.shields.io/badge/link-996.icu-red.svg)](https://996.icu)

## Features

This is a non-exhaustive list of implemented and unimplemented features being refined over time.

- [x] Recognize movie ID automagically
- [x] Dealing with movies separated into multiple parts
- [x] Summarize information from multiple sites to generate [NFO file](https://jellyfin.org/docs/general/server/metadata/nfo/).
- [x] Automatic tests for website crawler on a daily basis
- [x] Parallel data scraping
- [x] Downloading HD covers
- [x] AI based cover crop for atypical covers
- [x] Automatic version-checking and self-updating
- [x] Translating titles and descriptions
- [ ] Matching local subtitles
- [ ] Using thumb to create folder cover
- [ ] Keeping genre consistency across different websites
- [ ] Different mode of operations(Scraping and Moving, Scrape only)
- [ ] Optional: Allow user to interveine when there's a conflicts during scrapping.

## Installation

- For the impatient

	Visit [Github Release Page](https://github.com/Yuukiy/JavSP/releases/latest) and download the latest portable version of JavSP (Windows only).

- Buliding from source
  - Ensure you have Python >= 3.8
  - Run the following

	```
	git clone https://github.com/Yuukiy/JavSP.git
	cd JavSP
	pip install -r requirements.txt
	python JavSP.py
	```

## Usage

With a portable version, the executable `JavSP` will generate a ```config.ini``` during first invocation. You can modify the configuration file to instruct how `JavSP` should work for you.

JavSP also accepts CLI flags and prioritize them over `config.ini`, you can run `JavSP -h` to see a list of supportted flags.

For more detailed instructions please visit [JavSP Wiki](https://github.com/Yuukiy/JavSP/wiki)

Please file an issue if you find any problem using this software.😊

## Bug report

If you encounter any bug that is not already encountered by other users (you can check this by searching through the issue page), don't hesitate to go and [file an isssue](https://github.com/Yuukiy/JavSP/issues).


## Contribution

No need to buy me any coffee LoL. If you like to help, please help me through these methods:

- Help writing and improving the Wiki

- Help completing the Unit Test (Not necessarilly coding, testcases or insightful obvervations are also welcomed)

- Help translating the genre

- Pull Request for bug fix or new feature

- Consider giving it a star? (I would be very happy about it)


## License

This project is under the restriction of both the GPL-3.0 License and the [Anti 996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE). On top of that, using this project implies that you accept the following terms:

- Please don't promote this project on any Chinese social media like Weibo or WeChat, which are subject to censorship.

- Please comply with your local laws and regulations when using this project.

- Making profit out of this project is prohibited.

---

![Star History Chart](https://api.star-history.com/svg?repos=Yuukiy/JavSP&type=Date)
