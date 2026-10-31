# 后端 Agent README

状态日期：2026-10-31。本文以仓库现有前端为准，接口表是待 B 确认的契约草案，不是已上线 API。

## 先理解产品闭环

用户摇动实体龟壳 → 设备依次揭示上卦、下卦 → 服务端锁定本次卦象和短签 → 热敏打印 → 设备屏幕显示 QR → 手机领取这张签 → 查看网页长解读 → 选择主题或提出问题 → 同一浏览器保存历史并按日历回看。

后端不接管前端的视觉重设计。先复用已有主题、问答、状态页、历史和导出组件，把演示数据替换为授权响应。当前没有 backend 目录、服务端技术栈、部署配置、数据库或真实 API。

## 前端已完成什么

详见根 README 的功能表。主要模块：

| 文件/函数 | 已实现 | 接入时的改动 |
|---|---|---|
| app.js / makeRecord、启动末尾 | 固定乾卦演示记录；初次打开自动生成并保存 | 改为读取 URL 入口、领取/恢复服务端记录；失败时不创建真实历史 |
| app.js / generate | 四主题样例、加载与失败、缓存结果 | 提交任务、轮询恢复、校验响应归属后保存 |
| app.js / #ask.onclick | 200 字限制、模板问答、保留问题供重试 | 接入同卦问题 API，保持问答 ID 稳定及幂等 |
| app.js / scenario、notices | 错误状态与模拟控制 | 由明确业务 code 驱动；移出演示控制台后不能继续依赖 #scenario DOM |
| app.js / renderReading、renderQuestions、revealResult | 纯文本渲染、只读历史和结果切换 | 映射服务端字段及来源标签；不执行模型 HTML |
| app.js / exportCard、纸签预览 | Canvas 长图和浏览器打印 | 来源标记随真实数据变化；热敏打印另走设备协议 |
| history.js | 校验、写锁、记录合并、隔离坏记录 | 继续复用；新增字段/版本应有兼容方案 |

`renderQuestions`、`revealResult`、`exportCard`、日历列表和纸签页当前都有写死的“演示/编辑样例”标签。真实接入时统一按可信 `content_origin` 渲染；不能只改一个标签。`h5/data.js` 是演示打包文件，不是服务端可信数据或鉴权依据。

## B 需要完成的工作

1. **设备与签文记录**：确定起卦结果来源、设备身份、事件格式、重复事件去重；服务端校验上下卦与六爻方向。创建稳定 reading_id，锁定卦象、纸签、版本和时间。打印重试不能重新生成签文。
2. **扫码与会话**：创建高熵、有时效的入口 token；实现原子领取、刷新恢复和访问权限。QR 有效期与已领取会话有效期分开。新一签撤销旧未领取入口，不修改旧已领取记录。180 秒 QR、30 分钟会话是原方案参数，需联调确认。
3. **模型服务**：服务端保管 Key，生成短签、网页长解读、四主题与同卦问题回答；校验 JSON、长度、内容及来源。先跑通已审核的一个卦，再扩展 64 卦。
4. **任务与故障恢复**：持久化任务状态和结果；深解按 reading_id + theme 幂等；每次问答使用独立请求键，重试沿用该键，避免重复调用和收费。断线、刷新后能恢复原任务。
5. **部署与设备联调**：提供稳定 HTTPS 入口和可重现启动配置；确认路由回退、Cookie、同源或 CORS、限流、模型超时及脱敏日志；验证实体打印、屏幕 QR 和手机浏览器。

## 接口草案

优先同源 H5 + API。推荐由 HttpOnly/Secure Cookie 保存会话，并由 B 配套实现 SameSite/CSRF 策略。前端不持有模型 Key 或设备凭据。

| 操作 | 路由/方法 | 状态 |
|---|---|---|
| 扫码入口 | `GET /r/{token}` | 原方案此 GET 会领取；建议改为仅显示入口，显式 POST 原子领取，避免链接预取占用，须团队确认 |
| 领取与刷新恢复 | POST 领取路由、GET 会话/签文路由 | 具体路径与返回 envelope 待 B 提供，当前前端未实现 |
| 开始主题深解 | `POST /readings/{id}/deep-reading`，`{theme}` | 返回 task_id/status 或已有结果；幂等键规则待确认 |
| 查询主题任务 | `GET /readings/{id}/deep-reading` | theme/task_id 查询参数及终态待确认 |
| 问卦 | `POST /readings/{id}/questions`，`{question, theme?}` | 返回 question_id/task_id/status/answer；异步查询路径待确认 |
| 导出与历史 | 客户端 Canvas / localStorage | 不需要服务端分享或历史同步接口 |

建议 task 状态为 pending/running/succeeded/failed，失败响应包含稳定业务 code、可否重试和 request_id。409 如果表示任务已存在，应返回原 task_id 并查询，不盲目新建。

建议错误映射：401 会话结束；403 已领取或无权限（通过不同业务 code 区分）；404 无效入口；410 QR 过期或撤销；429 请求过频；503 服务暂不可用。HTTP 码及业务枚举由 B 最终确定并写入本文件，前端不解析错误文案猜状态。

轮询可从 1 秒逐步退避到 5 秒；总时限根据服务端模型预算确定。前端超时不代表服务端任务已取消。切签、切主题或离页时中止请求/忽略过期响应，每次比对 reading_id、task_id、theme/question_id。

### 成功领取/恢复的数据映射

返回字段至少包含下表，最终 envelope 由 B 明确。模型只生成文字对象，ID、卦象、时间、权限、版本及来源均由服务端绑定。

| 服务端字段 | 前端历史字段 | 要求 |
|---|---|---|
| reading_id | id | 稳定且不透明，同签重扫不新增记录 |
| hexagram | hex | hexagram_id、name_zh、upper_trigram、lower_trigram、lines_bottom_to_top；六爻由下至上 |
| base_reading | base | title/message/action，与实际纸签一致，保存后不可改写 |
| web_reading | web | title/meaning/reflection/action，完整网页解读；历史校验要求 title，界面分段展示后三项 |
| deep_readings | deep | 转换为 `{[theme]: content}`，四主题枚举见下文 |
| questions | questions | 每条 id/question/answer/created_at，answer 含 meaning/reflection/action |
| content_origin | content_origin | 服务端填写 ai/fallback；当前 demo/demo_template 不冒充真实来源 |
| session_expires_at | 不作为本机授权依据 | 会话授权始终由服务端判断 |

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

以上真实服务与设备验收目前均未执行。现有自动测试只覆盖前端存储与结构数据；根 README 列出命令。提交 PR 时报告实际执行项与仍待联调项，不把文档勾选当作测试证据。
