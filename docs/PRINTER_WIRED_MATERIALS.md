# ESP32 独立有线打印材料

2026-10-31：使用者确认尚无 USB Host 模块及 GPIO 引出线，要求整理材料。现有 Mac USB 直连英文、中文和卦象样张已通过；以下是待采购、待实测的独立设备方案。

目标连接：微雪屏幕板 → SPI → USB Host 模块 → USB 打印线 → Xprinter 控制板 → 原机芯。

后续更新：使用者照片已确认拥有 GPIO 引出线，无需重复购买。当前先采用 [Mac USB 中转](PRINT_BRIDGE.md)，此方案不需要 Host 模块；以下采购项仅用于未来脱离电脑独立运行。

## 需要补齐

| 材料 | 数量 | 必须确认的规格 |
|---|---:|---|
| MAX3421E USB Host 模块 | 1 | USB-A 母口；引出 SCK/MOSI/MISO/CS/INT，必要时 RST；SPI 逻辑兼容 3.3V；有明确供电图及 USB VBUS 5V 方案；建议已焊排针的独立模块 |
| 微雪板配套 GPIO 引出线 | 1 | SH1.0、12P，对应 ESP32-S3-Touch-LCD-1.28；最好原厂配套或带针脚定义的 SH1.0 转杜邦线，先检查开发板包装内是否已有 |
| 杜邦线及小型转接板 | 1 套 | 配合模块排针和 GPIO 引出线，保证信号与 GND 连接可靠；转接头公母按实际模块确定 |
| 5V 稳压供电 | 1 套 | 给 ESP32 与 Host 模块供电，建议预留合计 2A；可复用合适的 USB 电源，具体分线按模块原理图确定 |
| 绝缘固定件 | 1 套 | 尼龙柱、绝缘垫或合适的固定支架；固定控制板、机芯和走纸通道，避免焊点接触金属 |

现有打印机 USB-B 数据线可复用；模块若选 USB-A 母口，应配 USB-A 转 USB-B 数据线。当前打印机原配 12V / 2.6A 电源继续独立供电，无需因本方案更换。

MAX3421E 是芯片方案，不代表任意同名板都可直接插上使用。不要将 M5Stack 叠层模块视为微雪板的插接配件；需选择可接线的模块并核对原理图。USB Hub、USB 转 TTL、CH340/CH343 下载器不提供此处所需的 USB Host 功能。

## 给卖家的确认文字

> 我要给 Waveshare ESP32-S3-Touch-LCD-1.28 接一台 USB Printer Class 7/1/2 的热敏打印机。请提供 MAX3421E USB Host 模块正反面、原理图和针脚定义。要求 SPI 信号为 3.3V 兼容，USB-A 口有 5V VBUS，并说明模块输入电压、是否需要分别提供 3.3V/5V，以及 CS、INT、RST 引脚。请提供已焊针版本。另需该微雪板配套 SH1.0 12P GPIO 引出线。

## 接线边界

- 官方资料确认板载 USB-C 经 CH343P 接 UART，用于烧录；现成 USB-C 转 USB-B 线不能将它变为打印主机。
- GPIO 接口引出 15、16、17、18、21、33，可用于另一路 SPI 及控制信号。最终分配需结合所选模块与库适配，不能套用开源示例普通 ESP32 的默认 GPIO19/23 等引脚。
- 5V USB VBUS、3.3V SPI 逻辑、打印机 12V 电源是不同用途；12V 不接 ESP32 或 Host 的低压引脚。不按导线颜色猜针脚。
- 不从 GPIO 给打印机供电。是否共用 5V 电源、从哪里取电、如何避免 USB/外部电源反灌，均按模块原理图确定后再接。
- 已核实打印端口为 USB-B。灰色钱箱形状接口和板上焊盘仍无 UART 定义，不做试接。

## 驱动路线与到货验收

参考 [print-pics](https://github.com/gdsports/print-pics) 的 ESP32 + MAX3421E + USB 热敏打印结构，使用 [USB Host Shield 2.0](https://github.com/felis/USB_Host_Shield_2.0) 和 [USBPrinter_uhs2](https://github.com/gdsports/USBPrinter_uhs2) 作为候选。后者 README 提及旧版依赖补丁，且例子并非本款 ESP32-S3 板，因此需核对版本、许可并做 SPI/板型适配，不宣称已经即插即用。

到货后顺序：核对供电/针脚 → Host 芯片连通 → 枚举 0483:070b 及 Bulk 端点 → 复用 TEST 002/003 → 屏幕与打印同时运行 → 缺纸、断线和重试 → 单次摇动只出一张签。打印状态查询目前超时，必须先解决实际完成/故障反馈，不能只靠固定延时宣告成功。

来源：[微雪接口与 SH1.0 说明](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28#interfaces)、[官方原理图](https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-1.28/ESP32-S3-Touch-LCD-1.28_Rev3.pdf)、[M5Stack 模块原理及兼容限制](https://docs.m5stack.com/en/module/Module_USB)。本清单没有下单或承诺某商家的模块已通过验证。
