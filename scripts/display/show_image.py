#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path


def run(cmd, check=False, **kwargs):
    print(f"[CMD] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def run_shell(cmd, check=False):
    print(f"[CMD] {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


def require_root():
    if os.geteuid() != 0:
        print("[INFO] Re-running with sudo...")
        os.execvp("sudo", ["sudo", sys.executable, *sys.argv])


def get_default_image():
    repo_dir = Path(__file__).resolve().parents[2]
    return repo_dir / "assets" / "goobo_startup_480x640.png"


def stop_old_fbi():
    print("[INFO] Stop old fbi process...")
    run(["killall", "fbi"], check=False)


def stop_login_screen():
    print("[INFO] Stop desktop login screen and tty1 login prompt...")
    run(["systemctl", "stop", "display-manager.service"], check=False)
    run(["systemctl", "stop", "getty@tty1.service"], check=False)


def switch_to_tty1():
    print("[INFO] Switch to tty1...")
    run(["chvt", "1"], check=False)


def unblank_framebuffer():
    fb_blank = Path("/sys/class/graphics/fb0/blank")
    if fb_blank.exists():
        print("[INFO] Unblank framebuffer...")
        try:
            fb_blank.write_text("0\n")
        except Exception as e:
            print(f"[WARN] Failed to unblank framebuffer: {e}")


def disable_terminal_blanking():
    print("[INFO] Disable terminal blanking and cursor...")
    # Redirection must happen inside the root shell, not in the user shell.
    run_shell(
        "TERM=linux setterm -blank 0 -powerdown 0 -cursor off < /dev/tty1 > /dev/tty1",
        check=False,
    )


def set_backlight_max():
    print("[INFO] Set backlight to max...")
    backlight_root = Path("/sys/class/backlight")

    if not backlight_root.exists():
        print("[WARN] /sys/class/backlight not found.")
        return

    for b in backlight_root.iterdir():
        if not b.is_dir():
            continue

        max_file = b / "max_brightness"
        brightness_file = b / "brightness"

        try:
            max_brightness = max_file.read_text().strip()
        except Exception:
            max_brightness = "255"

        try:
            brightness_file.write_text(max_brightness + "\n")
            print(f"[OK] {b.name} brightness = {max_brightness}")
        except Exception as e:
            print(f"[WARN] Failed to set brightness for {b.name}: {e}")


def show_image(image_path: Path):
    print("[INFO] Show image on /dev/fb0:")
    print(f"       {image_path}")

    if not Path("/dev/fb0").exists():
        print("[ERROR] /dev/fb0 not found.")
        sys.exit(1)

    if not image_path.exists():
        print("[ERROR] Image not found:")
        print(f"        {image_path}")
        sys.exit(1)

    run(
        [
            "fbi",
            "-T",
            "1",
            "-d",
            "/dev/fb0",
            "-a",
            "--noverbose",
            str(image_path),
        ],
        check=True,
    )


def main():
    require_root()

    if len(sys.argv) >= 2:
        image_path = Path(sys.argv[1]).expanduser().resolve()
    else:
        image_path = get_default_image()

    stop_old_fbi()
    stop_login_screen()
    switch_to_tty1()
    unblank_framebuffer()
    disable_terminal_blanking()
    set_backlight_max()
    show_image(image_path)


if __name__ == "__main__":
    main()
