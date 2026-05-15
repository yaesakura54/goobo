"""
树莓派端 Runner — 轮询云端拉任务、执行、上报结果
"""
import glob
import json
import logging
import os
import shutil
import signal
import subprocess
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ===== 配置 =====
SERVER_URL = os.getenv("CODEGEN_SERVER_URL", "https://your-server.com")
DEVICE_ID = os.getenv("DEVICE_ID", "dev_001")
DEVICE_SECRET = os.getenv("DEVICE_SECRET", "xxx")
HARDWARE_TOKEN = os.getenv("HARDWARE_TOKEN", "xxx")

APP_DIR = "/opt/device-app/current"
OUTPUT_DIR = "/opt/device-app/output"
BACKUP_DIR = "/opt/device-app/backup"
SDK_DIR = "/opt/device-app/sdk"
POLL_INTERVAL = 3
VALIDATION_WAIT = 15

# ===== 全局状态 =====
current_process = None


def poll_server():
    """轮询云端拉取任务"""
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/codegen/device/poll",
            json={"device_id": DEVICE_ID, "device_secret": DEVICE_SECRET},
            headers={"Authorization": HARDWARE_TOKEN},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data")
            if data and data.get("task_id"):
                return data
        return None
    except Exception as e:
        log.error("轮询失败: %s", e)
        return None


def stop_current_app():
    """停止当前运行的应用进程"""
    global current_process
    if current_process and current_process.poll() is None:
        log.info("停止旧进程...")
        current_process.send_signal(signal.SIGTERM)
        try:
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            current_process.kill()
            current_process.wait()
    current_process = None


def backup_current():
    """备份当前代码"""
    main_py = os.path.join(APP_DIR, "main.py")
    if os.path.exists(main_py):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(main_py, os.path.join(BACKUP_DIR, "main.py"))
        log.info("已备份当前代码")


def deploy_code(code: str):
    """部署新代码"""
    os.makedirs(APP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main_py = os.path.join(APP_DIR, "main.py")
    with open(main_py, "w") as f:
        f.write(code)
    log.info("新代码已部署")


def start_app(task_id: str = "", attempt: int = 1):
    """启动应用进程。

    注入：
    - PYTHONPATH 让子进程能 `from device import ...`
    - TASK_ID / CODEGEN_ATTEMPT 让 SDK _tracer 知道把事件归属到哪个 task
    """
    global current_process
    main_py = os.path.join(APP_DIR, "main.py")
    env = {
        **os.environ,
        "PYTHONPATH": SDK_DIR,
        "TASK_ID": task_id,
        "CODEGEN_ATTEMPT": str(attempt),
    }
    current_process = subprocess.Popen(
        ["python3", main_py],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=APP_DIR,
        env=env,
    )
    log.info("应用已启动, PID=%s (TASK_ID=%s, attempt=%s)", current_process.pid, task_id, attempt)
    return current_process


def post_deploy_event(task_id: str, attempt: int, code_size: int):
    """部署成功瞬间给 backend 写一个 deploy event，作为 runtime log 的分隔符。"""
    try:
        requests.post(
            f"{SERVER_URL}/api/codegen/device/event",
            json={
                "device_id": DEVICE_ID,
                "device_secret": DEVICE_SECRET,
                "task_id": task_id,
                "attempt": attempt,
                "op": "deploy",
                "input": {"code_size_bytes": code_size},
            },
            headers={"Authorization": HARDWARE_TOKEN},
            timeout=5,
        )
    except Exception as e:
        log.warning("deploy event 上报失败: %s", e)


def read_output(proc, max_chars=2000):
    """非阻塞读取进程输出"""
    import select

    stdout = ""
    stderr = ""
    if proc.stdout and select.select([proc.stdout], [], [], 0)[0]:
        stdout = proc.stdout.read(max_chars).decode("utf-8", errors="replace")
    if proc.stderr and select.select([proc.stderr], [], [], 0)[0]:
        stderr = proc.stderr.read(max_chars).decode("utf-8", errors="replace")
    return stdout[-max_chars:], stderr[-max_chars:]


def check_expected_outputs(expected_outputs: dict) -> dict:
    """检查预期输出是否存在"""
    result = {}
    if not expected_outputs:
        return result

    for pattern in expected_outputs.get("files", []):
        if pattern.startswith("/"):
            full_pattern = pattern
        elif pattern.startswith("output/"):
            # output/xxx 解析到 /opt/device-app/output/xxx
            full_pattern = os.path.join(os.path.dirname(OUTPUT_DIR), pattern)
        else:
            full_pattern = os.path.join(APP_DIR, pattern)
        matches = glob.glob(full_pattern)
        result[f"file:{pattern}"] = len(matches) > 0

    return result


def report_to_server(task_id, success, stdout, stderr, output_check, process_alive):
    """上报执行结果"""
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/codegen/device/report",
            json={
                "device_id": DEVICE_ID,
                "device_secret": DEVICE_SECRET,
                "task_id": task_id,
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "output_check": output_check,
                "process_alive": process_alive,
            },
            headers={"Authorization": HARDWARE_TOKEN},
            timeout=10,
        )
        log.info("上报结果: success=%s, status_code=%s", success, resp.status_code)
    except Exception as e:
        log.error("上报失败: %s", e)


def rollback():
    """回滚到备份版本"""
    backup_main = os.path.join(BACKUP_DIR, "main.py")
    if os.path.exists(backup_main):
        shutil.copy2(backup_main, os.path.join(APP_DIR, "main.py"))
        log.info("已回滚到备份版本")
        start_app()
    else:
        log.warning("无备份可回滚")


def main():
    log.info("Runner 启动: device_id=%s, server=%s", DEVICE_ID, SERVER_URL)

    while True:
        task = poll_server()

        if not task:
            time.sleep(POLL_INTERVAL)
            continue

        task_id = task["task_id"]
        code = task["code"]
        expected_outputs = task.get("expected_outputs", {})
        attempt = int(task.get("attempt") or 1)

        log.info("收到任务: %s (attempt=%s)", task_id, attempt)

        # 停旧进程 → 备份 → 部署 → 起 deploy event 标记 → 启动
        stop_current_app()
        backup_current()
        deploy_code(code)
        post_deploy_event(task_id, attempt, len(code))
        proc = start_app(task_id=task_id, attempt=attempt)

        # 验证期
        log.info("验证期: 等待 %s 秒...", VALIDATION_WAIT)
        time.sleep(VALIDATION_WAIT)

        # 检查结果
        process_alive = proc.poll() is None
        stdout, stderr = read_output(proc)

        # 如果进程已退出，读取完整输出
        if not process_alive:
            remaining_out, remaining_err = proc.communicate(timeout=5)
            stdout += remaining_out.decode("utf-8", errors="replace")
            stderr += remaining_err.decode("utf-8", errors="replace")
            stdout = stdout[-2000:]
            stderr = stderr[-2000:]

        output_check = check_expected_outputs(expected_outputs)
        output_check_passed = all(output_check.values()) if output_check else True

        success = process_alive and output_check_passed and not stderr.strip()

        # 上报
        report_to_server(task_id, success, stdout, stderr, output_check, process_alive)

        # 失败则回滚
        if not success:
            log.warning("任务 %s 验证失败, 回滚", task_id)
            stop_current_app()
            rollback()


if __name__ == "__main__":
    main()
