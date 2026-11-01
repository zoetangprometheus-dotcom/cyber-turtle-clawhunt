# 后端 Agent README

状态日期：2026-10-31。本机 HTTP/SQLite 服务已实现并通过 12 项模拟测试，临时 HTTPS 与设备桥接已接通；本页接口表为当前本机实现契约。用户确认大有卦出纸和手机内容一致，主控已验证真实长解读、事业主题、问答及刷新回看。启动、限流、费用和有限验收范围见 [WEB_LOCAL_SETUP.md](WEB_LOCAL_SETUP.md)，临时隧道不等于稳定生产服务。

新增硬件联调起点：`firmware/cyber_turtle/`，支持 Waveshare ESP32-S3-Touch-LCD-1.28。详见 [固件与接线说明](ESP32_BRINGUP.md) 和 [实际验收记录](ESP32_ACCEPTANCE.md)。当前设备支持静态 Logo、随机上下卦及同屏显示。0.3.0 公共同卦演示 QR 已烧录、H5 已在 GitHub Pages 上线，不包含 Wi-Fi/HTTP、真实打印或认证领取；后端与硬件下一步从文档中的接入位置继续。

## 先理解产品闭环

Mac USB 直连英文、中文与卦象样张已由使用者确认通过；ESP32 独立打印仍待 USB Host 部件及驱动接入。本轮以 Mac 服务完成临时闭环，后续与队友后端对接时应保留现有字段、不可变记录与鉴权边界，见 [INTEGRATION_NEXT.md](INTEGRATION_NEXT.md)。

临时 [Mac 打印中转](PRINT_BRIDGE.md)复用现有串口 EVENT/STATE，无需刷机。新事件创建 reading_id 和一次性 token，写入 qrurl 并收到 ACK 后生成短签、固定内容和打印；同一短签供网页使用。固件仍按既有时序显示 QR，USB 发送完成不是出纸检测，打印状态反馈仍待落实。

模型配置沿用 [本机 AI 纸签配置](AI_LOCAL_SETUP.md)。DeepSeek Flash 已完成真实短签和本轮网页调用；`generate_extension(hexagram, base, theme=None, question=None)` 生成长文或回答，沿用不可变短签，不把 Key 写到 H5。关闭 AI 或生成失败时不以模板冒充真实结果。

用户摇动实体龟壳 → 设备依次揭示上卦、下卦 → 服务端锁定本次卦象和短签 → 热敏打印 → 设备屏幕显示 QR → 手机领取这张签 → 查看网页长解读 → 选择主题或提出问题 → 同一浏览器保存历史并按日历回看。

后端不接管前端视觉重设计，复用已有主题、问答、状态页、历史和导出组件。`scripts/web_service.py` 提供同源 HTTP/SQLite 服务，`h5/live.js` 处理领取、恢复和任务响应；旧 gh-pages 部署仍是静态演示，与临时服务的数据和浏览器历史隔离。

## 前端已完成什么

详见根 README 的功能表。主要模块：

| 文件/函数 | 当前职责 | 协作约束 |
|---|---|---|
| live.js、app.js 启动末尾 | 领取/恢复服务端记录，成功后保存；独立历史入口只读本机数据 | 失败不创建真实历史，不保存 token，不自动创建样例 |
| app.js / generate | 主题任务、加载、失败、显式重试 | 核对 reading_id、task_id 和 theme 后保存 |
| app.js / #ask.onclick | 200 字输入、问题任务、失败保留输入 | 保留 request_id 重试，不为断线恢复创建新问题键 |
| app.js / notices | 服务端业务状态 | 按 code 处理，真实入口不显示演示控制台 |
| app.js / renderReading、renderQuestions、revealResult | 纯文本渲染、只读历史和结果切换 | 映射服务端字段及来源标签；不执行模型 HTML |
| app.js / exportCard、纸签预览 | Canvas 长图和浏览器打印 | 来源标记随真实数据变化；热敏打印另走设备协议 |
| history.js | 校验、写锁、记录合并、隔离坏记录 | 继续复用；新增字段/版本应有兼容方案 |

`renderQuestions`、`revealResult`、`exportCard`、日历列表和纸签页应统一按可信 `content_origin` 渲染，保留旧历史的来源区别。`h5/data.js` 是演示打包文件，不是服务端可信数据或鉴权依据。

## 当前实现与后续工作

设备演示入口为 `#d=<hexagram_id>.<16位小写十六进制启动号>.<事件计数>`，来源为 `device_demo`，只展示卦象与联调说明，不生成签文、不开放模板问答。标识非服务端凭据；记录 ID 为 `device-启动号-事件计数`，跨重扫保留首次日期。不要沿用此公开链接格式实现受保护签文访问。部署及版本状态见 [设备扫码联调说明](DEVICE_SCAN.md)。

1. **设备与签文记录**：桥接校验设备事件与 canonical 卦象，Store 按事件幂等创建稳定 reading_id，第一份短签不可覆盖。后续独立设备身份和打印状态反馈仍需设计。
2. **扫码与会话**：10 分钟 token 原子领取、30 分钟 Cookie 会话及归属校验已实现。新签撤销旧未领取 token，不修改已领取记录；以当前实现替代原 180 秒 QR 建议。
3. **模型服务**：服务端保管 Key，短签、网页长解读、主题和问答按 schema 校验；当前属于卦名启发的现代创作，64 卦文化内容仍未审核。真实事业主题与一条问题通过，不等于全主题/全卦覆盖。
4. **任务与故障恢复**：持久化状态、主题/问题幂等、两 worker/四 pending 上限已实现。失败与进程重启不自动重试；每次显式重试可能产生新费用。
5. **部署与设备联调**：同源临时 HTTPS 已接通并完成有限手机/纸签验收。稳定域名、长期可用性、更多手机及独立打印仍待后续，不将临时隧道描述为生产托管。

## 当前本机接口

同源 H5 + API，HttpOnly Cookie 保存会话，SameSite=Strict，公网 Secure。POST 校验 Origin 与允许的 Host，不提供 CORS。前端不持有模型 Key 或设备凭据。

| 操作 | 路由/方法 | 状态 |
|---|---|---|
| 扫码入口 | `GET /r/{token}/` | 仅加载页面；实际领取通过 POST |
| 领取 | `POST /api/claim`，`{token}` | 设置 Cookie，返回 reading_id/status/record?/error? |
| 刷新恢复 | `GET /api/readings/{id}` | 签文状态 pending/ready/failed；ready 返回完整 record |
| 网页长文重试 | `POST /api/readings/{id}/retry`，`{}` | 显式重试失败长文；不能重生成失败的基础短签 |
| 开始主题深解 | `POST /api/readings/{id}/deep-reading`，`{theme}` | 按 reading_id + theme 幂等；失败后显式重发才重试 |
| 查询任务 | `GET /api/readings/{id}/tasks/{task_id}` | 检查会话和任务归属，返回已有状态/内容 |
| 问卦 | `POST /api/readings/{id}/questions`，`{request_id,question,theme?}` | UUID 请求键；每签最多八问，同键内容冲突返回 409 |
| 导出与历史 | 客户端 Canvas / localStorage | 不需要服务端分享或历史同步接口 |

task 状态为 pending/succeeded/failed；运行中也记为 pending。响应包含 reading_id/task_id/status，成功时含 content，失败时含 error，并带适用的 theme/question_id。同键同内容返回原任务，成功内容不可改写；同问题键不同文字或主题才返回 `409 invalid`。

错误 envelope 为 `{error,code}`：401 session；403 claimed 或 session；404 invalid；410 expired；429 busy；503 network；输入格式错误为 400 invalid，业务输入冲突为 409 invalid。前端按 code 处理，不解析错误文案猜状态。更完整契约见 [WEB_LOCAL_SETUP.md](WEB_LOCAL_SETUP.md#接口与任务)。

轮询可从 1 秒逐步退避到 5 秒；总时限根据服务端模型预算确定。前端超时不代表服务端任务已取消。切签、切主题或离页时中止请求/忽略过期响应，每次比对 reading_id、task_id、theme/question_id。

### 成功领取/恢复的数据映射

领取/恢复 envelope 为 `{reading_id,status,record?,error?}`，record 直接使用下表右侧历史字段。模型只生成文字对象，ID、卦象、时间、权限及来源均由服务端绑定。

| 服务端字段 | 前端历史字段 | 要求 |
|---|---|---|
| reading_id | id | 稳定且不透明，同签重扫不新增记录 |
| record.hex | hex | hexagram_id、name_zh、upper_trigram、lower_trigram、lines_bottom_to_top；六爻由下至上 |
| record.base | base | title/message/action，与实际纸签一致，保存后不可改写 |
| record.web | web | title/meaning/reflection/action，完整网页解读；历史校验要求 title，界面分段展示后三项 |
| record.deep | deep | `{[theme]: content}`，四主题枚举见下文 |
| questions | questions | 每条 id/question/answer/created_at，answer 含 meaning/reflection/action |
| record.content_origin | content_origin | 当前服务固定 ai；不以 demo/demo_template 或未审核 fallback 冒充真实结果 |

会话有效性由服务器判断，不从浏览器历史推断，也不在 record 中保存 token 或 Cookie。

首次成功打开时前端记录 `scanned_at = new Date().toISOString()` 及当时本地日期 `day = YYYY-MM-DD`，后续合并保留首次值，避免跨时区回看日期漂移。现有校验要求时间为带毫秒的 UTC `toISOString()` 形式；服务端时间转换成该形式后保存。问答 created_at 也需满足此格式。

本地 envelope 为 `{version:1, active_id, records, quarantined}`，键名 `cyber-turtle-history-v1`。无效记录会隔离保存，不悄悄删除；不可解析的整个 envelope 禁止覆盖。`history.js` 合并保留原 base/web/hex、已完成主题结果，并按问题 ID 去重追加。因此服务端同一 ID 的完成内容必须稳定；若确需修订，应另定版本/迁移规则，不能期待覆盖现有快照。

不要把 token、Cookie、设备凭据写入 localStorage。失败、过期、已被其他人领取时不写受保护记录。只读本地历史在会话结束后仍可打开；重新提问必须有有效会话。无云同步或登录系统需求。

### 模型输出约束

使用 [schemas/ai-output-schemas.json](../schemas/ai-output-schemas.json) 的 `$defs`：

- `base_reading`：纸签 title/message/action。
- `deep_reading`：网页长解读与主题长解读 title/meaning/reflection/action。
- `question_input`：只校验 `{question}`，非完整包含 theme 的 HTTP body；theme 在 API 层单独枚举校验。
- `question_answer`：meaning/reflection/action，不包含任务 ID 或来源。

根 `oneOf` 只覆盖 base_reading/deep_reading，验证问答必须明确选取对应 `$defs`。主题为 today、romance、career、friendship。输入去除首尾空白后按 Unicode 字符数限制 1–200 字，禁止纯空白。

提示词与字数规范见 [AI_CONTENT.md](AI_CONTENT.md)，编辑样例见 [content-examples.json](../data/content-examples.json)。样例并非真实模型输出；`data/hexagrams.json` 的 meaning_modern 为 null、review_status 为未文化审核状态，不可直接当作已审核知识库。

## 推荐接入顺序与验收

### 第一步：契约与一个真实领取闭环

- 在 PR 中确定领取/恢复/任务查询路径、字段、错误码、TTL、幂等规则及后端运行方式。
- 从一条设备或模拟设备事件创建记录，输出可访问 QR。两个浏览器竞争同一 token 仅一个领取成功；首次领取的浏览器刷新可恢复。
- QR 失效、会话失效、已领取、无效入口各自命中已有状态页；失败路径不新增历史。
- 页面与纸签使用同一不可变 base_reading。服务端响应验证后才传给渲染/历史模块。

### 第二步：模型与持久任务

- 实际生成基础签和网页长文，再完成四主题及一个自由问题；记录实际模型、prompt 版本、校验结果，敏感输入勿上传公开仓库。
- 重复点击/刷新/网络断开后恢复同一任务，不重复生成；切换另一签后迟到结果不串签。
- 无效输出、超时、限流都可解释地失败或标为 fallback；不改原纸签，不将未完成任务当成已完成。

### 第三步：历史与真实设备

- 同签重扫仅一条记录，新签增加一条；问答刷新后保留；两个标签页同时新增问答均保留。
- 历史只读、按日历定位、坏记录隔离、存储被禁用时提示、日历键盘焦点均保持。
- 在实际手机/微信内置浏览器、稳定 HTTPS origin 上验证历史、下载和复制。更换域名/浏览器不会自动迁移历史。
- 确认纸宽、可打印宽度、点阵/字库、走纸和重试；浏览器 `window.print()` 不代表热敏链路通过。
- 正式入口去掉演示控制台、固定乾卦和模板自动创建逻辑，使用真实来源标签；需要演示时保留独立演示入口。

上述列表是完整验收目标；本轮已完成的子集是大有卦用户确认出纸/扫码一致、主控浏览器真实长解读/事业主题/问答、刷新恢复与历史回看，详见 [本轮验收](WEB_LOCAL_SETUP.md#已验证与待验收)。其余主题、重复稳定性、更多手机及打印状态反馈未全覆盖。单板固件证据另见 [ESP32 验收记录](ESP32_ACCEPTANCE.md)。提交 PR 时区分模拟测试、真实模型调用、浏览器检查和用户实物反馈。
