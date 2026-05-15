"""示例 01: 心跳循环 — 最基础的 SDK 使用模式。

每 2 秒在输出目录追加一行时间戳，演示：
- system.should_continue() 主循环条件
- system.sleep() 可中断等待
- storage.append_line() 追加写文件
"""
from device import system, storage


def main():
    print("心跳程序启动")
    count = 0
    while system.should_continue():
        ts = system.now().strftime("%Y-%m-%d %H:%M:%S")
        storage.append_line("heartbeat.txt", ts)
        count += 1
        print(f"心跳 {count}: {ts}")
        system.sleep(2)
    print(f"心跳程序已优雅退出，共 {count} 次")


if __name__ == "__main__":
    main()
