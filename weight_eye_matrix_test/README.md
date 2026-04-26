# Weight Eye Matrix Test

这个目录把 HX711 称重模块和 8x8 WS281x LED 点阵联动起来：

- `weight > threshold`: 灯阵全亮。
- `weight <= threshold`: 灯阵显示眼睛眨眼。
- `weight > threshold`: 舵机按顺序转到初始角度。
- `weight <= threshold`: 舵机按顺序转到目标角度。

阈值和硬件参数都在 `config.ini`，改阈值不需要改 Python 代码。

## 依赖

复用相邻目录里的代码：

- `../hx711_test/hx711.py`
- `../eye_matrix_test/eye_matrix_8x8.py`
- `../bus_servo_test/bus_servo.py`

需要系统已经安装：

- `RPi.GPIO`
- `rpi_ws281x`
- `pyserial`

LED 点阵通常需要 root 权限访问 PWM/GPIO，建议用 `sudo` 运行。

## 配置

默认配置文件是 `config.ini`：

```ini
[display]
threshold = 90.0
eye_color = 0,0,255
expression_id = 1

[servo_bus]
enabled = true
port = /dev/ttyACM0
baud = 1000000
move_time_ms = 2500
move_gap_seconds = 0.4
speed = 0
enable_torque = true
startup_position = initial
move_order = 1,2,3,4,5

[servo_positions]
1 = 90,75
2 = 80,90
3 = 100,80
4 = 90,50
5 = 10,0

[logging]
enabled = true
path = weight_eye_matrix.log
max_bytes = 1048576
```

常用配置：

- `hx711.dout_pin`: HX711 DOUT 的 BCM 引脚，默认 `5`。
- `hx711.sck_pin`: HX711 SCK 的 BCM 引脚，默认 `6`。
- `hx711.scale`: 称重比例，默认 `1000.0`，需要按实际砝码校准。
- `hx711.tare_times`: 启动时空秤归零的采样次数，默认 `5`。数值越小启动越快，数值越大归零越稳。
- `hx711.read_times`: 每次读取重量的采样次数，默认 `5`。数值越小响应越快，数值越大读数越稳。
- `matrix.pin`: WS281x 信号引脚，默认 `12`。
- `matrix.brightness`: LED 亮度，范围 `0..255`。
- `display.threshold`: 重量阈值，默认 `90.0`。
- `display.full_color`: 全亮颜色，格式 `R,G,B`。
- `display.eye_color`: 眼睛颜色，格式 `R,G,B`，默认蓝色 `0,0,255`。
- `display.expression_id`: 小于等于阈值时使用的表情编号。
- `display.blink_fps`: 眨眼动画速度。
- `servo_bus.enabled`: 是否启用舵机联动。
- `servo_bus.port`: 舵机串口，默认 `/dev/ttyACM0`。
- `servo_bus.baud`: 舵机串口波特率，默认 `1000000`。
- `servo_bus.move_time_ms`: 单个舵机移动到目标角度的时间，数值越大转得越慢。
- `servo_bus.move_gap_seconds`: 一个舵机发出移动命令后，到下一个舵机发命令前的等待时间。
- `servo_bus.speed`: 舵机速度参数，默认 `0`。
- `servo_bus.enable_torque`: 启动时是否给配置的舵机开启扭矩。
- `servo_bus.startup_position`: 服务启动时先移动到哪组角度，可选 `initial`、`target`、`none`。
- `servo_bus.move_order`: 舵机动作顺序，默认从 `1` 到 `5`。
- `servo_positions`: 每行格式是 `舵机ID = 初始角度,目标角度`。
- `logging.enabled`: 是否写入日志文件。
- `logging.path`: 日志文件路径。相对路径会按 `config.ini` 所在目录解析。
- `logging.max_bytes`: 日志文件大小上限。写入前如果达到上限，会清空旧内容再写入新日志。

`startup_position = initial` 只控制服务启动后的第一组舵机动作。程序进入称重循环后，仍然按重量状态切换：高于阈值用初始角度，低于或等于阈值用目标角度。

舵机角度示例：

```ini
[servo_positions]
1 = 90,75
2 = 80,90
3 = 100,80
4 = 90,50
5 = 10,0
```

舵机速度示例：

```ini
# 更慢
move_time_ms = 4000
move_gap_seconds = 0.6

# 等一个舵机基本转完再启动下一个
move_time_ms = 2500
move_gap_seconds = 2.7

# 更快
move_time_ms = 1500
move_gap_seconds = 0.2
```

表情编号：

- `1`: 从 `/home/neurobo/test/DEMO.ino` 提取的静态眼睛，使用原始 NeoPixel 编号 `12,13,14,52,53,54`，程序会按 `matrix.zigzag/flip_x/flip_y` 自动转换。
- `2`: 一只 8x8 中央大眼睛眨眼。
- `3`: 左右两只小眼睛眨眼。

表情配置示例：

```ini
# DEMO.ino 静态眼睛
expression_id = 1

# 一只大眼睛眨眼
expression_id = 2

# 两只小眼睛眨眼
expression_id = 3
```

启动速度示例：

```ini
# 启动更快，读数更灵敏
tare_times = 3
read_times = 3

# 启动更慢，读数更稳定
tare_times = 15
read_times = 9
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

日志示例：

```text
2026-04-26 14:23:10 event=start offset=-123.45 threshold=90.000
2026-04-26 14:23:20 state=low weight=70.120 threshold=90.000 action=expression_target_servos
2026-04-26 14:25:02 state=high weight=95.320 threshold=90.000 action=full_light_initial_servos
```

日志不会记录每一次读取到的重量，只会记录：

- 程序启动。
- 重量第一次进入高于阈值状态。
- 重量第一次进入低于或等于阈值状态。

查看日志：

```bash
tail -f /home/neurobo/test/goobo/weight_eye_matrix_test/weight_eye_matrix.log
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

## 开机自启动

Ubuntu 25 使用 systemd 管理开机服务。安装脚本会创建并启用：

```text
/etc/systemd/system/goobo-weight-eye-matrix.service
```

安装：

```bash
cd /home/neurobo/test/goobo/weight_eye_matrix_test
sudo ./install_autostart.sh
```

安装脚本会执行 `systemctl enable` 和 `systemctl start`。运行安装脚本前，先确认树莓派已经接好 HX711、LED 点阵和 `/dev/ttyACM0` 舵机总线。

查看状态和日志：

```bash
sudo systemctl status goobo-weight-eye-matrix.service
sudo journalctl -u goobo-weight-eye-matrix.service -f
```

停止服务：

```bash
sudo systemctl stop goobo-weight-eye-matrix.service
```

取消开机自启动：

```bash
sudo systemctl disable goobo-weight-eye-matrix.service
```

如果舵机串口不是 `/dev/ttyACM0`，先修改 `config.ini` 里的 `servo_bus.port`，再同步调整 `install_autostart.sh` 生成的 service 依赖。
