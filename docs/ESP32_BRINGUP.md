# ESP32 硬件联调

当前已烧录版本：0.4.1-bringup，已配置公开 H5 地址并验证重启后保留。目标板为 Waveshare ESP32-S3-Touch-LCD-1.28（触摸版），16 MB Flash、2 MB PSRAM。0.4.1 按用户要求将整个显示画面旋转 180°，Logo、卦象、文字和二维码统一旋转。触摸只使用轻触/长按手势，不依赖坐标，无需改映射。保留 0.4.0 的 GPIO21 DFR0440 阶段短震及震后 500ms 摇动屏蔽，以及已验收的 balanced_v4 摇动参数。GPIO18 灯光逻辑已准备但关闭，等待独立供电和接线/位置确认，见 [反馈硬件连接](FEEDBACK_HARDWARE.md)。固件本身没有 Wi-Fi、AI 或打印驱动，现有 AI、扫码领取及打印由 Mac 中转提供。

## 操作

- USB 接电脑供电，待机只显示用户提供的黑底白色 Logo，保持静止；轻触开始，也可连续往返摇动约两三次，再停稳半秒。使用者已实测确认 0.3.3「拿放不触发，正常摇动能触发」；后续若改变装配方式再按实际手感校准。
- 流程：揭示上卦 → 揭示下卦 → 同屏显示双卦及编号 6 秒 → 二维码。揭示动画中不创建重复事件。
- 轻触在双卦和二维码之间切换；长按结果/二维码页返回 Logo，或直接再摇起新卦。二维码保持显示；回看双卦后 6 秒再次显示二维码。
- 必须先配置实际可访问的 HTTPS H5 地址；未配置时显示“网页待上线”，不显示假入口。同卦演示链接不含签文或凭据、不提供认证领取；网页仅保存公开卦象演示记录。二维码只在屏幕显示，纸签不印 QR。
- 触发后的屏幕保留白底、黑字、蓝色辅助和淡入淡出。每次开始时用 `esp_random()` 的 6 位选择 64 种上下卦组合之一，重复抽到同卦属于正常情况；同一流程中的卦象不再变化。这是本地联调随机逻辑，没有动爻/变卦或真实 AI 签文。H5 同步本次卦象，不套用固定乾卦签文，真实解读待服务接入。

卦象结构来自项目 `data/hexagrams.json`，`scripts/refresh-firmware-hexagrams.py` 校验全部 64 个组合及三爻映射后生成 `Hexagrams.h`，编译时自动更新。六爻按由下至上编码，上卦取高 3 位，下卦取低 3 位。

显示层将“兌、離”转为“兑、离”，确保八卦名适配现有 GB2312 字库。原始结构数据及串口字段保留原字形。组合卦以标准编号显示，避免“夬、姤、遯”等字库缺字；不改名或用其他字代替。

摇动使用 50Hz 三轴采样，低通追踪缓慢重力/姿态变化。剩余运动幅度须超过 0.35g 并持续至少 20ms；连续峰的方向夹角余弦须不大于 -0.5，峰间隔为 160–700ms。连续 4 峰（约两次往返）后，运动幅度回落到 0.12g 以下保持 400ms 才触发。未满 4 峰时静止 200ms 或峰间断开超过 700ms，就清空手势计数并保留重力基线；同方向冲击不继续累加。整个动作与停稳须在 4 秒窗口内完成，过慢或过长的摇动可能不触发。超过 150ms 的采样间断或非有限数会重置检测。串口 status 返回 shake_profile=balanced_v4；本轮实物手感已由使用者确认。

本轮查阅 [microbit-dal 的开源加速度手势实现](https://github.com/lancaster-university/microbit-dal/blob/master/source/drivers/MicroBitAccelerometer.cpp)，参考连续方向切换、避免零散动作长期累计的思路；本项目在现有三轴滤波检测器内实现，无新增依赖或复制第三方源码。

Logo 原图位于 `firmware/assets/cyber-turtle-logo.jpg`，生成后的 `Logo.h` 随代码保存，常规编译不需要图片工具。若替换原图，可在项目 Python 工具环境安装 `Pillow==11.3.0` 后运行 `scripts/refresh-firmware-logo.py`。脚本将完整原图按比例缩放为 232×78 RGB565 并居中，不拆字、拉伸或重画；待机渲染后不做周期性刷新。原图是宽横标，因此圆屏中的标志高度较小。

## 构建与烧录

需要 Python 3.9+、Arduino IDE 2（或 PATH 中的 arduino-cli）；Apple Silicon 还需要 Xcode Command Line Tools。工具链、依赖、构建缓存全部放在项目 `.local/esp32/`，不提交仓库。

在仓库根目录执行：

```sh
python3 scripts/firmware.py prepare
python3 scripts/firmware.py ports
python3 scripts/firmware.py build
python3 scripts/firmware.py upload --port <实际端口>
python3 scripts/firmware.py monitor --port <实际端口>
```

`upload` 会编译并覆盖指定板子的现有固件；必须显式指定端口。关闭 IDE 的串口监视器后再烧录。遇到下载中断，只删除报错的损坏压缩包再 prepare，不能绕过 SHA-256 校验。

使用官方推荐 ESP32 core 2.0.12 和官方示例内的 TFT_eSPI 2.5.34 配置 Setup207_GC9A01；直接绘图，不依赖 LVGL。脚本为 Apple Silicon 构建原生 ctags 并使用 Python esptool，处理旧工具的 x86 架构以及空格路径问题，不要求安装 Rosetta。下载版本与校验值见 `scripts/firmware.py`。

串口 115200 baud，每条命令以换行结束：

当前已部署地址：`https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/`。新设备烧录后执行 `qrurl https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/` 保存配置；现有已配置设备不必每次重写。源码不内置个人配置，NVS 保存的仅是公共基地址。

| 命令 | 作用 |
|---|---|
| status | 查看状态、IMU、触摸芯片通信和事件计数 |
| start / reset | 开始一次演示 / 回到首页 |
| reading | 查看最近一次起卦的编号、上下卦和六爻位图；尚未起卦时返回 READING_NONE |
| motion on / motion off | 开关加速度日志 |
| qr | 结果就绪后显示本次二维码并输出公共演示链接；未配置时返回 QR_NOT_CONFIGURED |
| qrurl <HTTPS base> | 保存 H5 基地址到本机 NVS；不含查询/片段/凭据，最长 110 bytes，须能编码入圆屏 QR。仅填写已核实的部署地址 |
| print | 返回 PRINT_BLOCKED，不发送 UART 数据 |
| bleprobe <设备地址> | 旧诊断入口，仅首页/结果页可执行；扫描 8 秒，仅连接指定地址并枚举 GATT 服务及特征属性，不写入打印数据，完成后自动重启 |

状态编号：0 Logo 待机，1 上卦，2 下卦，3 双卦结果，4 同卦演示 QR；原 qrtest 已移除。`touch=ok` 仅证明芯片寄存器可读，手势仍需人手验收。

BLE 探测使用已安装 Arduino-ESP32 2.0.12 的开源 BLE 客户端 API（该 core 的 `libraries/BLE/examples/BLE_client` 为参考），未新增第三方依赖。仅手动串口触发，探测时界面暂时不响应。扫描未发现设备不能判定它不支持 BLE；若底层连接无响应，可按开发板 RESET 恢复首页。地址仅作为本次命令输入，不存入固件源码。发现可写特征仍不等于打印协议已通过。

## 板载引脚

| 功能 | GPIO |
|---|---|
| GC9A01 LCD MOSI / SCLK / CS / DC / RST / BL | 11 / 10 / 9 / 8 / 14 / 2 |
| I2C SDA / SCL（触摸与 IMU 共用） | 6 / 7 |
| CST816S RST / IRQ | 13 / 5 |
| 打印串口预留 TX / RX | 16 / 17，当前未初始化 |

依据：[Waveshare 板卡文档](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28)、[官方 Arduino 示例说明](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28/Arduino)。不要套用无触摸版或其他屏幕型号的引脚。

## 打印机接线前必须确认

**2026-10-31 更新：用户已将打印部件更换为 Xprinter XP-58IIH 拆机组件，保留机芯及控制板，包装标注 58mm、USB＋蓝牙。以下 GY-EP204X 资料仅为历史，不再是当前接线方案；不得沿用其电压、波特率或 GPIO 接线。当前信息与待补材料见 [打印部件变更记录](PRINTER_XP58IIH.md)。**

### 旧方案，仅存档：GY-EP204X

用户设备为杰普维 GY-EP204X TTL Serial，目前未接线。已有 TDX-0901000 适配器输出 9V / 1A，低于打印机标注 9–24V / 2.5A 的供电要求，本轮不用于打印测试。建议 9V、至少 2.5A 的稳压电源，并核对接头尺寸与极性。ESP32 单独由电脑 USB 供电。

以下是**按端子名称的连接关系**，不是插头针脚顺序；需先核对实物标识，再断电接线：

| 打印机端 | 接到 |
|---|---|
| 电源 VH / V+ | 独立电源正极 |
| 电源 GND / V− | 独立电源负极 |
| TTL RX | ESP32 GPIO16（TX） |
| TTL TX | ESP32 GPIO17（RX） |
| TTL GND | ESP32 GND，共地 |

9–24V 不得接到 ESP32 GPIO、3.3V 或 VSYS。确认使用 TTL 接口，不能把 RS232 直接接到 GPIO；不按导线颜色猜针脚。接线和供电确认前，固件保持禁用打印。

[GY-EP204X 手册](https://dfimg.dfrobot.com/wiki/19355/DFR0503-EN_embedded-thermal-printer_datasheet_V1.0.pdf)给出的参考值为 TTL 3.3V、115200 8N1、57mm 纸、48mm/384 点有效打印宽度。机器有小票/标签两套指令，须核对自检页模式和波特率后再实现打印。浏览器纸签的 58mm 试排不能直接当作 384 点位图。

## 后端接入边界

遵循 [BACKEND_AGENT.md](BACKEND_AGENT.md)，不另造与前端冲突的接口。此版本只保留接入位置和契约建议，**尚未实现 HTTP 客户端**：

1. `startReading()` 是触摸/摇动统一入口；当前输出临时 `bringup-随机启动号-计数`，正式版本由 B 定义持久化幂等事件 ID 和认证，不能把临时日志 ID 当作跨重启去重方案。
2. `Hexagrams.h` 为结构数据，`reading` 指向本次已选卦象。真实接入时由 B 明确设备事件与服务端锁定方式，绑定 reading_id、hexagram（六爻由下至上）、base_reading、content_origin。纸签与 H5 必须使用同一不可变原签，打印失败不得重新起卦。
3. 当前 `Stage::Reading` 6 秒后进入 `Stage::Qr`，只表示同卦扫码演示，打印继续禁用。未来接入须增加独立打印状态、状态读取、超时与明确重试，只有确认本次打印成功才展示正式领取 QR。不能定时假装成功。
4. `drawQr()` 编码公共演示链接，不是认证入口。扫码标识使用两个 32 位启动随机值与事件计数，不作认证依据。正式版本由后端提供 HTTPS 领取 URL 与 expires_at，设备处理到期、撤销和网络错误；凭据不可提交仓库。
5. 正式起卦算法、设备认证/事件路由、Wi-Fi 配网、签文响应及打印模式仍待 B 与硬件联调确认。当前日志标记 `content_origin=demo_random`，不运行模型。

## 验证

主机逻辑测试：

```sh
mkdir -p .local/esp32/build
clang++ -std=c++11 tests/firmware-flow.test.cpp -o .local/esp32/build/flow-test
.local/esp32/build/flow-test
clang -c firmware/cyber_turtle/qrcodegen.c -o .local/esp32/build/qrcodegen.o
clang++ -std=c++11 tests/firmware-qr.test.cpp .local/esp32/build/qrcodegen.o -o .local/esp32/build/qr-test
.local/esp32/build/qr-test
```

覆盖状态顺序、双卦/QR 切换、忙碌去重、计时回绕、64 卦映射、链接格式与圆屏 QR 编码、噪声/慢转/短碰撞/持续偏移拒绝，以及往返摇动和总加速度不变的手腕摇动。真机烧录、串口和人手验收分开记录，见 [ESP32_ACCEPTANCE.md](ESP32_ACCEPTANCE.md)。
