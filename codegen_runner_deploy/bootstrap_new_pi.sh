#!/usr/bin/env bash
# 新树莓派一键初始化：从镜像烧录完到 codegen-runner 启动
#
# 用法：
#   HARDWARE_TOKEN=eyJ... BACKEND_URL=https://your-backend.example.com \
#     ./bootstrap_new_pi.sh <pi_ip> <device_id> <device_secret>
#
# 前置条件：
#   - 同目录下有 payload/（含 sdk/、runner.py、eye_matrix_8x8.py）
#   - 树莓派已烧录系统、连上网（同一局域网可 ping 通）
#   - SSH 用户存在，密码已知（首次会自动配 SSH 免密）
#   - 你已在 workshop 的"添加设备"弹窗里拿到 device_id 和 device_secret
#
# 完成后：
#   - 树莓派开机自动跑 codegen-runner，poll backend 等任务下发
set -euo pipefail

# 脚本和 payload/ 同级
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$SCRIPT_DIR/payload"

# ───── 配置（更换 backend 公网地址时改这里） ─────
BACKEND_URL="${BACKEND_URL:-http://192.168.50.25:8080}"
PI_USER="${PI_USER:-guyu}"
PI_PASSWORD="${PI_PASSWORD:-123456}"

# HARDWARE_TOKEN：必传环境变量（避免 JWT 进 git 仓库）。从 backend 运维处获取。
# ─────────────────────────────────────────────

if [ "$#" -lt 3 ]; then
  cat <<EOF
用法：$0 <pi_ip> <device_id> <device_secret>

示例：
  $0 192.168.50.31 rpi4b_a1b2c3d4 xxx-secret-yyy
  BACKEND_URL=https://api.example.com $0 ...

参数说明：
  pi_ip          — 树莓派的 IP 地址
  device_id      — workshop 添加设备时生成的 device_id
  device_secret  — workshop 添加设备时一次性显示的 secret

环境变量：
  HARDWARE_TOKEN — backend 共享密钥（**必传**，从 backend 运维处获取）
  BACKEND_URL    — 后端地址，默认 $BACKEND_URL
  PI_USER        — 树莓派 SSH 用户，默认 guyu
  PI_PASSWORD    — 首次配 SSH 时用的密码，默认 123456
  PIP_INDEX      — pip 镜像，默认清华
EOF
  exit 1
fi

PI_IP="$1"
DEVICE_ID="$2"
DEVICE_SECRET="$3"
PI_HOST="${PI_USER}@${PI_IP}"

# HARDWARE_TOKEN：必传，否则报错
if [ -z "${HARDWARE_TOKEN:-}" ]; then
  echo "❌ 必须传 HARDWARE_TOKEN 环境变量（从 backend 运维处获取）"
  echo "   示例：HARDWARE_TOKEN=eyJ... $0 $*"
  exit 1
fi
HW_TOKEN="$HARDWARE_TOKEN"

# 校验 payload/ 完整性
if [ ! -d "$PAYLOAD/sdk/device" ] || [ ! -f "$PAYLOAD/runner.py" ]; then
  echo "❌ payload 缺失：$PAYLOAD"
  echo "   需要包含 sdk/device/、sdk/examples/、runner.py、eye_matrix_8x8.py"
  exit 1
fi

# Helper：在 Pi 上跑 sudo 命令（password 走 stdin，比 expect 稳）
pi_sudo() {
  ssh "$PI_HOST" "echo '$PI_PASSWORD' | sudo -S -p '' bash -c \"$*\"" 2>&1 \
    | grep -v '^\[sudo\]' || true
}

echo "════════════════════════════════════════════════"
echo " Bootstrap 新树莓派"
echo "  设备:     $PI_HOST"
echo "  device_id: $DEVICE_ID"
echo "  backend:   $BACKEND_URL"
echo "════════════════════════════════════════════════"

# ─── 1) 网络可达 ───
echo ""
echo "[1/10] 检查网络..."
if ! ping -c 1 -W 2 "$PI_IP" >/dev/null 2>&1; then
  echo "  ❌ ping $PI_IP 失败，请确认 IP 和网络"
  exit 1
fi
echo "  ✓ Pi 可达"

# ─── 2) SSH 免密 ───
echo ""
echo "[2/10] 配置 SSH 免密..."
# 2a) 清掉 known_hosts 里 IP 的旧 fingerprint（新镜像 = 新 host key，否则 ssh 直接报
#     "REMOTE HOST IDENTIFICATION HAS CHANGED" 拒绝连接）。无旧 key 时静默返回，无副作用。
ssh-keygen -R "$PI_IP" >/dev/null 2>&1 || true

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "$PI_HOST" true 2>/dev/null; then
  if [ ! -f "$HOME/.ssh/id_ed25519.pub" ] && [ ! -f "$HOME/.ssh/id_rsa.pub" ]; then
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" -C "codegen-bootstrap" >/dev/null
    echo "  生成新 SSH key"
  fi
  expect <<EOF
set timeout 20
spawn ssh-copy-id -o StrictHostKeyChecking=no $PI_HOST
expect {
  "password:" { send "$PI_PASSWORD\r"; exp_continue }
  eof
}
EOF
  echo "  ✓ SSH 免密配好"
else
  echo "  ✓ SSH 免密已就绪"
fi

# ─── 3) 系统基础配置：sudo 兼容 + 时区 ───
echo ""
echo "[3/10] 系统基础配置..."

# 3a) sudo-rs → classic sudo（Ubuntu 25.10+ 默认装 sudo-rs，不支持 sudoers 通配符）
SUDO_VER=$(ssh "$PI_HOST" 'sudo --version 2>&1 | head -1' || echo "")
if echo "$SUDO_VER" | grep -qi "sudo-rs"; then
  if ssh "$PI_HOST" 'test -e /usr/bin/sudo.ws' 2>/dev/null; then
    pi_sudo "update-alternatives --set sudo /usr/bin/sudo.ws"
    NEW_VER=$(ssh "$PI_HOST" 'sudo --version 2>&1 | head -1')
    echo "  ✓ 已切到 classic sudo: $NEW_VER"
  else
    echo "  ⚠ 检测到 sudo-rs 但找不到 /usr/bin/sudo.ws，face NOPASSWD 通配符可能失效"
  fi
else
  echo "  ✓ 已是 classic sudo: $SUDO_VER"
fi

# 3b) 时区设 Asia/Shanghai（Pi 镜像默认 UTC，会导致生成代码里"早上 6 点"判错位 8 小时）
CUR_TZ=$(ssh "$PI_HOST" 'timedatectl show -p Timezone --value 2>/dev/null' || echo "")
if [ "$CUR_TZ" != "Asia/Shanghai" ]; then
  pi_sudo "timedatectl set-timezone Asia/Shanghai"
  echo "  ✓ 时区已切到 Asia/Shanghai（原: ${CUR_TZ:-unknown}）"
else
  echo "  ✓ 时区已是 Asia/Shanghai"
fi

# ─── 4) 装系统包 ───
echo ""
echo "[4/10] 安装系统依赖（apt）..."

# 4a) 等 dpkg 锁释放：新 Pi 开机 30~60 分钟后 apt-daily-upgrade.timer 会触发 unattended-upgrades，
#     如果烧录的镜像没跑过 apt upgrade，第一次升级要装 100+ 个包，会占锁半小时甚至更久。
#     之前实测撞过这个，跑 apt-get install 直接 fail "Could not get lock"。
#     强行打断会留半装的内核/sudo，下次开机进不去系统 → 必须等。
#     用 scp 临时脚本而非 pi_sudo 嵌套引号：内含的 echo "..." 会被远端 bash 解析时
#     和外层 bash -c "..." 撞引号，导致整段 here-block 被截断（实测踩过）。
WAIT_LOCK_TMP=$(mktemp -t bootstrap_wait_lock.XXXXXX)
cat > "$WAIT_LOCK_TMP" <<'WAIT_LOCK'
#!/bin/bash
deadline=$(($(date +%s) + 1800))   # 最多等 30 分钟
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
   || fuser /var/lib/dpkg/lock          >/dev/null 2>&1 \
   || fuser /var/lib/apt/lists/lock     >/dev/null 2>&1; do
  if [ $(date +%s) -gt $deadline ]; then
    echo '  ❌ 等 dpkg 锁 30 分钟没释放，可能 unattended-upgrades 卡住了'
    exit 1
  fi
  pids=$(fuser /var/lib/dpkg/lock-frontend 2>&1 | tr -d ' :' || true)
  echo "  ⏳ $(date +%T) 等 dpkg 锁释放（占用进程: ${pids:-?}）"
  sleep 15
done
echo '  ✓ dpkg 锁空闲'
WAIT_LOCK
scp -q "$WAIT_LOCK_TMP" "$PI_HOST:/tmp/bootstrap_wait_lock.sh"
pi_sudo "bash /tmp/bootstrap_wait_lock.sh && rm /tmp/bootstrap_wait_lock.sh"
rm -f "$WAIT_LOCK_TMP"

pi_sudo "DEBIAN_FRONTEND=noninteractive apt-get update -qq"
pi_sudo "DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pil python3-rpi-ws281x ffmpeg rpicam-apps" \
  | tail -5
echo "  ✓ apt 包装好"

# ─── 5) 装 Python 包（用户态） ───
# 注意：Pillow 不走 pip（apt 的 python3-pil 已提供，且 pip 装 aarch64 wheel 经常超时）
# 用清华镜像加速国内拉取
PIP_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
echo ""
echo "[5/10] 安装 Python 包（pip --user，镜像: ${PIP_INDEX}）..."
ssh "$PI_HOST" "
  set -e
  if ! python3 -m pip --version >/dev/null 2>&1; then
    curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py --user --break-system-packages -i $PIP_INDEX >/dev/null
  fi
  python3 -m pip install --user --break-system-packages --quiet --timeout 60 --retries 5 \
    -i $PIP_INDEX \
    sounddevice numpy requests
  python3 -c 'import sounddevice, numpy, PIL, requests; print(\"  ✓ pip 包就绪\")'
"

# ─── 6) 创建工作目录 ───
echo ""
echo "[6/10] 创建 /opt/device-app 目录..."
pi_sudo "mkdir -p /opt/device-app/{current,output,backup,sdk} && chown -R $PI_USER:$PI_USER /opt/device-app"
ssh "$PI_HOST" "mkdir -p ~/codegen-runner ~/test/goobo/eye_matrix_test"
echo "  ✓ 目录就绪"

# ─── 7) 部署 SDK + runner + eye_matrix 驱动 ───
echo ""
echo "[7/10] 同步代码..."
rsync -az --delete "$PAYLOAD/sdk/device/" "$PI_HOST:/opt/device-app/sdk/device/"
rsync -az --delete "$PAYLOAD/sdk/examples/" "$PI_HOST:/opt/device-app/sdk/examples/"
scp -q "$PAYLOAD/runner.py" "$PI_HOST:~/codegen-runner/runner.py"

if [ -f "$PAYLOAD/eye_matrix_8x8.py" ]; then
  scp -q "$PAYLOAD/eye_matrix_8x8.py" "$PI_HOST:~/test/goobo/eye_matrix_test/eye_matrix_8x8.py"
  echo "  ✓ eye_matrix 驱动已部署"
else
  echo "  ⚠ payload 内无 eye_matrix_8x8.py，face 灯阵将走 mock"
fi
echo "  ✓ SDK + runner 已同步"

# ─── 8) sudoers + systemd ───
echo ""
echo "[8/10] 配置 sudoers (face 免密) + systemd..."

# 8a) sudoers：让 PI_USER 能不输密码地跑 eye_matrix（face 模块需要）
# 用 scp 写本地文件再 sudo mv，比 echo > /etc/sudoers.d 更稳（避开 stdin 跟 password 抢通道的坑）
SUDOERS_TMP="/tmp/codegen-eye-matrix.sudoers"
cat > "$SUDOERS_TMP" <<EOF
$PI_USER ALL=(root) NOPASSWD: /usr/bin/python3 /home/$PI_USER/test/goobo/eye_matrix_test/eye_matrix_8x8.py *
EOF
scp -q "$SUDOERS_TMP" "$PI_HOST:/tmp/codegen-eye-matrix.sudoers"
pi_sudo "mv /tmp/codegen-eye-matrix.sudoers /etc/sudoers.d/codegen-eye-matrix && chown root:root /etc/sudoers.d/codegen-eye-matrix && chmod 440 /etc/sudoers.d/codegen-eye-matrix"
rm -f "$SUDOERS_TMP"

# 8b) user systemd service（不是 system service）
# 跑成 user service 是音频 daemon 的标准做法 — user@<uid>.service 自带 PulseAudio
# user session、XDG_RUNTIME_DIR 等环境，paplay 才能连上 /run/user/<uid>/pulse/native。
# 用 system service 的话开机时 user session 还没起来，paplay 直接连接拒绝。
# enable-linger 让 user@<uid> 开机自动起，不用 SSH 登录触发。
pi_sudo "loginctl enable-linger $PI_USER"

ssh "$PI_HOST" "mkdir -p ~/.config/systemd/user"
SVC_FILE="/tmp/codegen-runner.service"
cat > "$SVC_FILE" <<EOF
[Unit]
Description=Codegen Device Runner
After=default.target pulseaudio.service
Wants=pulseaudio.service

[Service]
Type=simple
WorkingDirectory=%h/codegen-runner
ExecStart=/usr/bin/python3 %h/codegen-runner/runner.py

Environment=CODEGEN_SERVER_URL=$BACKEND_URL
Environment=DEVICE_ID=$DEVICE_ID
Environment=DEVICE_SECRET=$DEVICE_SECRET
Environment=HARDWARE_TOKEN=$HW_TOKEN

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
scp -q "$SVC_FILE" "$PI_HOST:.config/systemd/user/codegen-runner.service"
ssh "$PI_HOST" "systemctl --user daemon-reload && systemctl --user enable codegen-runner && systemctl --user restart codegen-runner"
rm -f "$SVC_FILE"
echo "  ✓ user systemd 服务已启动"

# ─── 9) 音频自适应配置（USB 声卡） ───
# README 第二节"音频实测现象"：新 Pi 上 default sink 不指 USB 声卡、PCM 30%、AGC off →
# TTS 没声 / mic 录的全是底噪。这一步在 PA 里设默认 sink/source、拉音量、开 AGC。
# 不同 USB 声卡 mixer 控件名不一样 → 找不到的就跳过，不让其他设备误伤。
echo ""
echo "[9/10] 音频自适应配置（USB 声卡）..."
ssh "$PI_HOST" 'bash -s' <<'AUDIO_CFG'
set -uo pipefail

# 等用户 PulseAudio session 起来（user@<uid>.service 起完到 PA 就绪有几秒延迟）
for i in $(seq 1 15); do
  if pactl info >/dev/null 2>&1; then break; fi
  sleep 1
done
if ! pactl info >/dev/null 2>&1; then
  echo "  ⚠ PulseAudio user session 没起来，跳过音频配置"
  echo "    （手工修复：登录后跑 pactl info；下面这套 pactl 命令）"
  exit 0
fi

# 找 USB 声卡的 sink（输出）和 source（输入），名字含 usb
USB_SINK=$(pactl list short sinks 2>/dev/null   | awk '$2 ~ /[Uu][Ss][Bb]/ {print $2; exit}')
USB_SOURCE=$(pactl list short sources 2>/dev/null | awk '$2 ~ /[Uu][Ss][Bb]/ && $2 !~ /\.monitor$/ {print $2; exit}')

if [ -n "$USB_SINK" ]; then
  pactl set-default-sink   "$USB_SINK"      2>/dev/null && echo "  ✓ 默认 sink   → $USB_SINK"
  pactl set-sink-volume    "$USB_SINK" 70%  2>/dev/null && echo "  ✓ sink   音量 70%"
  pactl set-sink-mute      "$USB_SINK" 0    2>/dev/null
else
  echo "  ⚠ 没找到 USB sink（playback），跳过输出配置"
fi

if [ -n "$USB_SOURCE" ]; then
  pactl set-default-source "$USB_SOURCE"     2>/dev/null && echo "  ✓ 默认 source → $USB_SOURCE"
  pactl set-source-volume  "$USB_SOURCE" 85% 2>/dev/null && echo "  ✓ source 音量 85%"
  pactl set-source-mute    "$USB_SOURCE" 0   2>/dev/null
else
  echo "  ⚠ 没找到 USB source（capture），跳过输入配置"
fi

# 麦克风 AGC（部分 USB 声卡有 ALSA 'Auto Gain Control' 控件，控件名因卡而异 → 探测）
USB_CARD_IDX=$(aplay -l 2>/dev/null | grep -iE 'card [0-9]+:.*usb' | head -1 | sed -E 's/^card ([0-9]+):.*/\1/')
if [ -n "$USB_CARD_IDX" ]; then
  AGC_CTL=$(amixer -c "$USB_CARD_IDX" scontrols 2>/dev/null \
            | grep -iE "auto gain|agc" | head -1 | sed -E "s/.*'([^']+)'.*/\1/")
  if [ -n "$AGC_CTL" ]; then
    amixer -c "$USB_CARD_IDX" sset "$AGC_CTL" on >/dev/null 2>&1 \
      && echo "  ✓ AGC 已开（card $USB_CARD_IDX, '$AGC_CTL'）"
  else
    echo "  ⚠ card $USB_CARD_IDX 没 AGC 控件（录音过小可硬件层调）"
  fi
  # 顺手把 capture 主控件音量到 80%（如有 'Mic' 或 'Capture'）
  for ctl in "Mic" "Capture"; do
    if amixer -c "$USB_CARD_IDX" sget "$ctl" >/dev/null 2>&1; then
      amixer -c "$USB_CARD_IDX" sset "$ctl" 80% >/dev/null 2>&1 \
        && echo "  ✓ ALSA card $USB_CARD_IDX '$ctl' → 80%"
    fi
  done
else
  echo "  ⚠ aplay -l 没找到 USB card，跳过 ALSA 层调整"
fi
AUDIO_CFG

# ─── 10) 验证 ───
echo ""
echo "[10/10] 验证服务状态..."
sleep 2
STATUS=$(ssh "$PI_HOST" 'systemctl --user is-active codegen-runner' || echo "unknown")
echo "  systemd (user): $STATUS"
ssh "$PI_HOST" 'journalctl --user -u codegen-runner -n 5 --no-pager' 2>&1 | tail -5

echo ""
echo "════════════════════════════════════════════════"
echo " ✅ Bootstrap 完成"
echo ""
echo " 下一步："
echo "   验证 4 个部件: PI_USER=$PI_USER ./verify_pi_setup.sh $PI_IP"
echo "   实时看日志:    ssh $PI_HOST 'journalctl -u codegen-runner -f'"
echo "   提交任务:      浏览器打开 $BACKEND_URL/api/codegen/workshop"
echo "                  在设备下拉里选 $DEVICE_ID"
echo "════════════════════════════════════════════════"
