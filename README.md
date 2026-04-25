# Goobo Hardware Test Scripts

这个目录按硬件模块存放 Goobo 的独立测试脚本。每个子目录都可以单独进入后运行，不依赖统一的应用启动流程。

## 目录结构

- `bus_servo_test/`: 总线舵机测试，包含 ID 设置、角度读取、串口调试。
- `camera_test/`: 树莓派 CSI 相机拍照和录像测试。
- `audio_test/`: 麦克风录音和扬声器播放测试。
- `eye_matrix_test/`: 8x8 WS281x LED 点阵表情测试。
- `hx711_test/`: HX711 称重传感器驱动和读取测试。
- `weight_eye_matrix_test/`: HX711 重量阈值联动 8x8 LED 点阵。

## 相机测试

依赖系统命令 `rpicam-still`、`rpicam-vid`。录制 MP4 时还需要 `ffmpeg`。

```bash
cd /home/neurobo/test/goobo/camera_test
python3 camera_capture.py -o test.jpg
python3 camera_video.py -o test.mp4 -t 10
```

常用参数：

- `--width`、`--height`: 指定分辨率。
- `--framerate`: 指定录像帧率。
- `--bitrate`: 指定录像码率。
- `--keep-h264`: 保留中间 `.h264` 文件。

## 音频测试

依赖 Python 包 `sounddevice` 和 `numpy`。如果系统没有这些包，先安装：

```bash
python3 -m pip install sounddevice numpy
```

列出音频设备：

```bash
cd /home/neurobo/test/goobo/audio_test
python3 mic_record.py --list-devices
python3 speaker_play.py --list-devices
```

录音和播放：

```bash
python3 mic_record.py -o mic_test.wav -t 5
python3 speaker_play.py --wav mic_test.wav
python3 speaker_play.py --freq 440 -t 2
```

如果有多个音频设备，用 `--device` 指定设备 ID。

## LED 点阵测试

依赖 Python 包 `rpi_ws281x`。常见情况下需要 root 权限访问 PWM/GPIO。

```bash
cd /home/neurobo/test/goobo/eye_matrix_test
sudo python3 eye_matrix_8x8.py --state demo
sudo python3 eye_matrix_8x8.py --state happy --brightness 80
```

可用状态：

- `neutral`
- `happy`
- `sad`
- `sleepy`
- `surprised`
- `blink`
- `wink`
- `angry`
- `demo`

如果点阵方向不对，可以尝试 `--flip-x`、`--flip-y` 或 `--zigzag-off`。

## HX711 称重测试

依赖 Python 包 `RPi.GPIO`，默认接线：

- `DOUT`: BCM 5
- `SCK`: BCM 6

运行：

```bash
cd /home/neurobo/test/goobo/hx711_test
python3 test_hx711.py
```

启动后先保持秤为空，脚本会做 tare，然后持续打印 raw/value/weight。当前 `test_hx711.py` 里的 `scale` 是示例值，需要按实际砝码校准。

## 重量联动灯阵测试

这个脚本会读取 HX711 重量并控制 LED 点阵：

- 重量大于 `config.ini` 里的 `display.threshold` 时，灯阵全亮。
- 重量小于或等于阈值时，灯阵显示眼睛眨眼。

运行：

```bash
cd /home/neurobo/test/goobo/weight_eye_matrix_test
sudo python3 weight_eye_matrix.py
```

改阈值或硬件参数时，编辑：

```bash
/home/neurobo/test/goobo/weight_eye_matrix_test/config.ini
```

## 总线舵机测试

总线舵机脚本在 `bus_servo_test/`，详细命令见：

```bash
cd /home/neurobo/test/goobo/bus_servo_test
cat README.md
```

常用入口：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 scan --start 1 --end 20
python3 set_servo_ids.py --port /dev/ttyUSB0
python3 record_angles.py --port /dev/ttyUSB0
```

## 说明

这些脚本直接访问硬件设备，建议在树莓派本机运行。遇到串口、GPIO、PWM 或音频设备权限问题时，优先确认设备节点和当前用户权限。
