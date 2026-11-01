#!/bin/zsh
cd -- "${0:A:h}"
./.local/esp32/python/bin/python -u scripts/web-launch.py
print '\n按回车关闭此窗口，已启动的扫码服务仍会继续运行'
read
