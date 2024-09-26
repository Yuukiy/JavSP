# Changelog

## [Unreleased]

### Added
- 添加无码和字幕的水印 [#73](https://github.com/Yuukiy/JavSP/commit/eaedc84049597eaab1ba064229f9b5bcf38aa504)
- 支持刮削剧照 [#176](https://github.com/Yuukiy/JavSP/issues/176)
- direnv 适配 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 添加硬链接支持 [#374](https://github.com/Yuukiy/JavSP/pull/374)
- 添加Docker镜像，每次tag发布将会同步更新一个Docker镜像到ghcr.io上。[#322](https://github.com/Yuukiy/JavSP/pull/322)

  参见[Package javsp](https://github.com/Yuukiy/JavSP/pkgs/container/javsp)。
- 添加新的爬虫`arzon`, `arzon_iv` [#377](https://github.com/Yuukiy/JavSP/pull/377)

### Changed
- 使用 Poetry 作为构建系统 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 使用 Cx_Freeze 作为打包工具 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- 将 Groq 翻译接口重构为 OpenAI 通用翻译接口 [#371](https://github.com/Yuukiy/JavSP/pull/371)
- FIX: 修复图标没有添加到封面上的 bug [#262](https://github.com/Yuukiy/JavSP/issues/176)
- 用更高清的Logo替换旧的Logo [7b8690f](https://github.com/Yuukiy/JavSP/commit/7b8690fb4af831c0e5ad5ed97cac61d51117c7eb)

### Removed
- Pyinstaller 打包描述文件 [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
- requirements.txt [134b279](https://github.com/Yuukiy/JavSP/commit/134b279151aead587db0b12d1a30781f2e1be5b1)
