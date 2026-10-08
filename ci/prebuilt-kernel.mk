# Reuse the kernel built from this exact device tree and pinned kernel source.
# Headers are still generated from TARGET_KERNEL_SOURCE in the recovery job.
TARGET_FORCE_PREBUILT_KERNEL := true
TARGET_PREBUILT_KERNEL := device/google/coral/ci-kernel/Image.lz4
# A single .dtb holds the already concatenated bundle; AOSP copies it unchanged.
BOARD_PREBUILT_DTBIMAGE_DIR := device/google/coral/ci-kernel/dtb
