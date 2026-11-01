# 硬件联调验收记录

日期：2026-10-31。固件 0.1.0-bringup；开发板 Waveshare ESP32-S3-Touch-LCD-1.28。

## 本轮已实际执行

| 检查 | 结果 |
|---|---|
| `python3 scripts/firmware.py build` | 通过，程序 673081 bytes / 3145728，静态 RAM 20720 bytes / 327680 |
| `python3 scripts/firmware.py upload --port <已确认端口>` | 通过，bootloader、分区表、boot_app0、app 四段均写入并校验 hash，自动复位 |
| 启动串口 | `firmware=0.1.0-bringup`，Flash 16777216 bytes，PSRAM 约 2MB |
| 板载器件通信 | IMU 地址 0x6b，触摸 ID 0xb5，`imu=ok touch=ok` |
| 中文显示、轻触与摇动触发 | 使用者于 2026-10-31 实机确认：“中文显示正常，轻触和摇动都能触发” |
| 静止加速度采样 | 连续读数 norm 1.044–1.047g，未出现无读数或 NaN |
| 串口 start 连续两次 | 仅创建一次事件，第二次返回 `BUSY no duplicate event` |
| 真机状态推进 | STATE 1 → 2 → 3 → 4，即上卦、下卦、样例、打印阻塞 |
| 打印阻塞 | `print` 返回 `PRINT_BLOCKED ... no UART write`，未执行打印 |
| 内容同源 | `fixture` 返回现有 JSON 的“先走一小步”及原 message/action |
| 复位流程 | `reset` 回到 STATE 0，随后 `status` 正常，串口已关闭 |
| 主机 C++ 逻辑测试 | `clang++ -std=c++11 tests/firmware-flow.test.cpp ...` 执行通过 |
| Python 语法 / diff 空白检查 | 两个新增脚本 AST 解析、`git diff --check` 通过 |

构建产物位于 `.local/esp32/build/sketch/`，未提交仓库。没有写入 Wi-Fi、API Key 或设备认证信息；原前端文件未改。

本次应用二进制 `cyber_turtle.ino.bin` SHA-256：`53d301683fc4b898a2d83f1542642405314dcca500be91d3135fccb52b346e42`。重新编译的构建时间等元数据可能改变该值。

## 后续更新与待验收

### BLE 探测增补（2026-10-31）

- 用户确认 XP-58IIH 自检页由当前拆机组件搭配 12V / 2.6A 电源打印，且设备已开机准备联调。
- 增加 `BleProbe.h` 和串口 `bleprobe <address>`，使用 core 自带 BLE API，未增加依赖；只枚举服务和特征，不写入打印数据或订阅通知。
- 第一轮 8 秒扫描未发现自检页指定地址，输出 `BLE_TARGET_NOT_SEEN`；随后自动重启、`status` 正常，IMU/触摸通信仍正常。不能据此认定打印机不支持 BLE。
- 已补充扫描总数、打印机名称及相近地址候选日志，只会连接明确指定的地址。补充版本编译/烧录校验通过：程序 1289737 bytes，静态 RAM 44904 bytes；应用 SHA-256 `a4842a3543b29b7e86471de92cdd67a1039464890e943d2bea38707d6da4e331`。
- 用户随后明确采用 ESP32 与打印机有线连接，BLE 复测取消；当前没有已验证的 GATT 服务或打印链路。原始串口记录仅留在被忽略的 `.local/esp32/ble-probe.log`。

### 待机 Logo 更新（2026-10-31）

- 用户取消灯带任务并限定本轮只改 Logo；本轮未实现灯光、随机上下卦或打印连接。
- 新增 `firmware/assets/cyber-turtle-logo.jpg`、生成文件 `Logo.h` 及 `scripts/refresh-firmware-logo.py`；`cyber_turtle.ino` 仅改待机画面渲染。保留原图黑白、横向比例和完整画布，居中显示，原待机标题/提示/边框移除；触发后的页面与固定乾卦逻辑不变。
- 原图与用户附件 SHA-256 一致：`3eb27b1930d680686e80c46de48db87c72d734493b26da52915938bc1b5e0bcb`。232×78 RGB565 像素预览已检查，待机无周期刷新。图案为窄横标，不改成两行或拉伸。
- 实际编译通过：程序 1327465 bytes / 3145728，静态 RAM 44904 bytes / 327680；烧录四段 hash 校验通过。应用二进制 SHA-256：`f3f94a0661767eb70a3217b8af57b13cd694e967560c254d5e73f46a4496697c`。
- 真机串口启动正常，`imu=ok touch=ok`；串口触发得到 STATE 1→2→3→4，再 reset 回 STATE 0，串口已关闭。实际 LCD 上的 Logo 外观尚待用户目视确认，主机预览不能替代真机目视验收。

### 随机双卦与摇动改进（0.2.0-bringup，2026-10-31）

- 用户确认上一版 Logo 实屏显示正常；本轮保留 Logo，灯带与打印机不处理。
- 从项目既有 64 卦数据生成 `Hexagrams.h`；每次起卦选择一组上下卦并锁定到本轮结束，不添加动爻或变卦。揭示后同屏显示两个三爻图、简体卦名及组合卦编号，结果保持直到轻触返回或再摇起卦。
- 移除固件固定乾卦短签及相关生成脚本，避免向其他卦套用错误内容；H5 原有演示未改。八卦名按显示字库适配“兑/离”，原始数据不改。
- 摇动改为三轴动态加速度与方向反转检测，峰值门槛从旧版总加速度偏差 0.65g 改为动态分量 0.25g，稳定等待从 500ms 缩短为 200ms。3 峰门槛和忙碌去重保留，采样间断/异常值重置。
- `clang++ -std=c++11 tests/firmware-flow.test.cpp ...` 执行通过：覆盖结果保留、重复事件、时间回绕、64 卦映射、静止噪声、慢转、单次短碰撞、持续偏移、往返平移以及总加速度不变的手腕摇动。合成轨迹通过不等于人手验收。
- 真机串口得到 8 次抽样编号：32、49、33、1、30、10、49、12，上下卦及六爻与源数据一致；允许抽到重复卦。揭示中重复 start 返回 BUSY。等待超过旧版自动跳转时限后仍保持 STATE 3，reading 前后不变。记录位于忽略目录 `.local/esp32/random-acceptance.log`。
- 检查实际 U8g2 字库：最初数据含字库缺少的繁体/生僻字；改为八卦名简体、组合卦显示编号后，全部 49 个界面中文字符均有字形。未使用近似字替换生僻卦名。
- 最终固件编译、烧录 hash 校验和启动通过，程序 1329501 bytes，静态 RAM 44936 bytes。应用 SHA-256：`f40451e05832dac7ebf4af087ffc7ddcf4a597f8cd16b980da2c761af5033d9f`。
- 用户于 2026-10-31 实机确认：“摇动容易触发，双卦显示正常”。本轮摇动手感及双卦显示验收通过，保留当前 0.2.0-bringup 固件。
- 此前 45 秒串口监听内未收到 source=shake，不能作为该次用户实测的串口证据；人手验收依据为上述用户反馈。监听结束时 STATE 0、IMU/触摸正常，运动日志和串口已关闭；临时采样仅保存在 `.local/esp32/motion-verification.log`。

### 同卦扫码准备（0.3.0-bringup，2026-10-31）

- 新增 Flow 的双卦/QR 切换、QrLink.h 公共链接生成及 NVS 基地址配置；保留 Logo 和摇动阈值。
- H5 新增 scan.js 入口，随机卦与设备一致，重扫去重并可日历回看；设备入口不使用固定乾卦解读或模板问答。
- 固件构建通过：程序 1,334,697 bytes，静态 RAM 44,976 bytes。主机 flow/QR、前端 scan/history 与 JS 语法检查通过；本机浏览器验证同卦、重扫、新签、回看、无效链接通过。详见 [扫码联调说明](DEVICE_SCAN.md)。
- **未烧录此版、未公开部署、未用手机扫描实屏。** 当前设备仍为用户已验收的 0.2.0，待线上地址确定后继续。
- 打印机 USB 枚举检查通过，接口 7/1/2；未试打或修改打印队列。详见 [打印部件记录](PRINTER_XP58IIH.md)。

### 公开部署与扫码配置验收（0.3.0-bringup，2026-10-31）

- 使用者明确确认“公开部署并配置二维码”。静态 H5 已发布到 [GitHub Pages](https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/)，来源 gh-pages 根目录；提交 4f36ceda160fdc25c31e1d43302e40a2a7bf5139，Actions 运行 41186806609 成功，HTTPS 强制开启。
- 6 个线上 HTML/CSS/JS 文件均 HTTP 200，并与本地发布源逐字节一致。未上传日志、密钥、配置或问答数据，未覆盖 main。
- 0.3.0 编译及四段烧录 hash 校验通过，程序 1334697 bytes、静态 RAM 44976 bytes；应用 SHA-256：7cb4c71962550c519e5227feefd0c14bac49269554c85ca119937260ff7354f9。
- 线上地址写入 NVS，硬件复位后 BOOT 为 0.3.0、configured=yes、imu=ok、touch=ok；串口 1→2→3→4 通过，忙碌重复 start 被拒绝，同事件链接不变，新事件链接不同。串口关闭，设备留在二维码页供使用者扫描。
- 最后实测设备第 8 卦，上坎下坤，位图 16；打开设备实际 URL，线上显示“比”，上下卦一致；刷新后同设备记录仍只有 1 条、首次日期保持。
- 原始验收数据仅保存于被忽略的 .local/esp32/qr-acceptance.json 和 qr-acceptance.log。手机相机扫描实屏、人手切换仍待使用者确认；未执行打印。

### 手机实屏扫码验收（2026-10-31）

- 使用者确认：“扫码成功，上下卦一致”。设备实屏二维码 → 手机打开公开 H5 → 同一组上下卦显示的演示闭环验收通过。
- 此次反馈不扩展为不同手机/浏览器兼容性、扫描距离、触摸切换或真实 AI/打印验收。保持当前固件与线上版本，无需重复烧录。

### 尚未完成（部署后）

后续补充（2026-10-31）：已实现 Mac 串口 → USB 打印中转，未更改固件。首轮未走纸，恢复测试 005 后再测第 20 卦及人手摇动，使用者确认「本张和再次摇动均正常」。详细证据、启动方式和未解决的打印状态反馈见 [PRINT_BRIDGE.md](PRINT_BRIDGE.md)。当前是需要电脑的演示联动，不是 ESP32 脱机打印或真实 AI 闭环。

- 不同手机/浏览器、扫描距离与触摸切换未专项验收；当前手机扫码及同卦网页闭环已由使用者确认。
- 打印部件已更换为 Xprinter XP-58IIH 拆机组件（USB＋蓝牙）；供电、自检、Mac USB 枚举及电脑直连英文、中文、六爻图形样张已确认。ESP32 有线链路和打印状态反馈尚未验收。原 GY-EP204X 的供电与 TTL 方案作废，详见 [变更记录](PRINTER_XP58IIH.md)。
- Wi-Fi、真实服务端、AI、正式扫码领取、手机与纸签一致性的完整闭环。当前没有后端 API。

已收到新部件 12V / 2.6A 电源标签、完整自检页、控制板及 USB-B 接口照片，并获用户确认自检对应当前组件与电源。电脑通过 PyUSB 直写 Bulk OUT 端点的 TEST 002/003 已实物通过，系统 CUPS 路径曾报告发送成功但未出纸；状态查询仍超时，不代表打印完成。复现脚本为 scripts/printer-usb.py。使用者暂无 Host 模块和引出线，下一步按 [材料清单](PRINTER_WIRED_MATERIALS.md)补齐并联调；手机仅扫码。无需按旧方案购买 9V / 3A 电源。

### 降低摇动误触发（0.3.1-bringup，2026-10-31）

- 触发条件改为 0.40g、峰间至少 160ms、3 秒内 4 峰、停稳 350ms；保留三轴运动检测与触摸起卦、Logo、双卦、二维码流程。
- `clang++ -std=c++11 tests/firmware-flow.test.cpp` 编译运行通过：10 种运动场景中，主动往返平移和手腕旋转可触发；噪声、轻晃、拿放冲击、单次短摇和落桌回弹等不触发。流程、计时回绕及 64 卦映射检查通过。
- `python3 scripts/firmware.py build` 和 `upload --port /dev/cu.usbmodem5CF71301411` 成功；程序 1,334,713 bytes、静态 RAM 44,976 bytes，烧录 hash 校验通过。旧固件二进制备份保留于被忽略的 `.local/esp32/build/rollback-0.3.0-before-shake-tune/`。
- 实机串口读回：`firmware=0.3.1-bringup state=0 imu=ok touch=ok events=0 shake_profile=deliberate_v2`，证据在 `.local/esp32/shake-firmware-status.txt`。Mac 打印中转已恢复，等待新摇动或触摸；没有自动触发起卦或试打。
- 本次自动验证不等同于装壳后的实际手感验收。已请使用者验证轻拿轻放与主动往返摇两三下后的表现，尚待反馈。

### 拿放动作误触发修复（0.3.2-bringup，2026-10-31）

- 使用者反馈 0.3.1「还是太灵敏」，明确主要发生在拿起或放下。该版实际手感验收未通过。串口中最近事件来源为 `source=shake`，本次不调整触摸行为。
- 原因：旧版允许静止后的峰数在 3 秒内继续累加，且同方向冲击也能累计。用两组合成轨迹对比已保存的 0.3.1 与新版：零散同向碰撞、拿起停住再放下均从 1 次误触发降为 0；连续三次往返在两版均触发 1 次。证据保留在 `.local/esp32/shake-handling-regression.txt`。
- 新判据保留 0.40g，要求连续 6 个相反方向峰、单次持续至少 40ms、峰距 160–600ms。未完成的动作静止 200ms 即清空；完整动作停稳 500ms 后触发。操作改为连续往返约三次；总 3 秒窗口仍含最后停稳时间。
- `clang++ -std=c++11 tests/firmware-flow.test.cpp` 编译运行通过：16 种运动轨迹包含拿放、同向冲击、短暂反向冲击、分段摇动与三次连续平移/手腕旋转；成功手势与停稳实际跨过 uint32 计时回绕。流程与 64 卦映射检查通过。只读复核发现的回绕覆盖缺口已补充。
- `python3 scripts/firmware.py upload --port /dev/cu.usbmodem5CF71301411` 编译、烧录及 hash 校验通过；程序 1,334,841 bytes，静态 RAM 44,984 bytes。实机读回 `firmware=0.3.2-bringup state=0 imu=ok touch=ok events=0 shake_profile=continuous_v3`；证据在 `.local/esp32/shake-handling-upload.log` 和 `shake-handling-status.txt`。0.3.1 二进制和检测器留有回滚副本。
- 检查中发现前一次打印传输中断后中转已停止；本次未重打该旧任务。烧录后恢复中转，仅等待新事件，未主动触发起卦或打印。
- 已请使用者再试「握住外壳、避开屏幕，拿起停住再放下」和「连续往返约三次，停稳半秒」。实际手感尚待反馈；合成轨迹通过不等同于实物验收。

### 按手感反馈放宽主动摇动（0.3.3-bringup，2026-10-31）

- 使用者实测 0.3.2：「拿放不触发，但连续摇动也难触发」。防拿放部分获得确认，主动摇动门槛仍需调整。
- 保留相反方向与静止 200ms 清空未完成序列；改为 0.35g、持续 20ms、连续 4 峰、160–700ms 峰距、4 秒总窗口及 400ms 停稳。目标为自然连续往返两三下后停稳半秒。
- 19 种合成运动轨迹测试通过；新增较轻的 0.5g、600ms 周期平移与手腕旋转，以及两次往返成功场景。同方向 80ms 敲击、零散短冲击、拿起停住再放下、分段摇动仍不触发。成功手势包含计时回绕；流程和 64 卦映射检查仍通过。
- 编译、烧录与 hash 校验成功，程序 1,334,837 bytes、静态 RAM 44,984 bytes。实机读回 `firmware=0.3.3-bringup state=0 imu=ok touch=ok events=0 shake_profile=balanced_v4`。证据：`.local/esp32/shake-balanced-upload.log`、`shake-balanced-status.txt`。
- 0.3.2 实物测试期间，串口还出现设备重启和一条乱码 EVENT，导致中转校验拒绝并停止；原因未确认，本轮没有修改中转协议或补打旧任务。0.3.3 烧录后已重新启动中转等待新事件，通信稳定性与出纸不纳入本次摇动算法验收。
- 使用者随后确认 0.3.3：「拿放不触发，正常摇动能触发」。本轮拿放防误触与自然摇动实物手感验收通过，0.3.3 为当前已确认版本；该反馈不扩展为串口通信或打印稳定性验收。

### 灯光与震动软件准备（0.4.0-bringup，2026-11-01）

- 用户确认 DFR0440 尚未接线，5V / 60 颗灯带暂无独立电源。按官方板卡和模块资料，预留 GPIO21 控制震动、GPIO18 控制灯带。详见 [连接说明](FEEDBACK_HARDWARE.md)。
- 新增独立反馈逻辑及 RMT 输出适配；阶段短震、停止后 500ms 摇动屏蔽、八组灯光轮询与双卦锁定已编写。balanced_v4 摇动参数、Logo、扫码流程不变。
- 主控复核并运行反馈测试与现有 19 组摇动轨迹，全部通过。默认双输出关闭配置构建通过：程序 1,341,837 bytes，静态 RAM 50,784 bytes。软件通过不代表接线、震感或灯组位置已验收。
- **未烧录、未驱动输出、未重启中转。设备保留 0.3.3。** 旧固件二进制已备份到忽略目录 `.local/esp32/build/rollback-0.3.3-before-feedback/`。震动待接线确认；灯带等待独立 5V 电源、芯片确认和物理八卦位置校准。

### DFR0440 烧录与短震确认（0.4.0-bringup，2026-11-01）

- 使用者确认 S→GPIO21、VCC→VSYS、GND→GND 已接好，灯带未接。仅启用 VIBRATION_ENABLED，LIGHTS_ENABLED 保持 false。
- 启用震动的构建/烧录及四段 hash 校验通过：程序 1,341,925 bytes，静态 RAM 50,784 bytes；应用 SHA-256 bb1c6b94e37e0062851d58f9039726d7c86e1dc91487f6b6cdb700de5980c101。
- 真机 STATUS 确认 0.4.0、imu=ok、touch=ok、balanced_v4、QR configured=yes；FEEDBACK lights=disabled motor=enabled。
- 按用户要求先后发送两次独立 vibrate 测试，均返回 MOTOR_TEST 140ms，观察结束 state=0、events=0。用户确认第二次「能，短震后正常停止」。原始记录位于忽略目录 .local/esp32/feedback-motor-test.log。
- 用户随后完成上卦→下卦→双卦及静置测试，确认「短震正常，静置不会再次起卦」。当前接线状态下的单次驱动、阶段反馈与静置防误触验收通过；保留 0.4.0 和 balanced_v4 参数，不重复烧录或调整灵敏度。灯带供电及位置映射不属于本次通过范围。
- 原中转在本轮接线期间已退出；烧录后已恢复 READY mode=PRINT，等待新事件。未更改公网隧道、AI 配置或历史签文；未用串口 start 触发新签或打印。灯带仍未接、未验收。

### 屏幕整体旋转 180°（0.4.1-bringup，2026-11-01）

- 使用者要求将显示内容上下旋转 180°。复用已安装 TFT_eSPI 的 GC9A01 驱动，将 setRotation(0) 改为 setRotation(2)，并更新两个版本标识；仅三处固件行变更。Logo、卦象、文字、二维码一起旋转，触摸只处理手势、不依赖坐标，无需改映射。
- 当前已验收的 0.4.0 二进制先验证 SHA-256，再备份到忽略目录 .local/esp32/build/rollback-0.4.0-before-rotation/。上一打印任务结束后暂停中转，未中断正在发送的票据。
- 编译、四段烧录 hash 校验通过：程序 1,341,925 bytes，静态 RAM 50,784 bytes；应用 SHA-256 ab947924d30f75a49ab030714d25cf6819aeb87658e7feae0b303e01100efa20。未为此显示配置修改增加重复实现的单元测试。
- 真机 STATUS 确认 0.4.1、imu=ok、touch=ok、balanced_v4、QR configured=yes；FEEDBACK motor=enabled、lights=disabled。当前震动、摇动参数与 QR 配置均保留。证据位于忽略目录 .local/esp32/rotation-180-acceptance.json。
- 打印中转于 04:14 恢复 READY mode=PRINT，等待新起卦；未自动触发新签、模型调用或试打。用户确认「方向正确，轻触正常」，本轮屏幕旋转与轻触实物验收通过，保留 0.4.1 固件。
