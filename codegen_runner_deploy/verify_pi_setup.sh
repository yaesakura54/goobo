#!/usr/bin/env bash
# 验收新部署的树莓派：4 部件 + backend 联通
#
# 用法：
#   ./device_runner/deploy/verify_pi_setup.sh <pi_ip>
#
# 检查项：
#   1. SSH 连通
#   2. systemd 服务在跑
#   3. PYTHONPATH 下能 import device 全模块
#   4. camera 拍照（产物大小 > 0）
#   5. mic 录音 1 秒（产物大小 > 0）
#   6. speaker 朗读"测试"（人耳确认）
#   7. face 切换三个表情（眼睛灯阵确认）
#   8. backend /api/codegen/device/llm 联通
#
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "用法：$0 <pi_ip>"
  exit 1
fi

PI_IP="$1"
PI_USER="${PI_USER:-guyu}"
PI_HOST="${PI_USER}@${PI_IP}"

PASS=0
FAIL=0
results=()

check() {
  local name="$1"; shift
  local cmd="$*"
  if eval "$cmd" >/dev/null 2>&1; then
    results+=("✓ $name")
    PASS=$((PASS+1))
  else
    results+=("✗ $name")
    FAIL=$((FAIL+1))
  fi
}

echo "════════════════════════════════════════════════"
echo " 验收 $PI_HOST"
echo "════════════════════════════════════════════════"

# 1. SSH
check "SSH 可达" "ssh -o ConnectTimeout=5 -o BatchMode=yes $PI_HOST true"

# 2. systemd 服务
check "codegen-runner 运行中" "ssh $PI_HOST 'systemctl --user is-active codegen-runner | grep -q active'"

# 3. SDK 全模块 import
echo ""
echo "→ 测试 SDK 模块..."
ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk python3 -c '
from device import system, camera, mic, speaker, face, sensors, storage, vision, ai, net
print(\"  modules ok\")
'" && results+=("✓ SDK 模块导入") && PASS=$((PASS+1)) || { results+=("✗ SDK 模块导入"); FAIL=$((FAIL+1)); }

# 4. camera
echo ""
echo "→ 测试 camera 拍照..."
SIZE=$(ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk DEVICE_OUTPUT_DIR=/tmp/verify python3 -c '
import os
os.makedirs(\"/tmp/verify\", exist_ok=True)
from device import camera
ok = camera.capture_to(\"/tmp/verify/test.jpg\")
print(os.path.getsize(\"/tmp/verify/test.jpg\") if ok else 0)
' 2>&1 | tail -1")
if [ "${SIZE:-0}" -gt 1000 ]; then
  results+=("✓ camera 拍照（${SIZE} bytes）")
  PASS=$((PASS+1))
else
  results+=("✗ camera 拍照（产物 ${SIZE} bytes）")
  FAIL=$((FAIL+1))
fi

# 5. mic（录 1 秒，看是否产生 WAV）
echo "→ 测试 mic 录音 1 秒..."
SIZE=$(ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk DEVICE_OUTPUT_DIR=/tmp/verify python3 -c '
import os
os.makedirs(\"/tmp/verify\", exist_ok=True)
from device import mic
ok = mic.record_to(1, \"/tmp/verify/test.wav\")
print(os.path.getsize(\"/tmp/verify/test.wav\") if ok else 0)
' 2>&1 | tail -1")
if [ "${SIZE:-0}" -gt 1000 ]; then
  results+=("✓ mic 录音（${SIZE} bytes）")
  PASS=$((PASS+1))
else
  results+=("✗ mic 录音（产物 ${SIZE} bytes）")
  FAIL=$((FAIL+1))
fi

# 6. backend LLM 联通（顺带就证明了 device 凭证 + 网络通）
echo "→ 测试 backend LLM 联通..."
LLM_OK=$(ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk python3 -c '
import os
# Runner 进程的 env 需要从 systemd 拿不到，直接读 systemd 配置
with open(os.path.expanduser(\"~/.config/systemd/user/codegen-runner.service\")) as f:
    for line in f:
        if line.startswith(\"Environment=\"):
            k, _, v = line[12:].strip().partition(\"=\")
            os.environ[k] = v
from device import _llm
print(_llm.is_available())
import requests
r = requests.post(
    f\"{_llm.SERVER_URL}/api/codegen/device/llm\",
    json={\"device_id\": _llm.DEVICE_ID, \"device_secret\": _llm.DEVICE_SECRET, \"prompt\": \"hi\", \"max_tokens\": 4},
    headers={\"Authorization\": _llm.HW_TOKEN}, timeout=15,
)
print(r.status_code)
' 2>&1 | tail -2")
if echo "$LLM_OK" | grep -q "200"; then
  results+=("✓ backend LLM 联通")
  PASS=$((PASS+1))
else
  results+=("✗ backend LLM 联通 ($LLM_OK)")
  FAIL=$((FAIL+1))
fi

# 7. speaker + face 是有副作用的，需要人耳/人眼确认
echo ""
echo "════════════════════════════════════════════════"
echo " 自动检查结果（${PASS} pass, ${FAIL} fail）"
for r in "${results[@]}"; do echo "  $r"; done

echo ""
echo "════════════════════════════════════════════════"
echo " 接下来需要人工感知确认（看/听）："
echo "════════════════════════════════════════════════"

# stdin 是 tty 才 prompt y/n；CI/agent 等非交互场景跳过 prompt 但还是触发感知动作
INTERACTIVE=false
if [ -t 0 ]; then INTERACTIVE=true; fi

echo "→ 让设备说话（你应该听到女声'测试通过'）..."
ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk python3 -c '
import os
with open(os.path.expanduser(\"~/.config/systemd/user/codegen-runner.service\")) as f:
    for line in f:
        if line.startswith(\"Environment=\"):
            k, _, v = line[12:].strip().partition(\"=\")
            os.environ[k] = v
from device import speaker
speaker.say(\"验收测试通过\", voice=\"female\")
' 2>&1 | tail -3"

if $INTERACTIVE; then
  read -p "  听到女声'验收测试通过'了吗？(y/n) " SPK_OK
  if [ "$SPK_OK" = "y" ] || [ "$SPK_OK" = "Y" ]; then
    results+=("✓ speaker 人耳确认"); PASS=$((PASS+1))
  else
    results+=("✗ speaker 人耳确认"); FAIL=$((FAIL+1))
  fi
fi

echo ""
echo "→ 让脸切表情（你应该看到眼睛点阵切换 happy → surprised → neutral）..."
ssh "$PI_HOST" "PYTHONPATH=/opt/device-app/sdk python3 -c '
from device import face, system
import time
for s in [\"happy\", \"surprised\", \"neutral\"]:
    face.set_emotion(s)
    print(f\"  emotion={s}\")
    time.sleep(2)
face.off()
' 2>&1 | tail -5"

if $INTERACTIVE; then
  read -p "  看到 happy → surprised → neutral 切换且最后熄灭了吗？(y/n) " FACE_OK
  if [ "$FACE_OK" = "y" ] || [ "$FACE_OK" = "Y" ]; then
    results+=("✓ face 人眼确认"); PASS=$((PASS+1))
  else
    results+=("✗ face 人眼确认"); FAIL=$((FAIL+1))
  fi
fi

echo ""
echo "════════════════════════════════════════════════"
if $INTERACTIVE; then
  echo " 最终结果（${PASS} pass, ${FAIL} fail）"
  for r in "${results[@]}"; do echo "  $r"; done
  echo ""
  [ "$FAIL" -eq 0 ] && echo " ✅ 全部通过" || echo " ⚠ 有 $FAIL 项失败"
else
  [ "$FAIL" -eq 0 ] && echo " ✅ 自动检查全部通过" || echo " ⚠ 有 $FAIL 项自动检查失败"
  echo "   speaker + face 非交互模式跳过 prompt，请人工确认是否正常输出"
fi
echo "════════════════════════════════════════════════"
