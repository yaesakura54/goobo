"""示例 06: CPU 温度监控 — 系统信息 + CSV 写文件。

每 5 秒采一次 CPU 温度，写入 cpu_temp.csv。
"""
from device import system, storage


def main():
    print("CPU 温度监控启动")
    # 写表头（只在首次）
    if not storage.exists("cpu_temp.csv"):
        storage.append_line("cpu_temp.csv", "timestamp,temp_celsius")

    count = 0
    while system.should_continue():
        ts = system.now().strftime("%Y-%m-%d %H:%M:%S")
        temp = system.cpu_temp()
        if temp is not None:
            storage.append_line("cpu_temp.csv", f"{ts},{temp:.2f}")
            print(f"[{ts}] CPU 温度: {temp:.2f}°C")
            count += 1
        system.sleep(5)
    print(f"CPU 监控已退出，共记录 {count} 条")


if __name__ == "__main__":
    main()
