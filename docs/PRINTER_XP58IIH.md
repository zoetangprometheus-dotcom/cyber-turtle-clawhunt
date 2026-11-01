# 打印部件变更：Xprinter XP-58IIH

更新日期：2026-10-31。当前替换原 GY-EP204X 方案。Mac 直接 USB 的英文、中文及卦象图形已获使用者实物验收；后续 [ESP32 经 Mac 中转打印](PRINT_BRIDGE.md)也已获自动起卦及人手摇动实物确认。尚未实现脱离电脑的 ESP32 独立打印，补齐材料见 [有线连接材料清单](PRINTER_WIRED_MATERIALS.md)。

**最新用户决策：ESP32 与打印机通过有线连接；手机仅扫描 ESP32 屏幕二维码查看网页。不采用手机控制打印，不再继续 BLE 排查。下方蓝牙数据与首轮结果仅保留为历史证据。**

## 已知与未知

- 包装：芯烨 Xprinter XP-58IIH，纸宽 58mm，USB＋蓝牙。用户确认这套部件来自标准票据热敏打印机。
- 补充照片确认黑盒是 AC/DC 电源适配器，型号 YC30-1202600，输出 12V DC / 2.6A。保留现有配套电源与连接，不沿用旧机型电源建议；该电压不得接入 ESP32 GPIO。
- 控制板保留 USB-B 母口（USB1）；旁边的灰色模块化插座用途不能仅凭形状判定，不当作网口或 TTL 接口。未确认任何可直接连 ESP32 的 UART 端子。
- 包装的 100–240V 是原整机电源输入；12V / 1A 是钱箱输出，均不能直接作为裸控制板供电依据。
- 用户提供完整自检纸，含英文、简体中文、二维码及 completed 结尾，并确认由当前拆机组件与 12V / 2.6A 电源组合打印。自检成功不等于 ESP32 通信成功。
- 自检显示 Interface=USB&BT、BT VERSION=V2.1+V4.0+B9、BT NAME=Printer001、BT MODE=6+7、BT BAUDRATE=921600、Resident Character 含 Simplified Chinese GB18030。设备地址和配对 PIN 不写入公开仓库。
- V2.1+V4.0 是双模可能性的线索，不足以证明 BLE 打印服务可用；须实际扫描 GATT 服务和写入特征。BT MODE=6+7 无已核实的厂商解释；921600 不直接用于配置 ESP32 外部 UART。
- 已验证 ESC/POS 初始化、GB18030 中文及 GS v 0 图形；384 点画布中的居中卦象正常，但完整有效打印点宽、打印完成状态、缺纸恢复与连续大图流控仍未验证。BLE 已取消。
- 原 GY-EP204X 的 9–24V、2.5A、TTL 115200、384 点及 GPIO16/17 方案不适用于新部件。已烧录固件继续禁用打印，本次未更改固件。

## 请用户补充，按优先顺序

已收到电源标签、自检页、控制板正反面和接口照片，无需重复拆机拍摄。

1. 自检对应组件、电源已获用户确认。无需再提供手机 App 信息或操作蓝牙。
2. USB 打印线、电脑枚举和直接 USB 打印已验证；当前电脑也承担自动打印中转。GPIO 引出线已由后续照片确认具备，独立设备连接仍缺 USB Host 模块。
3. 若已有厂商提供的控制板 UART 接口定义，请补充；照片中未识别到可确认用途和电平的 TX/RX/GND，暂不接 GPIO。

## 有线接入方案（待硬件及协议验证）

### Mac USB 只读检查（2026-10-31）

用户确认供电、灯亮并重新插拔后，I/O Registry 已枚举到 `USB Printer Port`，厂商字符串 `Printer`，VID:PID=`0483:070B`。接口 0：class=7、subclass=1、protocol=2、端点数量=2；按 [USB Printer Class 规范](https://www.usb.org/sites/default/files/usbprint11a021811.pdf) 为双向打印接口，标准采用 Bulk OUT 和 Bulk IN。具体端点地址/包长本轮未读出，不猜测为固定值。

本轮只读取硬件枚举和接口属性，没有新增打印队列、修改默认打印机或发送任何打印数据。Mac 能识别 USB 不等于 ESC/POS 命令或 ESP32 主机链路验收通过。后续 USB Host 方案应支持 Printer Class 7/1/2，并从实际描述符解析端点。

### Mac 实际打印验收（2026-10-31，后续轮次）

1. CUPS 原生 usb backend 报告 53 字节发送成功、退出码 0，但使用者确认没有出纸，因此该尝试未通过打印验收。
2. 使用者短按 FEED 能走纸，指示灯常亮。标准 USB GET_PORT_STATUS 和 ESC/POS DLE EOT 状态查询超时；不能由超时推断缺纸或正常，也不能将 USB ACK 当成机械打印完成。
3. PyUSB 1.3.1 + libusb-package 1.0.30.0 直接访问打印机，实测 configuration=1、interface=0、alternate=0、Printer Class 7/1/2；Bulk OUT=0x01、Bulk IN=0x81，两者 MaxPacketSize=64。
4. 直接发送 TEST 002 共 26 字节，使用者确认“已打印，文字正常”。该结果验证直接 Bulk OUT 传输；未查明 CUPS 首次不出纸的具体原因。
5. TEST 003 共 5855 字节，含 GB18030 中文、六条阳爻图、上下卦标识；使用者确认“中文和六条横线都正常”。使用 256 字节分块、块间 20ms；仅为当前短样张验证，不代表无限长度/高速打印已通过。
6. 没有发送切刀、钱箱或纸上二维码命令，未改默认打印机、未建系统打印队列。原始本机日志和样张保存在被忽略的 .local/esp32/，设备序列号不进入公开文档。

可复现脚本：`scripts/printer-usb.py`。复用 [PyUSB](https://github.com/pyusb/pyusb) 和 [libusb-package](https://pypi.org/project/libusb-package/)；ESC/POS 图形格式参考 [Epson GS v 0](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_lv_0.html)。该指令在 Epson 文档中标为旧指令，但已通过当前 Xprinter 实机测试。

```sh
# 使用项目 Python 环境；依赖只安装到项目内
PIP_CACHE_DIR="$PWD/.local/esp32/downloads/pip" .local/esp32/python/bin/python -m pip install pyusb==1.3.1 libusb-package==1.0.30.0
.local/esp32/python/bin/python scripts/printer-usb.py probe
.local/esp32/python/bin/python scripts/printer-usb.py chinese
# 上一步只生成样张；以下命令会真实打印一张
.local/esp32/python/bin/python scripts/printer-usb.py chinese --send
```

脚本只选择唯一的 0483:070b 打印机并从描述符解析输出端点；传输失败不自动重打，以免重复出签。打印样张不等于真实 AI 签文。

保留原控制板、驱动与机芯组合及 12V / 2.6A 电源；ESP32 独立低压供电。目标为：ESP32 起卦/显示 → 有线发送到打印控制板 → 打印 → ESP32 显示领取二维码 → 手机扫码。

- 官方板卡文档确认 Waveshare 的 USB-C 经 CH343P 转 UART，连接 GPIO43/44，用于烧录和日志；不能靠一条 USB-C 转 USB-B 线直接充当打印机 USB 主机。
- 当前已知的打印数据口是 USB-B。因此优先评估 ESP32 → SPI USB Host 控制模块 → USB-B 打印机；需确认模块的 3.3V 逻辑、5V VBUS、SPI 引脚和 Printer Class/实际端点兼容性，尚未选定采购型号或实现驱动。普通 USB 转 TTL 模块不能替代 USB Host。
- 已找到开源参考 [USB_Host_Shield_2.0](https://github.com/felis/USB_Host_Shield_2.0) 和 [gdsports/print-pics](https://github.com/gdsports/print-pics)，后者使用 ESP32、MAX3421E 和 USB 热敏打印机；属于候选技术参考，不代表此板卡/打印机组合已验证。
- 如果厂商确认打印控制板提供可用 UART，可以采用更简单的 UART 接线；电平、针脚和协议必须先核实。不能把调试焊盘当成打印串口。
- 已烧录的 BLE 探测命令只会被串口显式调用，日常不会自动运行。本次停止该方向，保留现有可用屏幕和摇动功能，不为改文档重复烧录。

板卡接口依据：[Waveshare Interfaces](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28#interfaces)。

来源：[Espressif ESP32-S3 蓝牙能力](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/ble/overview.html)明确仅支持 BLE，不支持 Classic Bluetooth。[芯烨 XP-58IIH 产品页](https://www.xprinter.net/product/596.html)搜索摘要列出 USB/USB＋蓝牙选配；本次正文访问超时，未据此确认具体蓝牙类型或板内电源。
