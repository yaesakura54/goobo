# 新树莓派部署指南

> 拿到一台已烧录系统、可 ssh 的 Pi，5 分钟跑起 codegen-runner。

## 操作步骤

### 1) 在 workshop 拿设备凭证

1. 浏览器打开 `<backend>/api/codegen/workshop`
2. 登录
3. 顶部 **`+ 添加设备`** → 输入设备名 → **创建**
4. 弹窗里复制 `device_id` 和 `device_secret`（**只显示一次**）

弹窗里也直接给出 bootstrap 命令模板。

### 2) 跑 bootstrap

`HARDWARE_TOKEN` 是 backend 共享密钥，**必传**，从 backend 运维处获取。

```bash
HARDWARE_TOKEN=eyJ... \
  ./codegen_runner_deploy/bootstrap_new_pi.sh <pi_ip> <device_id> <device_secret>
```

如果 ssh 用户名不是默认的 `guyu`，或 backend 不在默认地址：

```bash
HARDWARE_TOKEN=eyJ... PI_USER=guyu BACKEND_URL=http://<your-mac-ip>:8080 \
  ./codegen_runner_deploy/bootstrap_new_pi.sh <pi_ip> <device_id> <device_secret>
```

脚本 10 步自动完成：

1. ping 检查
2. SSH 免密（清旧 host key + accept-new，避免新镜像 known_hosts 冲突）
3. 系统基础：sudo-rs → classic sudo（兼容 sudoers 通配符）+ 时区 `Asia/Shanghai`
4. apt 装 `python3-pil python3-rpi-ws281x ffmpeg rpicam-apps`（含等 dpkg 锁释放，避免撞 unattended-upgrades）
5. pip 装 `sounddevice numpy requests`
6. 创建 `/opt/device-app/{current,output,backup,sdk}`
7. rsync SDK + runner + eye_matrix 驱动
8. sudoers.d 给 face 模块免密 + user systemd（含 `loginctl enable-linger`，让 PulseAudio 开机自起）
9. USB 声卡自适应：默认 sink/source、音量、AGC 自动开
10. 验证服务状态

跑完会打印 `journalctl -u codegen-runner -f` 命令，可以实时看 runner 是否在 poll。

### 3) 验收

```bash
./codegen_runner_deploy/verify_pi_setup.sh <pi_ip>
# 用户不是 guyu 时显式传 PI_USER：
PI_USER=other_user ./codegen_runner_deploy/verify_pi_setup.sh <pi_ip>
```

自动测：SSH / runner / SDK 模块 / camera / mic / 后端 LLM 联通。
人工感知：speaker 朗读"验收测试通过"+ face 灯阵切表情。

## 重新部署 / 换设备 / 换 backend

- 换 device_id：workshop 添新设备拿新凭证 → 重跑 bootstrap，会覆盖 systemd 配置
- 换 backend：`BACKEND_URL=https://... ./codegen_runner_deploy/bootstrap_new_pi.sh ...`
- device_secret 忘了：workshop 删设备 → 重新添加 → 拿新凭证 → 重跑 bootstrap

## 我们踩过的坑（供参考）

### Pi 时间倒退导致 pip SSL 拒绝

树莓派没 RTC 电池，新镜像 `fake-hwclock` 保存的最后一次开机时间往往是镜像制造日期，可能远早于现在。开机后 NTP 还没同步上时，pip 调 HTTPS（`pypi.tuna.tsinghua.edu.cn` 等）SSL 验证会发现 `证书 notBefore > 当前系统时间`，报 `certificate is not yet valid` 直接 fail。整个 `install_environment.sh` 就因此卡在装 `sounddevice` 那步。

**修复**：在 install_environment 之前先推开发机时间 + 启用 NTP：

```bash
ssh <user>@<pi_ip> "echo '<pwd>' | sudo -S date -s '$(date -u +%Y-%m-%d\ %H:%M:%S\ UTC)'"
ssh <user>@<pi_ip> "echo '<pwd>' | sudo -S timedatectl set-ntp true"
```

`bootstrap_new_pi.sh` 第 3 步也内置了防御性校时：如果 Pi 时间比开发机时间早超过 1 天，自动推开发机时间过去并启用 NTP。但 install_environment 在 bootstrap 之前跑、撞 SSL 失败后就回不来了，所以**校时必须在 install_environment 之前**。

### reboot 后 `ssh -o BatchMode=yes` 探活会卡住

reboot 后想等 SSH 回来时用 `until ssh -o BatchMode=yes ... 'uptime'; do sleep 3; done` 这种探活循环不可靠——Pi 公钥还没配上时 `BatchMode=yes` 会拒绝密码认证，但不同 SSH 版本/网络条件下表现不一：可能立即 exit 1 让循环 retry，也可能**死等加密协商超时**让整个 ssh 命令挂住。

**更稳的探活**：用 `nc -z` 探 TCP 22 端口（不进 SSH 协议握手）：

```bash
until nc -z -G 3 <pi_ip> 22; do sleep 3; done && echo "SSH port open"
```

**或者干脆不前置等待**：直接跑 `bootstrap_new_pi.sh`，它的 step 1（ping）+ step 2（SSH 探活）会自己等到 Pi 起来。

### apt 锁被 unattended-upgrades 占住

新 Pi 开机后 30~60 分钟 `apt-daily-upgrade.timer` 会触发 unattended-upgrades。如果烧录的镜像没在出厂前跑过 `apt upgrade`，第一次升级要装 100+ 包（kernel/sudo/openssh/glibc 全套），占 dpkg 锁可能**半小时以上**。这时跑 `apt-get install` 直接 `Could not get lock /var/lib/dpkg/lock-frontend`。

**强行打断会留半装的内核 + sudo，下次开机进不去系统**，必须等。

**bootstrap 第 4 步已加等锁循环**：跑 `apt-get install` 前先 poll `fuser /var/lib/dpkg/lock-frontend`，最多等 30 分钟。期间每 15 秒打印一次"等待中"和占用进程，超时则报错退出。

**根因建议**：让烧录镜像的同事在出厂前跑一次 `apt update && apt -y upgrade`，避免每台新 Pi 都要等半小时。

### SSH host key 变了导致连接被拒

新镜像 = 新 SSH host key。本地 `~/.ssh/known_hosts` 里有这台 IP 的旧 fingerprint 时，`ssh` 直接报 `REMOTE HOST IDENTIFICATION HAS CHANGED` 拒绝连接，**不是密码错**。

**bootstrap 第 2 步已自动处理**：跑 `ssh-keygen -R "$PI_IP"` 清旧 fingerprint，加 `StrictHostKeyChecking=accept-new` 自动接受新 host key。无旧 key 时静默无副作用。

### 音频实测现象

第一次在新 Pi 上跑 verify，TTS 没声、mic 录的全是底噪。诊断时观察到：

- `pactl list short sinks` 只有 `mailbox.stereo-fallback`，default sink 没指向 USB 声卡
- USB 声卡的 PCM playback 在 30%，听不到
- USB 麦的 AGC 关着，录音 peak 只到满量程的 1.3%，火山 ASR 识别不了

**bootstrap 第 9 步已经自适应处理**：扫 `pactl list short sinks/sources` 找名字带 `usb` 的设备 → 设默认 sink/source、sink 音量 70%、source 音量 85%；再用 `aplay -l` 拿 USB ALSA card index、用 `amixer scontrols` 探测 AGC 控件名（控件名因卡而异）→ 找到就 `sset on`，找不到就跳过、不让其他设备误伤。

如果 verify 阶段 speaker / mic 还是不对，先用硬件示例自证是不是 SDK 之外的问题：

```bash
ssh <user>@<pi_ip>
cd ~/test/goobo/audio_test
python3 speaker_play.py --freq 440 -t 2     # 听不到 = 播放链路问题
python3 mic_record.py -o /tmp/m.wav -t 5
python3 speaker_play.py --wav /tmp/m.wav    # 听不到自己 = 录音链路问题
```

硬件示例都不行说明跟我们 SDK 无关，往系统层 / 接线侧查。

### TTS 朗读放不出声 / 音频被切成几秒

第一版 `speaker.py` 用 `sounddevice` 的 `sd.play() + sd.wait()`。在 daemon 长跑场景反复调用会累积 PortAudio 内部 stream 状态，遇到 PulseAudio underrun/recover 时主线程死锁在 futex 上 — 表现是某轮跑完后 main.py 不再推进。

试过 `sd.OutputStream` 上下文管理器修了死锁但没修"音频被静默吞掉"——`stream.write` 在 PA underrun 时被节流，写入慢吞吞，调用方以为播完但实际只播了几秒。

**最终方案：subprocess 到 `paplay`**（PulseAudio 原生）/ 降级 `aplay`（直 ALSA）。每次播放是独立进程，没有累积状态、播完进程退出资源彻底释放、`stop()` 直接 kill。

但切到 `paplay` 后又遇到下一个坑：`paplay` 报 `Connection refused / pa_context_connect() failed`、0.02s 立刻退出 — 因为 codegen-runner 之前是 system service，开机时用户 session（`user@<uid>`）还没起来，`/run/user/<uid>/pulse/native` 目录不存在，PulseAudio 客户端连不上。

**解法**：runner 改跑 user systemd service（不是 system service），由 `user@<uid>.service` 自带 PulseAudio session、`XDG_RUNTIME_DIR` 等完整环境；配 `loginctl enable-linger <user>` 让 user session 开机自动起、不用 SSH 登录触发。这是 Linux 长跑音频 daemon 的标准做法。

bootstrap 第 8 步已经做了这两件事：写 unit 到 `~/.config/systemd/user/codegen-runner.service` + `loginctl enable-linger`。

### camera 拍照过曝

我们 SDK 调 `rpicam-still` 时给了 `-t 300`（300ms 预览），出来的照片整张白成一片。`rpicam-still` 的预览阶段是给 AEC/AWB 收敛用的，300ms 太短，AEC 还没稳定就抓了，往往锁在初始高 gain 上 → 过曝。

硬件示例 `goobo/camera_test/camera_capture.py` 没设 `-t`（用 rpicam-still 默认 5000ms）— 5 秒太长，daemon 每分钟拍一次顶不住。**实测 `-t 500` 是合适折中**：AEC 收敛足够清晰、整张拍照耗时 ~1 秒。SDK 已改成这个值。

### 时区错位 8 小时

测占卜师需求时 LLM 生成"6:00-10:00 触发"的代码。但 Pi 出厂镜像默认时区是 `Etc/UTC`，而我们的用户都在北京（UTC+8），结果"早上 6 点"实际是 **北京 14 点**，完全错位。

两个层面修：

**SDK 层**：`system.now()` 永远返回**北京时间**的 aware datetime（`ZoneInfo("Asia/Shanghai")`），不管 Pi 系统时区是什么。LLM 生成的代码写 `if now.hour >= 6` 直接按北京 6 点判断，不用关心时区这事。

**bootstrap 层**：第 3 步检测到 Pi 时区不是 `Asia/Shanghai` 就 `timedatectl set-timezone Asia/Shanghai`，让 `date` / `journalctl` / 系统日志的时间也是北京时间，方便排查问题对照。

## 技术细节

### 为什么 face 要 sudo
`rpi_ws281x` 库直接访问 PWM/DMA 硬件，普通用户没权限。用 sudoers.d 给一行 NOPASSWD 白名单（**只对那个特定脚本有效**），最小权限，比"整个 systemd service 跑 root"安全。

### 为什么 storage 路径用 env
`device.storage` 默认写 `/opt/device-app/output`（真机）。本地开发：

```bash
DEVICE_OUTPUT_DIR=/tmp/test PYTHONPATH=/path/to/sdk python3 main.py
```

Pi 部署不动这个变量。

### 设备凭证不可恢复
backend 不存 `device_secret` 明文副本（mongo 里就一份）。忘了只能 workshop 删除设备重新添加。
