# -*- coding: utf-8 -*-
import time
import statistics
import RPi.GPIO as GPIO


class HX711:
    """
    More robust HX711 driver for Raspberry Pi using RPi.GPIO.

    gain:
        128 -> channel A, gain 128
         64 -> channel A, gain 64
         32 -> channel B, gain 32
    """

    GAIN_PULSES = {
        128: 1,
         64: 3,
         32: 2,
    }

    def __init__(self, dout_pin: int, pd_sck_pin: int, gain: int = 128):
        if gain not in self.GAIN_PULSES:
            raise ValueError("gain must be one of 128, 64, 32")

        self.dout_pin = dout_pin
        self.pd_sck_pin = pd_sck_pin
        self.gain = gain

        self.offset = 0.0
        self.scale = 1.0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pd_sck_pin, GPIO.OUT)
        GPIO.setup(self.dout_pin, GPIO.IN)

        GPIO.output(self.pd_sck_pin, False)

        self._read_raw_once()
        self._discard_initial_reads(8)

    def _discard_initial_reads(self, n: int = 8):
        for _ in range(n):
            try:
                self._read_raw_once(timeout=1.0)
            except Exception:
                pass
            time.sleep(0.12)

    def is_ready(self) -> bool:
        return GPIO.input(self.dout_pin) == 0

    def wait_ready(self, timeout: float = 1.0):
        start = time.time()
        while not self.is_ready():
            if (time.time() - start) > timeout:
                raise TimeoutError("HX711 not ready")
            time.sleep(0.001)

    def _clock_high(self):
        GPIO.output(self.pd_sck_pin, True)

    def _clock_low(self):
        GPIO.output(self.pd_sck_pin, False)

    def _read_next_bit(self) -> int:
        self._clock_high()
        bit = GPIO.input(self.dout_pin)
        self._clock_low()
        return bit

    def _read_next_byte(self) -> int:
        value = 0
        for _ in range(8):
            value = (value << 1) | self._read_next_bit()
        return value

    def _read_raw_once(self, timeout: float = 1.0) -> int:
        self.wait_ready(timeout=timeout)

        data = 0
        for _ in range(3):
            data = (data << 8) | self._read_next_byte()

        for _ in range(self.GAIN_PULSES[self.gain]):
            self._clock_high()
            self._clock_low()

        if data & 0x800000:
            data -= 0x1000000

        return data

    def read_raw(self, times: int = 7, timeout: float = 1.0) -> int:
        if times <= 0:
            raise ValueError("times must be > 0")

        samples = []
        for _ in range(times):
            v = self._read_raw_once(timeout=timeout)
            samples.append(v)
            time.sleep(0.01)

        if len(samples) == 1:
            return samples[0]

        med = statistics.median(samples)
        filtered = [x for x in samples if abs(x - med) <= max(5000, abs(med) * 0.2)]

        if not filtered:
            filtered = [med]

        filtered.sort()
        if len(filtered) >= 5:
            filtered = filtered[1:-1]

        return int(round(sum(filtered) / len(filtered)))

    def read_average(self, times: int = 10, timeout: float = 1.0) -> float:
        if times <= 0:
            raise ValueError("times must be > 0")
        values = [self._read_raw_once(timeout=timeout) for _ in range(times)]
        return sum(values) / len(values)

    def read_median(self, times: int = 9, timeout: float = 1.0) -> float:
        if times <= 0:
            raise ValueError("times must be > 0")
        values = [self._read_raw_once(timeout=timeout) for _ in range(times)]
        return statistics.median(values)

    def tare(self, times: int = 15):
        self._discard_initial_reads(5)
        values = []
        for _ in range(times):
            values.append(self.read_raw(times=7))
            time.sleep(0.05)
        self.offset = sum(values) / len(values)

    def set_scale(self, scale: float):
        if scale == 0:
            raise ValueError("scale cannot be 0")
        self.scale = scale

    def get_value(self, times: int = 7) -> float:
        return self.read_raw(times=times) - self.offset

    def get_weight(self, times: int = 7) -> float:
        return self.get_value(times=times) / self.scale

    def power_down(self):
        self._clock_low()
        self._clock_high()
        time.sleep(0.0001)

    def power_up(self):
        self._clock_low()
        time.sleep(0.0001)

    def cleanup(self):
        GPIO.cleanup((self.dout_pin, self.pd_sck_pin))
