---
date: 2026-10-31
date-basis: user-request
updated: 2026-10-31
type: project
language: zh-CN
tags: [project, cyber-turtle, prototype]
ai-first: true
---
# A 角色整体框架 v0.1

## 给后续 Codex
用户要求先做好整体框架，个性化内容醒后再修，未回答的选择按推荐方案推进。本目录是可交互演示与交接材料，不是实际硬件、扫码认证或在线 AI 成品。依据上级目录 v3.1 PRD 及 A-前端与内容的 00–07 文件。

## 如何打开
直接双击 `h5/index.html` 用浏览器打开，无需安装依赖、配置模型 Key 或启动服务器。为兼容 file://，数据通过 `h5/data.js` 加载。

若需本机 HTTP 预览，在本目录运行：
```sh
python3 -m http.server 4175 --bind 127.0.0.1 --directory h5
```
浏览器打开 http://127.0.0.1:4175 。结束时 Ctrl+C；这不是公开部署。手机无法通过自己的 localhost 访问电脑，手机联调另行配置。

## 可操作内容
- 固定乾卦基础签与四主题编辑样例；主题选择、模拟加载、失败与重试。
- 基础签/深解卡 PNG 生成和预览、下载入口、复制文字及失败回退。
- 纸签预览，浏览器打印入口；58 mm 是试排参数，不是已确认硬件规格。
- 演示控制台：过期、已领取、会话结束、网络失败、无效链接等 UI 状态。
- 64 卦数据浏览，六爻由数据生成。

## 数据与编辑入口
| 要修改 | 文件 |
|---|---|
| 页面结构与固定文案 | h5/index.html |
| 色彩/字体/布局/动画 | h5/style.css |
| 流程、导出与演示逻辑 | h5/app.js |
| 演示文案 | h5/data.js 中 examples；上级 07-content-examples.json 为文案来源 |
| 64 卦字段 | data/hexagrams.json |
| 逐卦文化审查 | data/64卦核对表.csv |
| 后端联调 | 09-接口接入框架.md |
| 下一轮需要回答 | 08-推荐选择与第二轮问题.md |
| 检查结果和限制 | 10-验收与交接.md |

演示未接入后端，因此刷新会恢复本机保存的当前签文、已完成主题与问答；真实扫码授权和服务端任务恢复仍必须按接口契约接入 B 的服务端。实际开发时以服务端响应替换静态数据，不允许把 demo 控制台保留为线上授权机制。

## 开源来源
数据候选来自 https://github.com/jesshewitt/i-ching ，保留 research 内原文、CC0 授权及 SHA-256 快照。上游 value 为由上至下 7/8 编码，项目转换为由下至上 1/0；已用三爻组合及泰/否非对称样例检查。保留源繁体字形，中文解释未批量生成、未文化审核。

前端采用原生 HTML/CSS/JS 与 Canvas，无运行时第三方依赖。之前研究的 html-to-image 可作为未来复杂卡片导出的候选；当前简单文字和卦线用 Canvas 足够，因此未引入该依赖。未复制第三方 UI 或字体资产。

## 自检
```sh
python3 tests/check-data.py
node --check h5/app.js
```

修改上级 `07-content-examples.json` 或 `data/hexagrams.json` 后，在框架目录运行 `python3 scripts/refresh-demo-data.py` 同步演示数据；不要把同步后的 data.js 当独立内容真源。


## 第二轮已更新
见 [[11-第二轮确认与问卦历史规范]]。新增顶部签文日历、主题区问卦、浏览器历史保存；纸签变短，网页扩展。历史功能建议通过稳定 HTTP/HTTPS origin 测试；file:// 只作快速预览，不承诺持久化兼容性。

新增测试：`node tests/history.test.cjs`。


## 历史与日历修复
F01/F02/F03 已修复，见 [[13-三项前端修复验收]]。历史写入使用浏览器 Web Locks；不支持安全协调写入时会明确提示未保存，不静默退回可能覆盖记录的写法。更新后请刷新已打开的旧页面。
