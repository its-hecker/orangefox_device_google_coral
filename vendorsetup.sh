#!/usr/bin/env bash
export FOX_BUILD_DEVICE=coral
export FOX_AB_DEVICE=1
export OF_DISABLE_MIUI_SPECIFIC_FEATURES=1
# Coral uses Qualcomm 4.0/default and Citadel 4.1/strongbox together.
# The qcom_decrypt 4.x trigger starts both when the vendor manifest is unavailable.
export OF_DEFAULT_KEYMASTER_VERSION=4.x
export FOX_VARIANT=Unofficial
export FOX_MAINTAINER=its-hecker
# First bring-up produces a temporary-boot image only.
export FOX_DISABLE_UPDATEZIP=1
