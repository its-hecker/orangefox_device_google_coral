// SPDX-License-Identifier: GPL-3.0-or-later
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>

struct Surface { int width, height; unsigned char* data; };
using gr_surface = Surface*;
struct Image {
    Surface surface;
    unsigned char* mapping = nullptr;
    size_t mapping_size = 0;
    explicit Image(int w, int h) : surface{w, h, nullptr} {
        const size_t page = sysconf(_SC_PAGESIZE);
        const size_t bytes = size_t(w) * h * 4;
        const size_t span = (bytes + page - 1) / page * page;
        auto* memory = static_cast<unsigned char*>(mmap(nullptr, span + page,
            PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
        if (memory == MAP_FAILED || mprotect(memory + span, page, PROT_NONE)) std::abort();
        mapping = memory;
        mapping_size = span + page;
        surface.data = memory + span - bytes;
    }
    ~Image() { munmap(mapping, mapping_size); }
    gr_surface GetResource() { return &surface; }
    int GetWidth() { return surface.width; }
    int GetHeight() { return surface.height; }
};
struct Label {
    void GetCurrentBounds(int& w, int& h) { w = h = 0; }
    void SetRenderPos(int, int) {}
    int Render() { return 0; }
};
struct Color { unsigned char red = 0, green = 0, blue = 0, alpha = 255; };
constexpr int TOP_LEFT = 0;
void gr_color(unsigned char, unsigned char, unsigned char, unsigned char) {}
void gr_fill(int, int, int, int) {}
void gr_draw_rect(int, int, int, int, int) {}
void gr_textEx_scaleW(int, int, const char*, void*, int, int, int) {}
int gr_get_width(gr_surface s) { return s->width; }
int gr_get_height(gr_surface s) { return s->height; }
struct Blit { int w, h, x, y; };
std::vector<Blit> blits;
void gr_blit(gr_surface s, int sx, int sy, int w, int h, int dx, int dy) {
    volatile unsigned char pixel;
    for (int y = sy; y < sy + h; ++y)
        for (int x = sx; x < sx + w; ++x)
            pixel = s->data[(size_t(y) * s->width + x) * 4];
    (void)pixel;
    assert(sx >= 0 && sy >= 0 && sx + w <= s->width && sy + h <= s->height);
    blits.push_back({w, h, dx, dy});
}
struct Font { void* GetResource() { return nullptr; } };
struct GUISliderValue {
    int mRenderX=0, mRenderY=0, mRenderW=1312, mRenderH=0;
    int mSliderX=0, mSliderY=0, mSliderW=128, mSliderH=152;
    int mFontHeight=0, mLabelW=0, mLinePadding=10;
    int mActionX=0, mActionY=0, mActionW=0, mActionH=0;
    int mLineW=0, mLineH=6, mLineX=0, mLineY=0;
    int mValuePct=50, mValue=50, mPadding=0;
    bool mShowCurr=false, mShowRange=false, mDragging=false, mRendered=false;
    char* mValueStr=nullptr;
    std::string mMinStr, mMaxStr;
    Label* mLabel=nullptr; Font* mFont=nullptr;
    Image* mBackgroundImage=nullptr; Image* mHandleImage=nullptr; Image* mHandleHoverImage=nullptr;
    Color mLineColor, mSliderColor, mTextColor, mFocusColor;
    bool isConditionTrue() { return true; }
    bool HasFocus() { return false; }
    int measureText(const char*) { return 0; }
    int SetRenderPos(int x, int y, int w=0, int h=0);
    int Render();
};
#include "slider_methods.inc"
int main(int argc, char** argv) {
    assert(argc == 2);
    const std::string name = argv[1];
    const bool uniform = name == "uniform";
    const int image_size = uniform ? 96 : 128;
    Image handle(image_size, image_size);
    Image hover(160, 160);
    GUISliderValue slider;
    slider.mHandleImage = &handle;
    if (uniform) slider.mSliderW = slider.mSliderH = 96;
    if (name == "wide") { slider.mSliderW = 152; slider.mSliderH = 128; }
    if (name == "hover") { slider.mHandleHoverImage = &hover; slider.mDragging = true; }
    if (name == "left_edge") slider.mValuePct = 0;
    if (name == "fallback") slider.mHandleImage = nullptr;
    slider.SetRenderPos(name == "left_edge" ? -200 : 117, 600, 1312);
    slider.Render();
    if (name == "fallback") {
        assert(blits.empty());
        assert(slider.mSliderW == 128 && slider.mSliderH == 152);
    } else {
        assert(slider.mSliderW == image_size && slider.mSliderH == image_size);
        assert(slider.mActionH == image_size);
        assert(blits.size() == 1);
        const Blit& blit = blits.back();
        const int draw_size = name == "hover" ? 160 : image_size;
        assert(blit.w == draw_size && blit.h == draw_size);
        const int position = slider.mLineX + slider.mValuePct * (slider.mLineW - slider.mSliderW) / 100;
        assert(blit.x + draw_size / 2 == position + slider.mSliderW / 2);
        assert(blit.y + draw_size / 2 == slider.mLineY + slider.mLineH / 2);
        if (name == "left_edge") assert(blit.x < 0);
    }
    std::printf("Slider rendering passed: %s\n", name.c_str());
}
