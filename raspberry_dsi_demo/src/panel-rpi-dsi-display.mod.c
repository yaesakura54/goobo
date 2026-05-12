#include <linux/module.h>
#include <linux/export-internal.h>
#include <linux/compiler.h>

MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};



static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0x6b720f69, "drm_mode_vrefresh" },
	{ 0xa1bdf106, "devm_kmalloc" },
	{ 0x6056b609, "drm_panel_add" },
	{ 0xe4fabe56, "drm_mode_probed_add" },
	{ 0x471c6663, "gpiod_set_value_cansleep" },
	{ 0xd56c0a40, "mipi_dsi_dcs_set_tear_on_multi" },
	{ 0xea0fbd40, "mipi_dsi_dcs_write_buffer_multi" },
	{ 0x1e05c42e, "mipi_dsi_attach" },
	{ 0xe28e5f14, "mipi_dsi_dcs_write" },
	{ 0x55901458, "mipi_dsi_dcs_exit_sleep_mode_multi" },
	{ 0x68732600, "devm_gpiod_get_optional" },
	{ 0x6056b609, "drm_panel_remove" },
	{ 0xd272d446, "__stack_chk_fail" },
	{ 0x291b9dfd, "_dev_info" },
	{ 0xa3350b9e, "mipi_dsi_driver_register_full" },
	{ 0x55901458, "mipi_dsi_dcs_enter_sleep_mode_multi" },
	{ 0x291b9dfd, "_dev_err" },
	{ 0x55901458, "mipi_dsi_dcs_set_display_off_multi" },
	{ 0x1e05c42e, "mipi_dsi_detach" },
	{ 0x51273755, "drm_connector_set_orientation_from_panel" },
	{ 0x0ac69d5f, "drm_mode_duplicate" },
	{ 0x35613d59, "drm_mode_set_name" },
	{ 0xba606f1f, "mipi_dsi_driver_unregister" },
	{ 0x291b9dfd, "_dev_warn" },
	{ 0x8cc37618, "drm_panel_init" },
	{ 0xacf4d36d, "of_drm_get_panel_orientation" },
	{ 0x55901458, "mipi_dsi_dcs_soft_reset_multi" },
	{ 0x55901458, "mipi_dsi_dcs_set_display_on_multi" },
	{ 0xe4de56b4, "__ubsan_handle_load_invalid_value" },
	{ 0xf4e8838e, "of_device_get_match_data" },
	{ 0xfd932d77, "devm_backlight_device_register" },
	{ 0x67628f51, "msleep" },
	{ 0x4e20863e, "module_layout" },
};

static const u32 ____version_ext_crcs[]
__used __section("__version_ext_crcs") = {
	0x6b720f69,
	0xa1bdf106,
	0x6056b609,
	0xe4fabe56,
	0x471c6663,
	0xd56c0a40,
	0xea0fbd40,
	0x1e05c42e,
	0xe28e5f14,
	0x55901458,
	0x68732600,
	0x6056b609,
	0xd272d446,
	0x291b9dfd,
	0xa3350b9e,
	0x55901458,
	0x291b9dfd,
	0x55901458,
	0x1e05c42e,
	0x51273755,
	0x0ac69d5f,
	0x35613d59,
	0xba606f1f,
	0x291b9dfd,
	0x8cc37618,
	0xacf4d36d,
	0x55901458,
	0x55901458,
	0xe4de56b4,
	0xf4e8838e,
	0xfd932d77,
	0x67628f51,
	0x4e20863e,
};
static const char ____version_ext_names[]
__used __section("__version_ext_names") =
	"drm_mode_vrefresh\0"
	"devm_kmalloc\0"
	"drm_panel_add\0"
	"drm_mode_probed_add\0"
	"gpiod_set_value_cansleep\0"
	"mipi_dsi_dcs_set_tear_on_multi\0"
	"mipi_dsi_dcs_write_buffer_multi\0"
	"mipi_dsi_attach\0"
	"mipi_dsi_dcs_write\0"
	"mipi_dsi_dcs_exit_sleep_mode_multi\0"
	"devm_gpiod_get_optional\0"
	"drm_panel_remove\0"
	"__stack_chk_fail\0"
	"_dev_info\0"
	"mipi_dsi_driver_register_full\0"
	"mipi_dsi_dcs_enter_sleep_mode_multi\0"
	"_dev_err\0"
	"mipi_dsi_dcs_set_display_off_multi\0"
	"mipi_dsi_detach\0"
	"drm_connector_set_orientation_from_panel\0"
	"drm_mode_duplicate\0"
	"drm_mode_set_name\0"
	"mipi_dsi_driver_unregister\0"
	"_dev_warn\0"
	"drm_panel_init\0"
	"of_drm_get_panel_orientation\0"
	"mipi_dsi_dcs_soft_reset_multi\0"
	"mipi_dsi_dcs_set_display_on_multi\0"
	"__ubsan_handle_load_invalid_value\0"
	"of_device_get_match_data\0"
	"devm_backlight_device_register\0"
	"msleep\0"
	"module_layout\0"
;

MODULE_INFO(depends, "backlight");

MODULE_ALIAS("of:N*T*Cwlk,w280bf036i");
MODULE_ALIAS("of:N*T*Cwlk,w280bf036iC*");
MODULE_ALIAS("of:N*T*Cwlk,wx101bh020i-40z");
MODULE_ALIAS("of:N*T*Cwlk,wx101bh020i-40zC*");

MODULE_INFO(srcversion, "50B9C572248E3B36F8F4B6F");
