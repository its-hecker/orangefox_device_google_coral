# Additional recovery prebuilt

`system/lib64/hw/android.hardware.gatekeeper@1.0-impl-qti.so` is the
64-bit Coral vendor Gatekeeper implementation. The existing QTI service loads
it through `HIDL_FETCH_IGatekeeper`; linking the service alone does not include
this library. Recovery packages it under `/system/lib64/hw` so the passthrough
loader can find it while the vendor partition is unmounted.

Source: [TheMuppets/proprietary_vendor_google_coral](https://github.com/TheMuppets/proprietary_vendor_google_coral/blob/34936469a30bf1da32769e9ce1632fa51322f15a/proprietary/vendor/lib64/hw/android.hardware.gatekeeper%401.0-impl-qti.so),
commit `34936469a30bf1da32769e9ce1632fa51322f15a`, path
`proprietary/vendor/lib64/hw/android.hardware.gatekeeper@1.0-impl-qti.so`.

- Git blob: `848936e6d1ad9013116ffef986b67b43bdf70563`
- SHA-256: `01c6c290337ad14d272c0e97611edf064b29a1b4e399132b95ca2e3a725f8028`

The binary is unchanged. Its vendor origin and existing proprietary licensing
remain applicable; the device tree's source-code license does not relicense it.
