# 本机 AI 接口与纸签

2026-10-31：使用者选择 DeepSeek Flash，通过已有 OpenAI 兼容协议接入。AI 自动打印已启用，用户已确认第 14 卦「大有」真实纸签出纸正常、手机扫码内容一致。新增本机扫码服务复用此配置，网页长解读、事业主题与一条问答已由主控真实验证；它仍依赖 Mac 与临时隧道，不是稳定生产托管或 ESP32 独立打印。

当前配置：Base URL 为 `https://api.deepseek.com`，模型 ID 为 `deepseek-flash`，JSON 输出开启，API Key 已保存至本机私有配置，AI 打印已启用。更换 Key 可在配置窗口保存并重新测试。模型 ID 已按 [DeepSeek 官方文档](https://api-docs.deepseek.com/)核对；本机对官方地址的 `deepseek-flash` 请求显式发送 `thinking: {type: "disabled"}`，让短签文使用非思考模式，避免默认思考占用 1024 token 的短输出预算。

## 使用

1. 双击仓库根目录 `打开AI配置.command`，打开 `http://127.0.0.1:8767/`。
2. 填写服务商提供的 Base URL、模型 ID、API Key，勾选「启用 AI 纸签」，点击「保存配置」。Base URL 可带 `/v1`，也支持完整 `/chat/completions` 地址。
3. 选择测试卦象，点击「测试连接并预览」。此操作会调用一次所填服务商的模型，可能计费，但不打印。未保存的修改不会参与测试。
4. 使用新扫码链路时，先运行 `启动临时扫码服务.command`，确认公网地址后再启动 `启动电脑打印中转.command`，详见 [启动说明](WEB_LOCAL_SETUP.md)。摇动 ESP32 后先更新设备二维码，收到 ACK 才请求短签，通过校验后打印。AI 配置在每个新任务开始时读取，不需要刷机；公网服务配置需在桥接启动前就绪。
5. 关闭「启用 AI 纸签」并保存，可恢复原卦象演示票。生成失败不会悄悄改印演示票。

当前仅实现非流式 Chat Completions 协议：Bearer 认证，短签 `max_tokens=1024`、网页/主题/问答 `max_tokens=3072`，默认带 `response_format: json_object`。若服务商不支持 JSON 模式，可关闭后重新测试。该窗口不表示所有兼容服务商或所有推理模型均已验证；短签要求返回 `choices[0].message.content` 中的三字段 JSON，网页与问答按各自 schema 校验。接口超时 45 秒，不自动重试付费请求。重定向被拒绝，防止把 Key 转发给其他地址。

## 纸签内容

纸签采用纵向分区：品牌与签号 → 放大的六爻 → 上下卦 → 大字卦名 → 标题与短签文 →「今日一小步」→ 来源说明。正文仍为 title（4–12 字）、message（20–50 字）、action（8–25 字），经过字段、长度和控制字符校验；底部注明「AI 创作 仅供自我探索」。纸上不打印二维码或长事件编号，不增加运势分数或幸运数字。

`scripts/receipt_layout.py` 为配置窗口和打印机生成同一张 384 点宽的黑白图，按字体实际宽度换行，并尽量平衡各行长度；六爻宽 288 点。点阵使用 GS v 0 分成最多 120 行的小段发送，避免浏览器字体与打印机字库导致排版不一致。样张图见 [新版预览](receipt-layout-preview.png)，乾卦编辑样张高 1125 点（图形约 141mm，另有走纸留白），正文长度不同会改变纸签长度。

渲染复用本地已有 Pillow 11.3.0，字体来自这台 Mac 的 `/System/Library/Fonts/Supplemental/Songti.ttc` 和 `/System/Library/Fonts/STHeiti Medium.ttc`，不将系统字体文件复制到仓库。其他系统须先适配字体；Python 环境需有 Pillow。`/api/preview` 只排版，不调用模型或打印。

卦名和结构来自当前设备事件与 canonical 数据校验，不由模型决定。64 卦文化资料尚未审核，所以本机提示词限定为卦名启发的现代创作，不声称是古籍原文、传统定论或审核过的经典释义，不生成动爻、变卦或确定性预测。

打印前把短签固定保存在本机任务库；重复事件不会重新生成或打印。如果生成期间出现新卦/返回首页，旧内容仍记录，但标为 superseded，不打印。只保留最新待处理事件，避免快速摇动积累大量请求；正在进行的一次网络请求可能仍产生服务商费用。

窗口显示最近一签状态和已生成内容。`generation_failed` 表示没有打印；`usb_sent` 仅代表传输完成，仍需看实际纸张；`uncertain` 表示可能已部分打印，不自动重试。当前没有对失败旧签的手动重印入口，修复配置后再摇动是新事件、新卦。

## 密钥和本机边界

- 服务仅绑定 127.0.0.1，校验 Host、Origin 和随机请求令牌，不提供跨站 API。
- `.local/esp32/ai-config.json` 使用 0600 权限；保存时原子替换。不回显 Key、不记录原始接口错误、不写浏览器 localStorage，不向公开 H5 或固件写入密钥。
- 留空 Key 可以保留已有值；更改 Base URL 时必须重新填写 Key，防止把旧服务商密钥发往新地址。清除 Key 时应关闭 AI 打印。
- 本项目位于 iCloud 文件夹，因此本地配置可能随 iCloud 同步；0600 和 Git 忽略不能阻止文件同步。不要分享 `.local` 目录。
- 代码和配置模板可协作，实际配置、签文和日志均留在被忽略的 `.local` 内。

## 已接入的本机网页能力

屏幕新二维码经临时 HTTPS 指向一次性领取入口。短签生成后不可变，网页显示同一份 base，并在领取授权下生成长解读；主题和问答沿用同一 canonical 卦象与原签。模型 Key 只由服务端读取，二维码不包含密钥或完整签文。

领取 token 有效 10 分钟，新签撤销旧未领取入口；Cookie 会话有效 30 分钟。历史保存后可离开会话只读回看，但不能续问；不同临时域名、旧 Pages 和不同浏览器之间不共享历史。接口与显式重试规则见 [WEB_LOCAL_SETUP.md](WEB_LOCAL_SETUP.md) 和 [BACKEND_AGENT.md](BACKEND_AGENT.md)。`bringup-*` 继续作为设备事件去重键，网页使用独立 reading_id，不把设备事件编号当作凭据。

## 入口与验收

- 本轮用户确认「大有」真实纸签出纸正常、手机内容一致；主控验证真实网页长解读、事业主题和问答，刷新/回看后仍只有 web 1、deep 1、question 1 个任务，没有新增调用。完整范围与隧道短暂断连记录见 [本轮验收](WEB_LOCAL_SETUP.md#已验证与待验收)。
- 一次 action 超过 25 字时校验拒绝、未打印。提示词目标已收紧为 12–18 字，保留原 8–25 字硬限制，不截断或自动修复重试；讼卦真实复测为 title 4/message 48/action 12 字并通过校验。中转已重新载入等待新事件；短签失败须重新摇动，重复起卦稳定性尚未全覆盖。

- 2026-10-31 真实 DeepSeek 验证：经配置窗口 `/api/test` 对第 1 卦调用一次 `deepseek-flash`，约 1.4 秒返回三字段短签；通过内容长度校验和 384 × 1088 点阵渲染。仅生成预览，未发送打印任务。配置回读确认 `has_key=true`、`enabled=true`，配置文件权限 0600，中转进程仍运行。真实测试记录和预览留在被 Git 忽略的 `.local/esp32/deepseek-live-check.json`、`.local/esp32/deepseek-live-preview.png`，不记录密钥。

- `scripts/ai_client.py`：兼容接口、配置读写、提示词与输出校验。
- `scripts/ai-panel.py` / `ai-panel.html`：本机配置、真实连接测试、不打印的预览及最近任务。
- `scripts/receipt_layout.py`：纸签点阵排版、PNG 预览与 ESC/POS 编码。
- `scripts/print-bridge.py`：AI 生成、不可变文本与独立串口读取/打印工作线程，打印使用共用点阵排版。
- `tests/ai-print.test.py`：7 项本机模拟接口测试通过，覆盖请求格式、DeepSeek Flash 非思考模式与其他接口隔离、身份信息与重定向隔离、配置权限、窗口跨站保护、去重、不打印失败或过时结果；未使用真实 Key 调用服务商。
- `tests/print-bridge.test.py`：5 项测试通过，包含 64 卦打印点阵解码与预览逐像素一致、爻序正确、最长内容留白和原去重/失败保护。
- 浏览器验证：窗口正常显示；未配置密钥时连接测试明确失败，无付费调用。没有读取用户之后填写的密钥。
- 5994 字节编辑排版样张已发送，使用者确认「出纸正常，文字和排版都完整」。样张标注「排版样张 非 AI 生成」，不作为真实模型验收。
- 参考长签形式的新版：2026-10-31 已发送 54090 字节点阵样张，标注「编辑排版样张 非 AI 生成」；使用者确认「完整出纸，排版清楚」，新版实物排版验收通过，不作为真实模型调用验收。此前 5994 字节的验收只适用于旧版。本机窗口已验证加载 384 × 1125 预览图，自动打印服务已重启并等待新事件。

使用 Python 标准库 HTTP 服务与客户端，复用原项目 PyUSB/pySerial 和本机已有 Pillow。当前服务商按使用者选择配置为 DeepSeek；协议参考：[DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。排版参考 [Pillow ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) 与 [ESC/POS GS v 0](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_lv_0.html)。
