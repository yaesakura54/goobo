GREEN  := \033[1;32m
YELLOW := \033[1;33m
CYAN   := \033[1;36m
RESET  := \033[0m

obj-m += panel-rpi-dsi-display.o
DTBO_NAME := vc4-kms-dsi-rpidisp
MODEL_FILE := /proc/device-tree/model
MODEL_EXISTS := $(wildcard $(MODEL_FILE))
PI_MODEL := pi4
MODULE_NAME := panel-rpi-dsi-display.ko
CONFIG_TXT := /boot/firmware/config.txt
OVERLAY_DIR := /boot/firmware/overlays
MODULE_INSTALL_DIR := /lib/modules/$(shell uname -r)/kernel/drivers/gpu/drm/panel

#链接
panel-rpi-dsi-display-y := rpi_dsi_driver.o panel_w280bf036i.o panel_wx101bh020i.o
ifneq ($(MODEL_EXISTS),)
    MODEL_FILE_STR := $(shell cat $(MODEL_FILE))
    ifeq ($(findstring Pi 4,$(MODEL_FILE_STR)),Pi 4)
        PI_MODEL := pi4
    else ifeq ($(findstring Pi 5,$(MODEL_FILE_STR)),Pi 5)
        PI_MODEL := pi5
	else ifeq ($(findstring Pi 3,$(MODEL_FILE_STR)),Pi 3)
    	PI_MODEL := pi3
	else
		@echo "Failed to detect Pi Model!"
		@exit 1
		endif
endif


# --------------------------------------------------------
# 3. 编译目标 (Targets)
# --------------------------------------------------------

# 默认目标提示
all:
	@echo "$(YELLOW)请指定要编译的屏幕型号，例如:$(RESET)"
	@echo "  make w280bf036i"
	@echo "  make wx101bh020i"

modules:
	@echo "$(CYAN)[INFO] 当前检测到的硬件平台: Raspberry Pi $(PI_MODEL)$(RESET)"
	@echo "$(GREEN)[CC]   开始编译内核驱动模块...$(RESET)"
	@$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
	@echo "$(GREEN)[OK]   内核模块 $(MODULE_NAME) 编译完成!$(RESET)"

clean:
	@echo "$(YELLOW)[CLEAN] 清理编译临时文件...$(RESET)"
	@$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
	@rm -rf *.dtbo
	@echo "$(GREEN)[OK]   清理完成.$(RESET)"

# --- 屏幕特定的编译任务 ---

w280bf036i: modules
	@echo "$(GREEN)[DTC]  正在编译 w280bf036i 设备树 (for $(PI_MODEL))...$(RESET)"
	@dtc -I dts -O dtb -o $(DTBO_NAME).dtbo dts/vc4-kms-dsi-w280bf036i-$(PI_MODEL).dts
	@echo "$(GREEN)[OK]   设备树 Overlay 生成完毕: $(DTBO_NAME).dtbo$(RESET)"

wx101bh020i: modules
	@echo "$(GREEN)[DTC]  正在编译 wx101bh020i 设备树 (for $(PI_MODEL))...$(RESET)"
	@dtc -I dts -O dtb -o $(DTBO_NAME).dtbo dts/vc4-kms-dsi-wx101bh020i-40z-$(PI_MODEL).dts
	@echo "$(GREEN)[OK]   设备树 Overlay 生成完毕: $(DTBO_NAME).dtbo$(RESET)"

# --- 安装任务 ---

install: remove
	@echo "$(CYAN)[INSTALL] 开始安装驱动...$(RESET)"
	
	@echo "  -> 复制内核模块到 $(MODULE_INSTALL_DIR)..."
	@install -m 644 -D $(MODULE_NAME) $(MODULE_INSTALL_DIR)
	
	@echo "  -> 复制设备树到 $(OVERLAY_DIR)..."
	@install -m 644 -D $(DTBO_NAME).dtbo $(OVERLAY_DIR)
	
	@echo "  -> 更新模块依赖 (depmod)..."
	@depmod -a
	
	@echo "  -> 修改 config.txt..."
	@echo "ignore_lcd=1" >> $(CONFIG_TXT)
	@echo "dtoverlay=$(DTBO_NAME)" >> $(CONFIG_TXT)
	
	@echo "$(GREEN)[SUCCESS] 安装完成! 请重启生效 (sudo reboot)$(RESET)"

remove:
	@echo "$(YELLOW)[REMOVE] 正在卸载旧驱动...$(RESET)"
	@rm -rf $(MODULE_INSTALL_DIR)/$(MODULE_NAME)
	@rm -rf $(OVERLAY_DIR)/$(DTBO_NAME).dtbo
	@sed -i "/ignore_lcd=1/d" $(CONFIG_TXT)
	@sed -i "/dtoverlay=$(DTBO_NAME)/d" $(CONFIG_TXT)
	@echo "$(GREEN)[OK]   旧驱动已移除.$(RESET)"