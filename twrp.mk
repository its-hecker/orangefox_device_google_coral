BOARD_USES_QCOM_FBE_DECRYPTION := true
DISABLE_ARTIFACT_PATH_REQUIREMENTS := true
# Match the tested Infinity Android 17 system's Keymaster version metadata.
# This is not a claim that the Android 12.1 recovery has newer platform fixes.
CORAL_RECOVERY_OS_VERSION := 17
PLATFORM_SECURITY_PATCH := 2026-09-01
# The 12.1 build uses PLATFORM_VERSION_LAST_STABLE for the boot header; changing
# PLATFORM_VERSION alone does not change its encoded OS version.
BOARD_MKBOOTIMG_ARGS += --os_version $(CORAL_RECOVERY_OS_VERSION)

TARGET_RECOVERY_TWRP_LIB := \
    librecovery_twrp_coral \
    libnos_citadel_for_recovery \
    libnos_for_recovery \
    liblog \
    libbootloader_message \
    libfstab \
    libext4_utils

# TWRP
TW_THEME := portrait_hdpi
BOARD_SUPPRESS_SECURE_ERASE := true
TARGET_RECOVERY_QCOM_RTC_FIX := true
TW_INPUT_BLACKLIST := "hbtp_vm"
# Coral S6E3HC2 panel: qcom,mdss-dsi-bl-max-level = <0x3ff>.
TW_BRIGHTNESS_PATH := "/sys/class/backlight/panel0-backlight/brightness"
TW_MAX_BRIGHTNESS := 1023
TW_DEFAULT_BRIGHTNESS := 512
TW_INCLUDE_CRYPTO := true
AB_OTA_UPDATER := true
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_RECOVERY_ADDITIONAL_RELINK_BINARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/system/bin/strace
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/system/lib64/android.hardware.authsecret@1.0.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/system/lib64/android.hardware.oemlock@1.0.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/libnos.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/libnosprotos.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/pixelatoms-cpp.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/libnos_datagram_citadel.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/libnos_client_citadel.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/nos_app_avb.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/nos_app_keymaster.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib64/nos_app_weaver.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/system/lib64/pixelpowerstats_provider_aidl_interface-cpp.so
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += $(OUT_DIR)/target/product/$(PRODUCT_HARDWARE)/vendor/lib/hw/bootctrl.msmnile.so
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
#TW_EXCLUDE_MTP := true
TW_USE_TOOLBOX := true
#TARGET_RECOVERY_PIXEL_FORMAT := ABGR_8888
TW_NO_HAPTICS := true
TW_INCLUDE_REPACKTOOLS := true
#TW_EXTRA_LANGUAGES := true
TW_INCLUDE_RESETPROP := true
TW_USE_FSCRYPT_POLICY := 1
TW_LOAD_VENDOR_MODULES := "ftm5.ko"
