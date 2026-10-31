# 第三方来源

## I Ching 数据

- 上游：https://github.com/jesshewitt/i-ching
- 文件：`site/data/hexagrams.json`、`site/data/trigrams.json`
- 许可：CC0 1.0 Universal，全文保存在 `research/LICENSE-translation.txt`
- 抓取日期：2026-10-31；抓取时使用 main，未固定 commit。原始文件 SHA-256 见 `research/source-manifest.json`。
- 原始快照和上游 README 保留于 research，仅作为出处与研究证据，不是运行时依赖。

本项目从快照提取卦名和爻值，生成 `data/hexagrams.json`；将上游由上至下的 7/8 转为本项目由下至上的 1/0，并推导上下卦。数据也打包进 `h5/data.js`。上游翻译为 AI 辅助翻译并经作者编辑，不是已经核对的中文经典资料。当前结构检查通过，文化解释仍待审核。

未引入该上游的应用代码、字体或 UI。前端使用系统字体与原生 Canvas，无运行时第三方库。原创项目代码的许可证由团队另行决定。
