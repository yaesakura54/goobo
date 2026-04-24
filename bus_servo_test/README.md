# Bus Servo Test

这个目录是独立的总线舵机测试项目，不依赖 `uv`，也不依赖原来的 `ble2rk` 或 `lelamp_runtime` 运行流程。

目标只保留三类能力：

- 设置舵机 ID
- 读取并记录舵机角度
- 调试舵机串口、ID、状态和简单移动

## 依赖

系统里如果已经有 `pyserial`，可以直接运行。否则安装：

```bash
cd /home/neurobo/test/goobo/bus_servo_test
python3 -m pip install -r requirements.txt
```

如果当前用户没有串口权限，临时用 `sudo` 运行，或把用户加入 `dialout`：

```bash
sudo usermod -aG dialout $USER
```

加入用户组后需要重新登录。

## 查串口

常见 USB 转串口设备是 `/dev/ttyUSB0` 或 `/dev/ttyACM0`：

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

默认波特率是 `1000000`，如果你的舵机或转接板配置不同，用 `--baud` 指定。

## 调试舵机

扫描总线上的 ID：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 scan --start 1 --end 20
```

测试单个 ID 是否响应：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 ping --id 1
```

读取单个舵机状态：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 status --id 1
```

打开或关闭扭矩：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 torque --id 1 on
python3 debug_servo.py --port /dev/ttyUSB0 torque --id 1 off
```

发一个位置命令：

```bash
python3 debug_servo.py --port /dev/ttyUSB0 move --id 1 --degrees 180 --time-ms 1000 --enable-torque
```

## 设置舵机 ID

设置 ID 时，总线上必须只连接一个舵机。否则多个舵机会被写成同一个 ID。

默认顺序和 LeLamp 原工程保持一致：

- `wrist_pitch` -> `5`
- `wrist_roll` -> `4`
- `elbow_pitch` -> `3`
- `base_pitch` -> `2`
- `base_yaw` -> `1`

运行：

```bash
python3 set_servo_ids.py --port /dev/ttyUSB0
```

如果舵机当前不是默认 ID `1`：

```bash
python3 set_servo_ids.py --port /dev/ttyUSB0 --current-id 3
```

如果你确认总线上只接了一个舵机，也可以用广播方式写 ID：

```bash
python3 set_servo_ids.py --port /dev/ttyUSB0 --broadcast
```

自定义 ID 映射：

```bash
python3 set_servo_ids.py --port /dev/ttyUSB0 --motors base_yaw:1,base_pitch:2
```

## 记录角度

读取 1 到 5 号舵机的位置并打印：

```bash
python3 record_angles.py --port /dev/ttyUSB0
```

写入 CSV：

```bash
python3 record_angles.py --port /dev/ttyUSB0 --csv angles.csv
```

指定 ID、频率和时长：

```bash
python3 record_angles.py --port /dev/ttyUSB0 --ids 1,2,3 --hz 20 --duration 10 --csv angles.csv
```

## 说明

脚本使用 Feetech/ST 系列常见协议：

- 包头：`0xff 0xff`
- 指令：`PING/READ/WRITE`
- 位置寄存器：`Present_Position`
- 角度换算：`0..4095` 映射到 `0..360` 度

如果你的舵机型号不是 `STS3215` 或寄存器表不同，优先用 `debug_servo.py raw-read/raw-write` 验证寄存器地址。
