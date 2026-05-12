savedcmd_panel-rpi-dsi-display.mod := printf '%s\n'   rpi_dsi_driver.o panel_w280bf036i.o panel_wx101bh020i.o | awk '!x[$$0]++ { print("./"$$0) }' > panel-rpi-dsi-display.mod
