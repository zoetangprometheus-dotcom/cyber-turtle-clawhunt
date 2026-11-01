#pragma once
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEClient.h>

// Diagnostic only, using the installed Arduino-ESP32 BLE client API.
// No characteristic values, descriptors, subscriptions or print data are written.
// Restart after each probe releases all diagnostic state and restores the UI.
void probePrinterBle(String target) {
  target.toLowerCase();
  if (target.length() != 17) { Serial.println("BLE_INVALID_ADDRESS"); return; }
  for (unsigned i = 0; i < 17; ++i) {
    if ((i % 3 == 2) ? target[i] != ':' : !isxdigit(target[i])) {
      Serial.println("BLE_INVALID_ADDRESS"); return;
    }
  }
  Serial.println("BLE_PROBE scanning 8 seconds; UI paused; no print writes");
  BLEDevice::init("CyberTurtle-Probe");
  BLEScan *scan = BLEDevice::getScan();
  scan->setActiveScan(true);
  scan->setInterval(100);
  scan->setWindow(80);
  BLEScanResults results = scan->start(8, false);
  Serial.printf("BLE_SCAN_COUNT %d\n", results.getCount());
  bool found = false;
  for (int i = 0; i < results.getCount(); ++i) {
    BLEAdvertisedDevice device = results.getDevice(i);
    String address(device.getAddress().toString().c_str());
    String name(device.getName().c_str()); name.toLowerCase();
    bool exact = address == target;
    bool printerName = name.indexOf("print") >= 0 || name.startsWith("xp-");
    bool relatedAddress = address.substring(0, 15) == target.substring(0, 15);
    if (!exact && !printerName && !relatedAddress) continue;
    Serial.printf("BLE_CANDIDATE name=%s address=%s rssi=%d exact=%d\n",
      device.getName().c_str(), address.c_str(), device.getRSSI(), exact);
    if (!exact) continue; // Never connect to an unselected nearby device.
    found = true;
    BLEClient *client = BLEDevice::createClient();
    Serial.println("BLE_CONNECTING");
    if (!client->connect(&device)) { Serial.println("BLE_CONNECT_FAILED"); break; }
    Serial.println("BLE_CONNECTED");
    auto services = client->getServices();
    if (services) for (auto const &entry : *services) {
      Serial.printf("BLE_SERVICE %s\n", entry.first.c_str());
      auto characteristics = entry.second->getCharacteristics();
      if (characteristics) for (auto const &item : *characteristics) {
        auto c = item.second;
        Serial.printf("BLE_CHAR %s read=%d write=%d write_no_response=%d notify=%d indicate=%d\n",
          item.first.c_str(), c->canRead(), c->canWrite(), c->canWriteNoResponse(), c->canNotify(), c->canIndicate());
      }
    }
    client->disconnect();
    break;
  }
  if (!found) Serial.println("BLE_TARGET_NOT_SEEN; does not prove BLE unsupported");
  Serial.println("BLE_PROBE_DONE no print writes; restarting");
  Serial.flush(); delay(300); ESP.restart();
}
