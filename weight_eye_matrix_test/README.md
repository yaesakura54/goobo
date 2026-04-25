# Weight Eye Matrix Test

这个目录把 HX711 称重模块和 8x8 WS281x LED 点阵联动起来：

- `weight > threshold`: 灯阵全亮。
- `weight <= threshold`: 灯阵显示眼睛眨眼。

阈值和硬件参数都在 `config.ini`，改阈值不需要改 Python 代码。

## 依赖

复用相邻目录里的代码：

- `../hx711_test/hx711.py`
- `../eye_matrix_test/eye_matrix_8x8.py`

需要系统已经安装：

- `RPi.GPIO`
- `rpi_ws281x`

LED 点阵通常需要 root 权限访问 PWM/GPIO，建议用 `sudo` 运行。

## 配置

默认配置文件是 `config.ini`：

```ini
[display]
threshold = 90.0
eye_color = 255,0,0
eye_count = 2
```

常用配置：

- `hx711.dout_pin`: HX711 DOUT 的 BCM 引脚，默认 `5`。
- `hx711.sck_pin`: HX711 SCK 的 BCM 引脚，默认 `6`。
- `hx711.scale`: 称重比例，默认 `1000.0`，需要按实际砝码校准。
- `matrix.pin`: WS281x 信号引脚，默认 `12`。
- `matrix.brightness`: LED 亮度，范围 `0..255`。
- `display.threshold`: 重量阈值，默认 `90.0`。
- `display.full_color`: 全亮颜色，格式 `R,G,B`。
- `display.eye_color`: 眼睛颜色，格式 `R,G,B`，默认红色 `255,0,0`。
- `display.eye_count`: 眼睛数量，`1` 是 8x8 中央大眼睛，`2` 是左右两只小眼睛。
- `display.blink_fps`: 眨眼动画速度。

眼睛数量示例：

```ini
# 一只大眼睛
eye_count = 1

# 两只小眼睛
eye_count = 2
```

常用颜色示例：

```ini
# 红色
eye_color = 255,0,0

# 绿色
eye_color = 0,255,0

# 蓝色
eye_color = 0,0,255

# 白色
eye_color = 255,255,255

# 暖黄色
eye_color = 255,180,0
```

## 运行

```bash
cd /home/neurobo/test/goobo/weight_eye_matrix_test
sudo python3 weight_eye_matrix.py
```

使用其他配置文件：

```bash
sudo python3 weight_eye_matrix.py --config ./config.ini
```

启动后保持秤为空，脚本会先 tare，然后进入循环读取重量并控制灯阵。
