# 赛博龟壳 · Cyber Turtle

Clawhunt 黑客松项目：摇一摇实体龟壳，得到一张纸签，再用手机扫描设备屏幕上的二维码，展开同一卦象的解读与问答。

**本机扫码领取与 AI 网页链路已接通：用户确认第 14 卦「大有」纸签正常出纸、手机内容一致；真实网页长解读、事业主题、问答、刷新与历史回看已验证。** 后端 12 项模拟测试通过；当前依赖 Mac 与临时 HTTPS，隧道曾断连后自动恢复，重复稳定性仍待验证，ESP32 独立打印尚未实现。前端使用原生 HTML/CSS/JavaScript，无运行时第三方依赖。此前的 [GitHub Pages](https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/) 仍是静态演示，新服务启动与验收边界见 [本机扫码签文服务](docs/WEB_LOCAL_SETUP.md)。

打印测试见 [打印机记录](docs/PRINTER_XP58IIH.md)，独立连接需补齐的部件见 [材料清单](docs/PRINTER_WIRED_MATERIALS.md)。队友后端接口与后续联调顺序见 [接入交接](docs/INTEGRATION_NEXT.md)。

无需新增模块的 [Mac 打印中转](docs/PRINT_BRIDGE.md)继续复用现有 USB 连接。新扫码链路须先启动网页服务和隧道、写入公网地址，再启动 `启动电脑打印中转.command`；新事件更新屏幕二维码并收到 ACK 后才生成短签与打印。Mac 需持续运行，不代表 ESP32 已能独立打印。准确顺序以 [本轮启动说明](docs/WEB_LOCAL_SETUP.md)为准。

后端 Agent 请先读 [后端接入 README](docs/BACKEND_AGENT.md)，所有协作者遵循 [AGENTS.md](AGENTS.md)。

本机 AI 纸签提供 [配置窗口与说明](docs/AI_LOCAL_SETUP.md)：双击 `打开AI配置.command`，填写兼容接口地址、模型和 Key，保存并测试后，新起卦可生成短签打印。[新版长签](docs/receipt-layout-preview.png)采用大卦象、突出卦名与分区短文，预览和打印共用点阵图。新版编辑样张和本轮真实 AI 纸签均已获得出纸反馈。新网页服务复用不可变短签生成长解读，不重新抽卦或改写纸签；字段超限会失败、不打印，不自动截断或再次调用。

Waveshare ESP32-S3-Touch-LCD-1.28 的静态 Logo、触摸/摇动、随机上下卦与双卦同屏固件位于 `firmware/cyber_turtle/`。构建、烧录、接线和待接入边界见 [ESP32 联调说明](docs/ESP32_BRINGUP.md)，实际验收见 [验收记录](docs/ESP32_ACCEPTANCE.md)。0.3.0 [同卦扫码演示](docs/DEVICE_SCAN.md)已烧录，线上地址已存入设备并验证重启后保留；使用者已实机确认扫码成功、上下卦一致。固件本身的真实签文 API、认证领取和独立打印尚未接入；本机 AI 与打印由 Mac 中转处理。

## 项目文档归档

完整资料入口见 [归档索引](archive/README.md)：包含产品 PRD、A 角色资料、早期前端阶段稿，以及当前固件、AI、打印、扫码和展示文档的导航。历史资料与当前实现分开标注，原始文件附 SHA-256 清单。密钥、真实用户数据和本机依赖不在公开备份中。

## 本地运行

真实扫码链路先双击 `启动临时扫码服务.command`，再启动电脑打印中转；快捷入口已实测可复用现有服务与隧道。底层 `python3 scripts/web_service.py` 仅绑定 `127.0.0.1:8768`；Cloudflare 临时 HTTPS、配置与启动顺序见 [WEB_LOCAL_SETUP.md](docs/WEB_LOCAL_SETUP.md)。启动服务不会自动起卦或调用模型。

下列命令仅用于静态页面预览，不运行领取或生成 API：

需要 Python 3；运行测试另需支持 `structuredClone` 的 Node.js（建议 18 或以上）。

```sh
git clone https://github.com/zoetangprometheus-dotcom/cyber-turtle-clawhunt.git
cd cyber-turtle-clawhunt
python3 -m http.server 4175 --bind 127.0.0.1 --directory h5
```

打开 <http://127.0.0.1:4175>，按 Ctrl+C 停止服务。此命令只开放本机；手机的 localhost 不是电脑地址。手机联调应使用稳定 HTTPS 地址。

静态预览不需要 API Key、npm install 或构建步骤；真实生成由服务端读取本机 AI 配置。`file://` 仅适合快速看版式；历史保存依赖 localStorage 和 Web Locks，应在 localhost 或 HTTPS 中验证。不支持安全写入时页面会提示未保存。不同端口、域名、浏览器之间的历史互不共享。

## 已完成与待接入

| 模块 | 当前已有 | 仍需完成 |
|---|---|---|
| 纸签与网页 | 58 mm / 384 点宽纸签、放大的卦象、固定短文与网页长解读；实物出纸通过 | 更多内容长度与打印异常状态验收 |
| 四主题 | 服务端幂等任务、查询恢复、显式重试；事业主题真实生成通过 | 其余三主题与更多手机验收 |
| 同卦问答 | 会话鉴权、200 字输入、请求键幂等、每签最多八问；一条真实问答通过 | 更多输入与手机交互验收 |
| 本机历史 | 按 reading_id 保存，刷新/日历回看通过，独立历史入口无 API 请求 | 真实会话过期及更多手机验收 |
| 历史可靠性 | 多标签页写锁合并、损坏记录隔离、原数据保留、日历键盘焦点 | 目标手机及微信内置浏览器联调 |
| 保存分享 | 基础签/主题长图、PNG 下载入口、复制文字回退 | 手机相册/分享行为实测；问答暂不单独导图 |
| 状态界面 | 服务端过期、已领取、会话结束、无效入口与网络状态 | 目标手机和微信浏览器联调 |
| 64 卦 | 编号、上下卦和六爻结构，结构测试已通过 | 文化核对、中文卦意与备用内容审核 |

新服务入口为 `/r/<token>/`，10 分钟内只允许一个浏览器领取，Cookie 会话有效 30 分钟；新签撤销旧未领取入口。根路径只提示扫描二维码，不自动创建样例。保存后的本机历史在会话结束后仍可回看，但不能继续提问。旧 Pages 的 `#d=卦编号.启动标识.事件计数` 仍是公开同卦演示标识，不是认证凭据。Pages 与临时域名的历史隔离，本机历史不是账号系统或跨设备同步。

## 目录与修改入口

```text
h5/                         可直接运行的前端
  index.html                页面结构和固定文案
  style.css                 版式、动画、打印样式
  app.js                    领取流程、主题、问答、日历、导出
  history.js                存储校验、锁、合并和日期工具
  scan.js                   公共同卦演示入口校验与记录映射
  live.js                   同源 API、领取/恢复、任务及响应归属校验
  data.js                   生成文件，提交到仓库以便直接预览
data/
  content-examples.json     编辑样例的唯一源文件
  hexagrams.json            64 卦结构数据，文化含义未审核
  64卦核对表.csv             文化复核工作表
schemas/ai-output-schemas.json   模型文字输出约束
docs/BACKEND_AGENT.md        后端契约、协作与验收
docs/WEB_LOCAL_SETUP.md      本机扫码服务、临时 HTTPS 与启动顺序
docs/AI_CONTENT.md           提示词、字数、主题和内容边界
scripts/refresh-demo-data.py 数据打包脚本
scripts/web_service.py      本机 HTTP 服务、SQLite 领取和生成任务
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
node tests/scan.test.cjs
python3 tests/check-data.py
node --check h5/app.js
node --check h5/history.js
PYTHONDONTWRITEBYTECODE=1 python3 tests/web-service.test.py
```

这些检查覆盖历史存储、64 卦结构、领取竞争、鉴权和模拟生成任务；不代表真实设备或模型验收。手动验收范围见后端 README。`tests/corruption-check.html` 仅供独立测试 origin 注入坏记录，勿在实际用户的存储环境使用。单独发布 `h5/` 不会提供真实 API；配置、数据库、日志和测试目录不随公开页面发布。

## 协作方式

- A：前端交互、视觉、纸签与内容规范；B：后端、模型服务、会话与设备固件；C：外壳和工业设计，协同确认屏幕/打印规格。
- 从最新 `main` 建 `feat/<topic>`、`fix/<topic>` 或 `docs/<topic>` 分支，经 Pull Request 合并。当前流程是团队约定，尚未配置分支保护。
- PR 说明问题、修改范围、验证结果和未完成项；接口变更同时更新接入文档和响应样例。
- 后端技术栈由 B 根据设备链路选择。先确定契约并完成一条真实闭环，不重做已完成的前端布局。
- 仓库所有者稍后邀请队友。公开可读不自动授予写入权限。

## 数据来源与许可

64 卦结构整理自 [jesshewitt/i-ching](https://github.com/jesshewitt/i-ching) 的 CC0 数据，来源与转换说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。保留上游快照不代表认可其文化解释。

本项目原创代码和内容的许可证尚未由团队选定；未在此次公开上传中额外授予开源许可证。第三方数据继续按其原有许可使用。
