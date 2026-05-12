/* rpi_dsi_display.h */
#ifndef __RPI_DSI_DISPLAY_H__
#define __RPI_DSI_DISPLAY_H__

#include <drm/drm_mipi_dsi.h>
#include <drm/drm_modes.h>
#include <drm/drm_panel.h>
#include <linux/gpio/consumer.h>
#include <video/mipi_display.h>

/* 电源上电时序结构体 */
struct power_on_timing {
    unsigned long post_reset;
    unsigned long reset_low;
    unsigned long after_reset;
    unsigned long slpout;
};

/* 面板描述信息 */
struct rpi_dsi_display_desc {
    const struct drm_display_mode *mode;
    unsigned int lanes;
    unsigned long flags;
    enum mipi_dsi_pixel_format format;
    int (*init_sequence)(struct mipi_dsi_device *dsi);
    const struct power_on_timing *pwr_timing;
    bool do_sw_reset;
};

/* 驱动私有数据结构 */
struct rpi_dsi_display {
    struct drm_panel panel;
    struct mipi_dsi_device *dsi;
    const struct rpi_dsi_display_desc *desc;
    struct gpio_desc *reset;
    enum drm_panel_orientation orientation;
};

static inline struct rpi_dsi_display *to_rpi_dsi_display(struct drm_panel *panel)
{
    return container_of(panel, struct rpi_dsi_display, panel);
}

#endif /* __RPI_DSI_DISPLAY_H__ */