# -*- coding: utf-8 -*-
import time
from hx711 import HX711

DOUT_PIN = 5
SCK_PIN = 6

hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=SCK_PIN, gain=128)

try:
    print("Keep the scale empty, tare start...")
    hx.tare(times=20)
    print(f"offset = {hx.offset}")

    hx.set_scale(1000.0)

    while True:
        raw = hx.read_raw(times=9)
        value = raw - hx.offset
        weight = value / hx.scale

        print(f"raw={raw:10d}  value={value:10.2f}  weight={weight:8.3f}")
        time.sleep(0.3)

except KeyboardInterrupt:
    print("Exit")

finally:
    hx.cleanup()
