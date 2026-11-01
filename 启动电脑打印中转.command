#!/bin/zsh
cd -- "${0:A:h}"
./.local/esp32/python/bin/python -u scripts/print-bridge.py --send
print '\n中转程序已退出，按回车关闭窗口'
read
