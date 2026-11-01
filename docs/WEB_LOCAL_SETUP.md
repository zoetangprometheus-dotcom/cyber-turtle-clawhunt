# 本机扫码签文服务

状态日期：2026-10-31。本次增加 Python 标准库 HTTP 服务、SQLite 领取与任务库，以及网页长解读、四主题和同卦问答接口。后端 12 项模拟测试已由主控复跑通过；用户已确认第 14 卦「大有」正常出纸、手机扫码内容一致。主控浏览器已验证真实长解读、事业主题、问答、刷新恢复和历史回看，具体范围见文末。

当前地址（2026-11-01 11:34 恢复后）为 [临时扫码入口](https://lighter-windsor-eventually-clips.trycloudflare.com)，公网健康检查返回 200，app.js、live.js、style.css 返回 200 且与本地源码一致。旧 missing-onion-lenses-participate、modems-hostel-addresses-old、turtle-parish-pop-organized 域名对应通道已失效。网页服务、桥接和 Cloudflare QUIC 隧道已重新接通；临时地址会随隧道重建改变，不是稳定生产部署。

## 启动顺序

在仓库根目录操作。通常双击 `启动临时扫码服务.command`（调用 `scripts/web-launch.py`），待返回公网地址后，再启动 `启动电脑打印中转.command`。快捷入口已由主控验证可复用正在运行的服务与隧道，不会因此重启它们。下面是手动启动与排查步骤。

Mac 需保持唤醒、联网；ESP32 与打印机继续分别通过 USB 连接 Mac。AI 配置沿用 [本机 AI 设置](AI_LOCAL_SETUP.md)，不在网页填写或保存模型 Key。

1. 先启动签文服务：

   ```sh
   python3 scripts/web_service.py
   ```

   默认只监听 `127.0.0.1:8768`，可用 `--port` 为隔离测试选择其他端口。新进程成功绑定后，将中断的 pending 任务标为 failed，不恢复付费调用。重复 import 或桥接创建 Store 不会改变任务状态。

2. 在另一个终端启动临时隧道并保留进程：

   ```sh
   cloudflared tunnel --url http://127.0.0.1:8768 --no-autoupdate --protocol quic
   ```

   从隧道输出取得本次 `https://….trycloudflare.com` 地址，把基地址写入被 Git 忽略的 `.local/esp32/web-public.json`，格式如下；文件权限设为 `0600`。不要写 `/r/…`、token、Cookie 或模型 Key：

   ```json
   {"base_url":"https://lighter-windsor-eventually-clips.trycloudflare.com"}
   ```

   服务每次请求重新读取允许的公网地址。更换域名后必须更新该文件；旧二维码和旧域名的浏览器历史不会自动迁移。

3. 确认服务健康后，再启动 `启动电脑打印中转.command`：

   ```sh
   curl -fsS http://127.0.0.1:8768/api/health
   ```

   正常响应为 `{"service":"cyber-turtle-web"}`。还应检查本次公网地址的同一路径。健康检查不生成签文、不打印、不调用模型。桥接启动时读取公网配置是否存在，需在配置准备好后启动；不要同时开启多个占用设备串口的程序。

`scripts/web-launch.py` 简化上述服务、隧道和地址写入。启动服务或隧道本身不会发送设备 `start`、补跑旧事件或触发付费生成；实际生成等待新设备事件或已授权的网页操作。

## 摇动、打印与领取

新设备事件到达双卦同屏阶段后，桥接创建稳定 reading_id 和一次性 token，将 `qrurl <公网基地址>/r/<token>/` 写入现有固件。收到 `QR_URL_SAVED` 后才排队生成短签与打印；二维码更新失败或超时不开始该次生成/打印。无需在本轮重新烧录，Logo、摇动检测和原页面切换时序保持。

短签生成成功后固定写入本机库，同一份 title/message/action 用于纸签和网页。手机领取成功且短签已就绪后，服务才生成网页长解读；主题和问答只延展这张签，不重新抽卦、不改写原纸签。屏幕 QR 仍按固件时序出现，USB 发送完成也不等于已检测到出纸，因此不能称为“确认打印成功才允许领取”。

- QR 从创建起有效 10 分钟，只允许第一个浏览器原子领取。新签撤销所有旧的未领取 token，不修改已经领取的记录。
- 同一浏览器可刷新恢复；其他浏览器领取同一 token 返回 `claimed`。扫码入口 GET 本身不领取，页面通过 POST 领取。
- HttpOnly Cookie 会话有效 30 分钟；公网启用 Secure，SameSite=Strict。签文 ID 不是访问凭据，读取和生成接口都必须校验 Cookie 与归属。
- 完整签文成功后才保存本机历史。会话结束后可回看已保存内容，不能再通过 API 续问；清除浏览器数据会移除本机历史。
- 历史限定同一浏览器、同一 origin。旧 GitHub Pages、不同临时域名及其他设备的历史互相隔离，没有账号或云同步。
- 根路径只提示扫描设备二维码并提供本机历史入口，不自动创建样例签。旧 [GitHub Pages](https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/) 仍是此前静态演示，不能作为新服务验收。

## 接口与任务

H5 与 API 同源，不配置 CORS。所有 POST 要求匹配当前 Host 的 Origin；只接受本机地址与当前允许的公网域名。静态服务仅提供明确列举的 H5 文件，不能访问配置、数据库、日志或项目目录。

| 操作 | 请求 | 返回与约束 |
|---|---|---|
| 领取 | `POST /api/claim`，`{token}` | `{reading_id,status,record?,error?}`；status 为 pending/ready/failed，并设置会话 Cookie |
| 恢复签文 | `GET /api/readings/{id}` | 同上；ready 时包含完整历史 record |
| 重试网页长文 | `POST /api/readings/{id}/retry`，`{}` | 仅显式重试失败长文；基础短签失败须重新摇动，不能借此重生成原签 |
| 主题长解读 | `POST /api/readings/{id}/deep-reading`，`{theme}` | 按 reading_id + theme 幂等；主题为 today/romance/career/friendship |
| 同卦提问 | `POST /api/readings/{id}/questions`，`{request_id,question,theme?}` | request_id 为 UUID；trim 后 1–200 字，每签最多 8 问 |
| 查询任务 | `GET /api/readings/{id}/tasks/{task_id}` | `{reading_id,task_id,status,content?,error?}`，并带适用的 theme/question_id |

任务状态为 pending/succeeded/failed，运行中的任务仍标记 pending。最多两个工作线程、四个未完成任务（含正在运行）；容量满返回 `429 busy`。成功内容不可覆盖。问题的同一 request_id 必须对应相同文字与主题，冲突返回 `409 invalid`；传输中断后继续查询原任务，不能为了“恢复”创建新键。

失败不会自动重新调用模型。用户明确重试主题或问题时，重发同一主题或同一 request_id；网页长文使用专门 retry 接口。服务重启把未完成任务标为 failed，也不自动重试。正在进行的网络请求即使浏览器离开，仍可能计费；失败后的手动重试是新的模型调用。

错误返回 `{error,code}`：`401 session` 会话失效，`403 claimed` 已被领取，其他越权为 `403 session`，`404 invalid` 无效入口/任务，`410 expired` 过期或撤销，`429 busy` 容量或问数限制，`503 network` 服务不可用。输入格式问题返回 `400 invalid`，请求键冲突等业务输入问题返回 `409 invalid`。前端按 code 处理，不解析错误文案猜状态。

## 本机数据与协作边界

`Store.create(event, hexagram)` 返回 `(reading_id, token)`，重复事件返回 None，不能重新发送二维码或改写原记录；`set_base(event, base)` 仅保存第一份短签，`fail(event, message)` 仅标记尚未有短签的失败。桥接通过这三个方法共享 `.local/esp32/web-readings.sqlite3`，不通过公网接受客户端提供的卦象或短签。

SQLite 文件权限为 `0600`，只存 token/session 的哈希；API 不返回 token，访问日志不记录 URL、Cookie、问题、签文或服务商原始错误。真实签文与问答仍在数据库中，数据库、配置、日志均不得提交仓库。本项目位于 iCloud 目录，Git 忽略与文件权限不能阻止 iCloud 同步。

修改协作时保持 `reading_id`、任务与主题归属，切签后的迟到响应不能写进另一张签。纯文本渲染模型内容，可信来源字段由服务器填写；不以固定样例填补失败。需要更换稳定域名、生产托管或独立设备后端时另行确定迁移契约，不把临时隧道当作这些能力已完成。

## 已验证与待验收

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/web-service.test.py
```

12 项测试通过：并发领取、所有权、token/会话过期、静态 allowlist、CSRF、公网地址重载与 Secure Cookie、不可变记录、主题/问题幂等、任务容量、失败不自动重试、数据库重开与日志脱敏。测试全部使用临时数据库和注入模型，未读取真实配置或调用服务商。

本轮实际验收由主控记录：

- 用户确认第 14 卦「大有」纸签出纸正常，手机扫码后内容一致；主控比对网页与已固定短签一致。
- 真实网页长解读、事业主题和一条问答成功；刷新恢复、日历回看通过。相同 reading_id 回看后任务仍为 web 1、deep 1、question 1，没有新增模型调用。
- 独立 `/history/` 回看不发起 API 请求；已保存本机历史，URL 移除领取 token，localStorage 无 API Key，所测浏览器视口无横向溢出。
- 64 卦新 URL 的二维码编码检查通过，模块至少 3 px；这不是全部 64 卦真实模型或手机实测。
- 一次短签 action 超过 25 字，校验拒绝且未打印。提示词目标已收紧为 12–18 字，仍保留原 8–25 字硬限制，不截断、不自动重试；讼卦真实复测得到 title 4/message 48/action 12 字，校验通过。遇到短签失败，检查配置后重新摇动，属于新事件而非原签重试。

尚待专项验收：其余三个主题的真实模型表现、新起卦的重复稳定性、30 分钟过期后的真实手机回看、目标微信浏览器与更多手机的历史保存/导出，以及打印缺纸与状态反馈。中转已重新载入等待新事件；不能将上述有限验收称为全部卦象、设备或长期可用性已验证。

## 2026-11-01 扫码网址恢复

- 用户能识别二维码，但网页打不开。本机 8768 健康接口正常；旧公网域名当时无法在本机解析，原 cloudflared 进程仍存活但不断报连接取消。保留本机服务和数据库，只停止已核对 PID/命令的故障隧道。
- 第一轮重建已连接边缘节点，但 60 秒内公网健康未通过而被启动器终止。后续公共 DNS 检查能解析该候选域名；第二轮连接重试至约 148 秒才注册成功，180 秒验证窗口内通过公网健康检查。
- `scripts/web-launch.py` 将新隧道验证窗口延长到 180 秒；候选域名仅写入一次以供服务端 Host 校验。启动失败、中断或清理等待超时时均恢复之前配置；不存在旧配置则移除候选。复用健康通道的行为保持。
- `PYTHONDONTWRITEBYTECODE=1 .local/esp32/python/bin/python tests/web-launch.test.py`：7 项模拟测试通过，含 75 秒后就绪、失败回退、进程退出、中断与清理超时。主控审查并修复了清理等待抛异常会跳过回退的问题。未触发真实模型或打印测试。
- 新公网 `/api/health`、`/app.js`、`/style.css`、`/live.js` 均返回 200，脚本和样式与当前文件逐字节一致。设备收到 `QR_URL_SAVED`，状态仍为已验收的 `0.3.3-bringup / balanced_v4`，中转已恢复等待新事件。
- 串口检查时设备已处于待机、没有当前事件。上一张签文仍保存在数据库，但其未领取 token 已过期；本轮没有更改其内容、续期凭据或补打。已请用户重新摇动后扫描新二维码，以完成手机验收。
- 这次恢复没有提供固定域名或后台自动修复。后续若进程存活但公网健康失败，启动器仍明确报错；应核对项目隧道再恢复，不能以 PID 存活判断服务可用。域名改变后，旧 origin 的浏览器本机历史不会自动迁移。
- 手机验收通过：使用者确认重新摇动并扫描新二维码后「能打开，卦象和内容正常」。对应第 42 卦「益」，上巽下震；只读检查显示基础签已固定、已领取、web 任务成功 1 个、deep 任务成功 2 个，无签文错误。本轮未由主控代领 token 或发起上述生成。
