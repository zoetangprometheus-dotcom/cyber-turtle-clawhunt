#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string>

// Public demo identity only: never treat this URL or nonce as authentication.
inline bool validQrBase(const std::string &base) {
  if (base.size() < 9 || base.size() > 110 || base.compare(0, 8, "https://")) return false;
  const size_t end = base.find('/', 8);
  const std::string host = base.substr(8, end == std::string::npos ? end : end - 8);
  if (host.empty() || host.front() == '.' || host.back() == '.') return false;
  for (char c : host) if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
      (c >= '0' && c <= '9') || c == '.' || c == '-')) return false;
  for (unsigned char c : base) if (c <= 32 || c >= 127 || c == '?' || c == '#' || c == '@' || c == '\\') return false;
  return true;
}

inline std::string makeQrLink(const std::string &base, uint8_t id,
                             uint32_t high, uint32_t low, uint32_t event) {
  if (!validQrBase(base) || id < 1 || id > 64 || !event) return "";
  char fragment[48];
  snprintf(fragment, sizeof(fragment), "#d=%u.%08lx%08lx.%lu", unsigned(id),
           (unsigned long)high, (unsigned long)low, (unsigned long)event);
  return base + fragment;
}
