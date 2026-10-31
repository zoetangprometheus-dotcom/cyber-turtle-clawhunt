# 赛博龟壳 · Cyber Turtle

Clawhunt 黑客松项目：摇一摇实体龟壳，得到一张纸签，再用手机扫描设备屏幕上的二维码，展开同一卦象的解读与问答。

**当前仓库是已完成主要交互的前端演示和后端协作起点，尚未接入真实 AI、扫码认证、设备或热敏打印。** 前端使用原生 HTML/CSS/JavaScript，无运行时第三方依赖。公开代码不等于已经部署了可扫码的线上服务。

后端 Agent 请先读 [后端接入 README](docs/BACKEND_AGENT.md)，所有协作者遵循 [AGENTS.md](AGENTS.md)。

## 本地运行

需要 Python 3；运行测试另需支持 `structuredClone` 的 Node.js（建议 18 或以上）。

```sh
git clone https://github.com/zoetangprometheus-dotcom/cyber-turtle-clawhunt.git
cd cyber-turtle-clawhunt
python3 -m http.server 4175 --bind 127.0.0.1 --directory h5
```

打开 <http://127.0.0.1:4175>，按 Ctrl+C 停止服务。此命令只开放本机；手机的 localhost 不是电脑地址。手机联调应使用稳定 HTTPS 地址。

不需要 API Key、npm install 或构建步骤。`file://` 仅适合快速看版式；历史保存依赖 localStorage 和 Web Locks，应在 localhost 或 HTTPS 中验证。不支持安全写入时页面会提示未保存。不同端口、域名、浏览器之间的历史互不共享。

## 已完成与待接入

| 模块 | 当前已有 | 仍需完成 |
|---|---|---|
| 纸签与网页 | 纸签短文、放大的卦象区域、网页长解读、58 mm 试排预览 | 确认纸宽、点阵、字体和真机打印协议 |
| 四主题 | 今日/自我、感情、事业/学业、友情；加载、失败、重试 | 服务端生成、任务恢复、幂等与限流 |
| 同卦问答 | 200 字输入、空白校验、连续多条问答、失败保留输入 | 当前为显式标注的模板；需会话认证和真实模型 |
| 本机历史 | localStorage、同签去重、只读回看、月历、多条记录 | 真实领取成功后按服务端 reading_id 保存 |
| 历史可靠性 | 多标签页写锁合并、损坏记录隔离、原数据保留、日历键盘焦点 | 目标手机及微信内置浏览器联调 |
| 保存分享 | 基础签/主题长图、PNG 下载入口、复制文字回退 | 手机相册/分享行为实测；问答暂不单独导图 |
| 状态界面 | 过期、已领取、会话结束、无效链接、网络错误的演示状态 | 服务端业务状态驱动；上线移出演示控制台 |
| 64 卦 | 编号、上下卦和六爻结构，结构测试已通过 | 文化核对、中文卦意与备用内容审核 |

当前演示固定从乾卦样例开始，模拟新扫描只创建新的演示记录。页面不存在真实网络请求或 token 领取逻辑。本机历史不是账号系统或跨设备同步。

## 目录与修改入口

```text
h5/                         可直接运行的前端
  index.html                页面结构和固定文案
  style.css                 版式、动画、打印样式
  app.js                    演示流程、主题、问答、日历、导出
  history.js                存储校验、锁、合并和日期工具
  data.js                   生成文件，提交到仓库以便直接预览
data/
  content-examples.json     编辑样例的唯一源文件
  hexagrams.json            64 卦结构数据，文化含义未审核
  64卦核对表.csv             文化复核工作表
schemas/ai-output-schemas.json   模型文字输出约束
docs/BACKEND_AGENT.md        后端工作、接口草案、接入顺序和验收
docs/AI_CONTENT.md           提示词、字数、主题和内容边界
scripts/refresh-demo-data.py 数据打包脚本
tests/                      存储回归测试和数据检查
research/                   上游数据快照、许可与 SHA-256 记录
```

修改 `data/content-examples.json` 或 `data/hexagrams.json` 后执行：

```sh
python3 scripts/refresh-demo-data.py
```

不要单独编辑 `h5/data.js`，它由上述两个 JSON 生成。

## 检查

在仓库根目录执行：

```sh
node tests/history.test.cjs
python3 tests/check-data.py
node --check h5/app.js
node --check h5/history.js
```

前两项检查多标签页合并、坏数据保留、失败写入和 64 卦结构；不代表真实设备或模型验收。手动验收范围见后端 README。`tests/corruption-check.html` 仅供独立测试 origin 注入坏记录，勿在实际用户的存储环境使用。部署静态页面时发布 `h5/` 即可，不发布测试目录。

## 协作方式

- A：前端交互、视觉、纸签与内容规范；B：后端、模型服务、会话与设备固件；C：外壳和工业设计，协同确认屏幕/打印规格。
- 从最新 `main` 建 `feat/<topic>`、`fix/<topic>` 或 `docs/<topic>` 分支，经 Pull Request 合并。当前流程是团队约定，尚未配置分支保护。
- PR 说明问题、修改范围、验证结果和未完成项；接口变更同时更新接入文档和响应样例。
- 后端技术栈由 B 根据设备链路选择。先确定契约并完成一条真实闭环，不重做已完成的前端布局。
- 仓库所有者稍后邀请队友。公开可读不自动授予写入权限。

## 数据来源与许可

64 卦结构整理自 [jesshewitt/i-ching](https://github.com/jesshewitt/i-ching) 的 CC0 数据，来源与转换说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。保留上游快照不代表认可其文化解释。

本项目原创代码和内容的许可证尚未由团队选定；未在此次公开上传中额外授予开源许可证。第三方数据继续按其原有许可使用。
