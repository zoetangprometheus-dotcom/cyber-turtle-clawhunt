# 第三方来源

## I Ching 数据

- 上游：https://github.com/jesshewitt/i-ching
- 文件：`site/data/hexagrams.json`、`site/data/trigrams.json`
- 许可：CC0 1.0 Universal，全文保存在 `research/LICENSE-translation.txt`
- 抓取日期：2026-10-31；抓取时使用 main，未固定 commit。原始文件 SHA-256 见 `research/source-manifest.json`。
- 原始快照和上游 README 保留于 research，仅作为出处与研究证据，不是运行时依赖。

本项目从快照提取卦名和爻值，生成 `data/hexagrams.json`；将上游由上至下的 7/8 转为本项目由下至上的 1/0，并推导上下卦。数据也打包进 `h5/data.js`。上游翻译为 AI 辅助翻译并经作者编辑，不是已经核对的中文经典资料。当前结构检查通过，文化解释仍待审核。

未引入该上游的应用代码、字体或 UI。前端使用系统字体与原生 Canvas，无运行时第三方库。原创项目代码的许可证由团队另行决定。

## 本机纸签渲染

- 复用环境已有的 [Pillow](https://github.com/python-pillow/Pillow) 11.3.0，HPND 许可，依赖包保留其许可证；未复制上游代码到项目。
- 纸签调用本机 macOS 的 Songti 与 STHeiti 字体，不在仓库分发字体文件。用户提供的长签照片仅作为分区与层级参考，未复制原图中的商标、插画或数值内容。

## ESP32 固件

- 板卡基础来自 [Waveshare 官方示例](https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-1.28/ESP32-S3-Touch-LCD-1.28-Demo.zip)，下载压缩包 SHA-256 固定在 `scripts/firmware.py`。整个示例不作为一个统一许可证项目重新发布。
- `firmware/cyber_turtle/CST816S.cpp/.h` 来自该示例的 CST816S 库，Felix Biego，MIT，文件保留完整许可。修改了中断事件标志的 volatile 和初始值。
- `firmware/cyber_turtle/qrcodegen.c/.h` 来自示例所含 LVGL 的 Nayuki QR Code generator，MIT，原文件保留完整许可；未引入 LVGL 运行时。
- TFT_eSPI 2.5.34 与 Waveshare Setup207 配置通过脚本下载到本地，不提交库副本；[Bodmer/TFT_eSPI](https://github.com/Bodmer/TFT_eSPI) 为 MIT，下载库保留原许可证。
- [U8g2_for_TFT_eSPI](https://github.com/Bodmer/U8g2_for_TFT_eSPI) 1.7.0 使用 BSD 2-Clause 风格许可，完整声明位于其源文件头。脚本对下载快照做 SHA-256 校验；字体遵循各自许可，不全部归属于库许可。
- 中文使用 `u8g2_font_wqy16_t_gb2312`，文泉驿点阵宋体；[上游字体说明](https://github.com/olikraus/u8g2/wiki/fntgrpwqy)列明 Copyright (C)2004–2010 WenQuanYi Project Board of Trustees and Qianqian Fang，GPL v2 with font embedding exception。字体源与转换路径见该说明。此轮本地编译烧录，未发布固件二进制；分发二进制时同时提供所用库/字体的完整许可与对应源材料。
- Apple Silicon 本地构建工具 Arduino ctags 5.8-arduino11 来源 [arduino/ctags](https://github.com/arduino/ctags)，GPL v2；仅用于构建，不链接入设备固件。本地将旧的保留字宏改名以兼容 macOS SDK。工具代码及许可保留在 `.local/esp32/vendor/`。
