#include "../firmware/cyber_turtle/QrLink.h"
#include "../firmware/cyber_turtle/qrcodegen.h"
#include <cassert>
#include <cstdio>

int main(int argc, char **argv) {
  const char *base = argc > 1 ? argv[1] : "https://zoetangprometheus-dotcom.github.io/cyber-turtle-clawhunt/";
  for (unsigned id = 1; id <= 64; ++id) {
    const std::string link = makeQrLink(base, id, UINT32_MAX, UINT32_MAX, UINT32_MAX);
    uint8_t scratch[qrcodegen_BUFFER_LEN_FOR_VERSION(7)], qr[qrcodegen_BUFFER_LEN_FOR_VERSION(7)];
    assert(!link.empty());
    assert(qrcodegen_encodeText(link.c_str(), scratch, qr, qrcodegen_Ecc_MEDIUM,
                               1, 7, qrcodegen_Mask_AUTO, true));
    int cells = qrcodegen_getSize(qr), scale = 160 / (cells + 8);
    assert(scale >= 3 && (cells + 8) * scale <= 160);
  }
  puts("PASS: 64 links encode at >=3px/module with four-module quiet zone");
}
