#!/bin/zsh
cd -- "${0:A:h}"
./.local/esp32/python/bin/python scripts/print-bridge.py --stop
print '\n按回车关闭窗口'
read
