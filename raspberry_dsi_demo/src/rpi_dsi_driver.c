
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_modes.h>
#include <drm/drm_panel.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <video/mipi_display.h>
#include <linux/of.h>
#include <linux/backlight.h>



extern const struct rpi_dsi_display_desc w280bf036i_desc;
extern const struct rpi_dsi_display_desc wx101bh020i_40z_desc;


/*
 * 电源上电时序结构体
 * post_reset: 在重置后等待的毫秒数（用于让 IC 稳定）
 * reset_low:  重置引脚拉低持续的毫秒数
 * after_reset: 在重置完成后等待的毫秒数（用于软复位或初始化前的延时）
 * slpout: 退出睡眠模式后等待的毫秒数
 */
struct power_on_timing
{
    unsigned long post_reset;
    unsigned long reset_low;
    unsigned long after_reset;
    unsigned long slpout;
};

/*
 * 面板描述信息
 * 包含显示模式、DSI 通道数、像素格式、初始化序列以及上电时序等信息。
 * init_sequence: 指向发送面板初始化命令序列的回调（可为 NULL）
 * pwr_timing: 指向上面定义的电源时序结构体
 * do_sw_reset: 是否在准备阶段执行 DCS 软复位
 */
struct rpi_dsi_display_desc
{
    const struct drm_display_mode* mode;
    unsigned int                   lanes;
    unsigned long                  flags;
    enum mipi_dsi_pixel_format     format;
    int (*init_sequence)(struct mipi_dsi_device* dsi);
    const struct power_on_timing* pwr_timing;
    bool                          do_sw_reset;
};

/*
 * 驱动私有数据结构，绑定到 drm_panel
 * 包含对 mipi_dsi_device 的引用、面板描述以及复位 GPIO 等信息
 */
struct rpi_dsi_display
{
    struct drm_panel                   panel;
    struct mipi_dsi_device*            dsi;
    const struct rpi_dsi_display_desc* desc;
    struct gpio_desc*                  reset;
    enum drm_panel_orientation         orientation;
};

/* 将通用的 drm_panel 指针转换为我们的私有结构体指针 */
inline static struct rpi_dsi_display* to_rpi_dsi_display(struct drm_panel* panel)
{
    return container_of(panel, struct rpi_dsi_display, panel);
}
/**
 * 程序入口
 */
static int rpi_dsi_display_prepare(struct drm_panel* panel)
{
    struct rpi_dsi_display*       rpi_dsi_display = to_rpi_dsi_display(panel);
    struct mipi_dsi_multi_context ctx             = {.dsi = rpi_dsi_display->dsi};
    /*
     * 执行硬件复位序列（如果提供了 reset GPIO）
     * 通常顺序：拉高 -> 等待 post_reset -> 拉低 -> 等待 reset_low -> 拉高 -> 等待 after_reset
     */
    if (rpi_dsi_display->reset)
    {
        gpiod_set_value_cansleep(rpi_dsi_display->reset, 1);
        msleep(rpi_dsi_display->desc->pwr_timing->post_reset);
        gpiod_set_value_cansleep(rpi_dsi_display->reset, 0);
        msleep(rpi_dsi_display->desc->pwr_timing->reset_low);
        gpiod_set_value_cansleep(rpi_dsi_display->reset, 1);
        msleep(rpi_dsi_display->desc->pwr_timing->after_reset);
    }

    /* 可选的软件 DCS 复位 */
    if (rpi_dsi_display->desc->do_sw_reset)
    {
        mipi_dsi_dcs_soft_reset_multi(&ctx);
        msleep(rpi_dsi_display->desc->pwr_timing->after_reset);
    }

    /* 发送面板定制的初始化命令序列（如果有） */
    if (rpi_dsi_display->desc->init_sequence)
    {
        int ret = rpi_dsi_display->desc->init_sequence(
            rpi_dsi_display->dsi);
        /*
         * 注意：init_sequence 返回的是 ctx.accum_err（int），不是 ERR_PTR。
         * 这里保持原有逻辑：如果返回值为错误（负值），打印日志并返回错误码。
         */
        if (ret < 0)
        {
            dev_err(panel->dev,
                    "Failed to send init sequence to panel: %d",
                    ret);
            return ret;
        }
    }
    mipi_dsi_dcs_exit_sleep_mode_multi(&ctx);
    msleep(rpi_dsi_display->desc->pwr_timing->slpout);
    return ctx.accum_err;
}

inline static int rpi_dsi_display_enable(struct drm_panel* panel)
{
    struct mipi_dsi_multi_context ctx = {.dsi = to_mipi_dsi_device(
                                            panel->dev)};
    mipi_dsi_dcs_set_display_on_multi(&ctx);
    return ctx.accum_err;
}

inline static int rpi_dsi_display_disable(struct drm_panel* panel)
{
    struct mipi_dsi_multi_context ctx = {.dsi = to_mipi_dsi_device(
                                            panel->dev)};
    mipi_dsi_dcs_set_display_off_multi(&ctx);
    return ctx.accum_err;
}

static int rpi_dsi_display_unprepare(struct drm_panel* panel)
{
    struct rpi_dsi_display*       rpi_dsi_display = to_rpi_dsi_display(panel);
    struct mipi_dsi_multi_context ctx             = {.dsi = rpi_dsi_display->dsi};
    mipi_dsi_dcs_enter_sleep_mode_multi(&ctx);

    if (rpi_dsi_display->reset)
        gpiod_set_value_cansleep(rpi_dsi_display->reset, 0);
    return ctx.accum_err;
}

static int rpi_dsi_display_get_modes(struct drm_panel*     panel,
                                    struct drm_connector* connector)
{
    struct rpi_dsi_display*        rpi_dsi_display = to_rpi_dsi_display(panel);
    const struct drm_display_mode* desc_mode       = rpi_dsi_display->desc->mode;
    struct drm_display_mode*       mode;

    mode = drm_mode_duplicate(connector->dev, desc_mode);
    if (!mode)
    {
        dev_err(&rpi_dsi_display->dsi->dev,
                "failed to add mode %ux%u@%u\n",
                desc_mode->hdisplay,
                desc_mode->vdisplay,
                drm_mode_vrefresh(desc_mode));
        return -ENOMEM;
    }

    drm_mode_set_name(mode);
    drm_mode_probed_add(connector, mode);

    connector->display_info.width_mm  = desc_mode->width_mm;
    connector->display_info.height_mm = desc_mode->height_mm;

    drm_connector_set_orientation_from_panel(connector, panel);
    return 1;
}

inline static enum drm_panel_orientation
rpi_dsi_display_get_orientation(struct drm_panel* panel)
{
    struct rpi_dsi_display* rpi_dsi_display = to_rpi_dsi_display(panel);
    return rpi_dsi_display->orientation;
}

static const struct drm_panel_funcs rpi_dsi_display_funcs = {
    .disable         = rpi_dsi_display_disable,
    .unprepare       = rpi_dsi_display_unprepare,
    .prepare         = rpi_dsi_display_prepare,
    .enable          = rpi_dsi_display_enable,
    .get_modes       = rpi_dsi_display_get_modes,
    .get_orientation = rpi_dsi_display_get_orientation,
};

static int rpi_dsi_display_set_brightness(struct backlight_device* bl)
{
    struct rpi_dsi_display* rpi_dsi_display = bl_get_data(bl);
    struct mipi_dsi_device* dsi             = rpi_dsi_display->dsi;
    uint8_t                 brightness      = bl->props.brightness;
    int                     ret             = 0;
    ret                                     = mipi_dsi_dcs_write(dsi, MIPI_DCS_SET_DISPLAY_BRIGHTNESS, &brightness, sizeof(brightness));
    if (ret < 0)
        return ret;
    return 0;
}

static const struct backlight_ops rpi_dsi_display_bl_ops = {
    .update_status = rpi_dsi_display_set_brightness,
};

/**
 * 程序入口
 */
static int rpi_dsi_display_probe(struct mipi_dsi_device* dsi)
{
    struct rpi_dsi_display* rpi_dsi_display =
        devm_kzalloc(&dsi->dev, sizeof(*rpi_dsi_display), GFP_KERNEL);
    if (!rpi_dsi_display)
        return -ENOMEM;

    const struct rpi_dsi_display_desc* desc =
        of_device_get_match_data(&dsi->dev);
    dsi->mode_flags = desc->flags;
    dsi->format     = desc->format;
    dsi->lanes      = desc->lanes;

    rpi_dsi_display->panel.prepare_prev_first = true;

    rpi_dsi_display->reset =
        devm_gpiod_get_optional(&dsi->dev, "reset", GPIOD_OUT_HIGH);
    if (IS_ERR(rpi_dsi_display->reset))
    {
        dev_err(&dsi->dev, "Failed to get reset GPIO\n");
        return PTR_ERR(rpi_dsi_display->reset);
    }

    int ret = of_drm_get_panel_orientation(dsi->dev.of_node,
                                           &rpi_dsi_display->orientation);
    if (ret < 0)
    {
        dev_warn(&dsi->dev,
                 "Failed to get orientation, default to normal");
        rpi_dsi_display->orientation =
            DRM_MODE_PANEL_ORIENTATION_NORMAL;
    }

    drm_panel_init(&rpi_dsi_display->panel, &dsi->dev, &rpi_dsi_display_funcs, DRM_MODE_CONNECTOR_DSI);

    ret = drm_panel_of_backlight(&rpi_dsi_display->panel);
    if (ret < 0)
        return ret;

    if (!rpi_dsi_display->panel.backlight)
    {
        dev_info(&dsi->dev,
                 "No backlight configured, using DCS backlight\n");
        struct backlight_device* bl = devm_backlight_device_register(
            &dsi->dev, "rpi-dsi-display-bl", &dsi->dev, rpi_dsi_display, &rpi_dsi_display_bl_ops, NULL);
        if (IS_ERR(bl))
        {
            dev_err(&dsi->dev, "Failed to register DCS backlight device\n");
            return PTR_ERR(bl);
        }
        bl->props.max_brightness         = 0xFF;
        bl->props.brightness             = 0x80;
        bl->props.power                  = BACKLIGHT_POWER_OFF;
        rpi_dsi_display->panel.backlight = bl;
    }

    drm_panel_add(&rpi_dsi_display->panel);

    mipi_dsi_set_drvdata(dsi, rpi_dsi_display);
    rpi_dsi_display->dsi  = dsi;
    rpi_dsi_display->desc = desc;
    if ((ret = mipi_dsi_attach(dsi)))
        drm_panel_remove(&rpi_dsi_display->panel);
    return ret;
}

static void rpi_dsi_display_remove(struct mipi_dsi_device* dsi)
{
    struct rpi_dsi_display* rpi_dsi_display = mipi_dsi_get_drvdata(dsi);

    mipi_dsi_detach(dsi);
    drm_panel_remove(&rpi_dsi_display->panel);
}

static const struct of_device_id rpi_dsi_display_ids[] = {
    {.compatible = "wlk,w280bf036i", .data = &w280bf036i_desc},
    {.compatible = "wlk,wx101bh020i-40z", .data = &wx101bh020i_40z_desc},
    {}
};

MODULE_DEVICE_TABLE(of, rpi_dsi_display_ids);

static struct mipi_dsi_driver rpi_dsi_display = {
    .probe  = rpi_dsi_display_probe,
    .remove = rpi_dsi_display_remove,
    .driver =
        {
                .name           = "rpi_dsi_display_driver",
                .of_match_table = rpi_dsi_display_ids,
        },
};

module_mipi_dsi_driver(rpi_dsi_display);
MODULE_AUTHOR("coocaxx");
MODULE_DESCRIPTION("RPI DSI Display driver");
MODULE_LICENSE("GPL");