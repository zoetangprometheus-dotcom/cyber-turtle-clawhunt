#!/bin/zsh
cd -- "${0:A:h}"
./.local/esp32/python/bin/python scripts/ai-panel.py --open
