#include <linux/module.h>
#include "rpi_dsi_driver.h"
/*********************沃乐康 10.0 inch wx101bh020i_40z **************BEGIN********************/
/*
 * wx101bh020i_40z 面板的初始化命令序列
 * 使用 mipi_dsi_dcs_write_seq_multi 发送一系列厂商提供的寄存器设置。
 * 这些命令大多来自面板手册（或参考实现），目的是设置 gamma、功率、MIPI 参数等。
 * 返回 ctx.accum_err（内部记录所有 DSI 发送错误的累积值）。
 */
inline static int wx101bh020i_40z_init_sequence(struct mipi_dsi_device* dsi)
{
    struct mipi_dsi_multi_context ctx = {.dsi = dsi};
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE1, 0x93);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE2, 0x65);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE3, 0xF8);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x80, 0x01);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x01);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x00, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x01, 0x44);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x03, 0x10);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x04, 0x38);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0C, 0x74);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x17, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x18, 0xAF);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x19, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1A, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1B, 0xAF);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1C, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x35, 0x26);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x37, 0x09);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x38, 0x04);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x39, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3A, 0x01);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3C, 0x78);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3D, 0xFF);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3E, 0xFF);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3F, 0x7F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x40, 0x06);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x41, 0xA0);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x42, 0x81);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x43, 0x1E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x44, 0x0D);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x45, 0x28);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x55, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x57, 0x69);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x59, 0x0A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5A, 0x2A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5B, 0x17);

    // G2.2    //G2.5
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5D, 0x7F); // 0x7F
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5E, 0x6B); // 0x69
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5F, 0x5C); // 0x59
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x60, 0x50); // 0x4C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x61, 0x4C); // 0x46
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x62, 0x3E); // 0x38
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x63, 0x41); // 0x3A
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x64, 0x2B); // 0x23
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x65, 0x43); // 0x3C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x66, 0x42); // 0x3B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x67, 0x43); // 0x3B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x68, 0x62); // 0x58
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x69, 0x52); // 0x46
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6A, 0x5A); // 0x4B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6B, 0x4C); // 0x3C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6C, 0x48); // 0x3A
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6D, 0x3A); // 0x2C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6E, 0x28); // 0x1D
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6F, 0x10); // 0x10
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x70, 0x7F); // 0x7F
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x71, 0x6B); // 0x69
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x72, 0x5C); // 0x59
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x73, 0x50); // 0x4C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x74, 0x4C); // 0x46
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x75, 0x3E); // 0x38
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x76, 0x41); // 0x3A
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x77, 0x2B); // 0x23
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x78, 0x43); // 0x3C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x79, 0x42); // 0x3B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7A, 0x43); // 0x3B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7B, 0x62); // 0x58
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7C, 0x52); // 0x46
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7D, 0x5A); // 0x4B
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7E, 0x4C); // 0x3C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7F, 0x48); // 0x3A
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x80, 0x3A); // 0x2C
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x81, 0x28); // 0x1D
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x82, 0x10); // 0x10
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x00, 0x42);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x01, 0x42);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x02, 0x40);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x03, 0x40);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x04, 0x5E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x05, 0x5E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x06, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x07, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x08, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x09, 0x57);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0A, 0x57);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0B, 0x77);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0C, 0x77);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0D, 0x47);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0E, 0x47);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0F, 0x45);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x10, 0x45);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x11, 0x4B);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x12, 0x4B);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x13, 0x49);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x14, 0x49);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x15, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x16, 0x41);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x17, 0x41);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x18, 0x40);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x19, 0x40);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1A, 0x5E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1B, 0x5E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1C, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1D, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1E, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x1F, 0x57);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x20, 0x57);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x21, 0x77);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x22, 0x77);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x23, 0x46);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x24, 0x46);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x25, 0x44);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x26, 0x44);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x27, 0x4A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x28, 0x4A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x29, 0x48);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2A, 0x48);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2B, 0x5F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2C, 0x01);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2D, 0x01);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2E, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2F, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x30, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x31, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x32, 0x1E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x33, 0x1E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x34, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x35, 0x17);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x36, 0x17);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x37, 0x37);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x38, 0x37);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x39, 0x08);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3A, 0x08);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3B, 0x0A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3C, 0x0A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3D, 0x04);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3E, 0x04);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x3F, 0x06);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x40, 0x06);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x41, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x42, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x43, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x44, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x45, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x46, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x47, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x48, 0x1E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x49, 0x1E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4A, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4B, 0x17);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4C, 0x17);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4D, 0x37);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4E, 0x37);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x4F, 0x09);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x50, 0x09);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x51, 0x0B);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x52, 0x0B);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x53, 0x05);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x54, 0x05);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x55, 0x07);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x56, 0x07);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x57, 0x1F);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x58, 0x40);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5B, 0x30);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5C, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5D, 0x34);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5E, 0x05);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x5F, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x63, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x64, 0x6A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x67, 0x73);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x68, 0x07);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x69, 0x08);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6A, 0x6A);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6B, 0x08);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6C, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6D, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6E, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x6F, 0x88);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x75, 0xFF);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x77, 0xDD);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x78, 0x2C);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x79, 0x15);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7A, 0x17);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7D, 0x14);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x7E, 0x82);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x04);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x00, 0x0E);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x02, 0xB3);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x09, 0x60);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x0E, 0x48);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x37, 0x58); // ȫ־ƽ̨add
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x2B, 0x0F); // ȫ־ƽ̨add
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x05);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0x15, 0x1D); // ȫ־ƽ̨add
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE0, 0x00);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE6, 0x02);
    mipi_dsi_dcs_write_seq_multi(&ctx, 0xE7, 0x0C);
    // mipi_dsi_dcs_write_seq_multi(&ctx, 0x11, 0x00);
    // mipi_dsi_msleep(&ctx, 120);
    // mipi_dsi_dcs_write_seq_multi(&ctx, 0x29, 0x00);
    // mipi_dsi_msleep(&ctx, 20);
    // mipi_dsi_dcs_write_seq_multi(&ctx, 0x36, 0x00);
    mipi_dsi_dcs_set_tear_on_multi(&ctx, MIPI_DSI_DCS_TEAR_MODE_VBLANK);
    return ctx.accum_err;
}

static const struct drm_display_mode wx101bh020i_40z_mode = {
    .clock = 70956, // 900 * 1314 * 60 / 1000 = 70956

    .hdisplay    = 800,
    .hsync_start = 800 + /* HFP */ 40,
    .hsync_end   = 800 + 40 + /* HSync */ 40,
    .htotal      = 800 + 40 + 40 + /* HBP */ 20,

    .vdisplay    = 1280,
    .vsync_start = 1280 + /* VFP */ 30,
    .vsync_end   = 1280 + 30 + /* VSync */ 4,
    .vtotal      = 1280 + 30 + 4 + /* VBP */ 10,

    .width_mm  = 135,
    .height_mm = 216,

    .type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED,
};

static const struct power_on_timing wx101bh020i_40z_pwr_timing =
    {
        .post_reset  = 20,
        .reset_low   = 20,
        .after_reset = 120,
        .slpout      = 120};

const struct rpi_dsi_display_desc wx101bh020i_40z_desc = {
    .mode          = &wx101bh020i_40z_mode,
    .lanes         = 2,
    .flags         = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_VIDEO_BURST | MIPI_DSI_MODE_LPM,
    .format        = MIPI_DSI_FMT_RGB888,
    .init_sequence = wx101bh020i_40z_init_sequence, // 初始化命令
    .pwr_timing    = &wx101bh020i_40z_pwr_timing,
    .do_sw_reset   = true // 软件复位
};

/*********************沃乐康 10.0 inch wx101bh020i_40z **************END*********************/

