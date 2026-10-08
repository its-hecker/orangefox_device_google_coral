#!/usr/bin/env bash
export FOX_BUILD_DEVICE=coral
export FOX_AB_DEVICE=1
export OF_DISABLE_MIUI_SPECIFIC_FEATURES=1
export OF_DEFAULT_KEYMASTER_VERSION=4.1
export FOX_VARIANT=Unofficial
export FOX_MAINTAINER=its-hecker
# First bring-up produces a temporary-boot image only.
export FOX_DISABLE_UPDATEZIP=1
