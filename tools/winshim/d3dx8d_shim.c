/*
 * d3dx8d.dll replacement for running the MinGW build under Wine (development/test only).
 * Original Project Zero Hour code. Implements exactly the 17 D3DX8 entry points that
 * generalszh.exe imports (objdump -p), on top of the Direct3D 8 interfaces Wine provides.
 * Not a general D3DX implementation; not shipped with the game.
 */
#define COBJMACROS
#define INITGUID
#include <windows.h>
#include <d3d8.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

typedef struct { float m[4][4]; } MAT;
typedef struct { float x, y, z; } V3;
typedef struct { float x, y, z, w; } V4;

/* ---------------------------------------------------------------- math */
__declspec(dllexport) MAT* WINAPI D3DXMatrixMultiply(MAT *o, const MAT *a, const MAT *b)
{
    MAT t; int i, j, k;
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) {
        float s = 0; for (k = 0; k < 4; k++) s += a->m[i][k] * b->m[k][j];
        t.m[i][j] = s;
    }
    *o = t; return o;
}
__declspec(dllexport) MAT* WINAPI D3DXMatrixTranspose(MAT *o, const MAT *a)
{
    MAT t; int i, j; for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) t.m[i][j] = a->m[j][i];
    *o = t; return o;
}
__declspec(dllexport) MAT* WINAPI D3DXMatrixScaling(MAT *o, float x, float y, float z)
{
    memset(o, 0, sizeof *o); o->m[0][0] = x; o->m[1][1] = y; o->m[2][2] = z; o->m[3][3] = 1; return o;
}
__declspec(dllexport) MAT* WINAPI D3DXMatrixTranslation(MAT *o, float x, float y, float z)
{
    memset(o, 0, sizeof *o); o->m[0][0] = o->m[1][1] = o->m[2][2] = o->m[3][3] = 1;
    o->m[3][0] = x; o->m[3][1] = y; o->m[3][2] = z; return o;
}
__declspec(dllexport) MAT* WINAPI D3DXMatrixRotationZ(MAT *o, float a)
{
    float c = cosf(a), s = sinf(a);
    memset(o, 0, sizeof *o); o->m[0][0] = c; o->m[0][1] = s; o->m[1][0] = -s; o->m[1][1] = c;
    o->m[2][2] = o->m[3][3] = 1; return o;
}
__declspec(dllexport) MAT* WINAPI D3DXMatrixInverse(MAT *o, float *det, const MAT *a)
{
    /* Gauss-Jordan on a 4x8 augmented matrix */
    float w[4][8]; int i, j, k; float d = 1;
    for (i = 0; i < 4; i++) for (j = 0; j < 8; j++) w[i][j] = j < 4 ? a->m[i][j] : (j - 4 == i);
    for (i = 0; i < 4; i++) {
        int p = i; for (k = i + 1; k < 4; k++) if (fabsf(w[k][i]) > fabsf(w[p][i])) p = k;
        if (fabsf(w[p][i]) < 1e-12f) return NULL;
        if (p != i) { for (j = 0; j < 8; j++) { float t = w[i][j]; w[i][j] = w[p][j]; w[p][j] = t; } d = -d; }
        d *= w[i][i];
        { float inv = 1.0f / w[i][i]; for (j = 0; j < 8; j++) w[i][j] *= inv; }
        for (k = 0; k < 4; k++) if (k != i) { float f = w[k][i]; for (j = 0; j < 8; j++) w[k][j] -= f * w[i][j]; }
    }
    if (det) *det = d;
    for (i = 0; i < 4; i++) for (j = 0; j < 4; j++) o->m[i][j] = w[i][j + 4];
    return o;
}
__declspec(dllexport) V4* WINAPI D3DXVec3Transform(V4 *o, const V3 *v, const MAT *m)
{
    V4 t;
    t.x = v->x * m->m[0][0] + v->y * m->m[1][0] + v->z * m->m[2][0] + m->m[3][0];
    t.y = v->x * m->m[0][1] + v->y * m->m[1][1] + v->z * m->m[2][1] + m->m[3][1];
    t.z = v->x * m->m[0][2] + v->y * m->m[1][2] + v->z * m->m[2][2] + m->m[3][2];
    t.w = v->x * m->m[0][3] + v->y * m->m[1][3] + v->z * m->m[2][3] + m->m[3][3];
    *o = t; return o;
}
__declspec(dllexport) V4* WINAPI D3DXVec4Transform(V4 *o, const V4 *v, const MAT *m)
{
    V4 t;
    t.x = v->x * m->m[0][0] + v->y * m->m[1][0] + v->z * m->m[2][0] + v->w * m->m[3][0];
    t.y = v->x * m->m[0][1] + v->y * m->m[1][1] + v->z * m->m[2][1] + v->w * m->m[3][1];
    t.z = v->x * m->m[0][2] + v->y * m->m[1][2] + v->z * m->m[2][2] + v->w * m->m[3][2];
    t.w = v->x * m->m[0][3] + v->y * m->m[1][3] + v->z * m->m[2][3] + v->w * m->m[3][3];
    *o = t; return o;
}

/* ---------------------------------------------------------------- misc */
__declspec(dllexport) UINT WINAPI D3DXGetFVFVertexSize(DWORD fvf)
{
    UINT s = 0, i, n;
    switch (fvf & D3DFVF_POSITION_MASK) {
        case D3DFVF_XYZ: s = 12; break; case D3DFVF_XYZRHW: s = 16; break;
        case D3DFVF_XYZB1: s = 16; break; case D3DFVF_XYZB2: s = 20; break; case D3DFVF_XYZB3: s = 24; break;
        case D3DFVF_XYZB4: s = 28; break; case D3DFVF_XYZB5: s = 32; break;
    }
    if (fvf & D3DFVF_NORMAL) s += 12;
    if (fvf & D3DFVF_PSIZE) s += 4;
    if (fvf & D3DFVF_DIFFUSE) s += 4;
    if (fvf & D3DFVF_SPECULAR) s += 4;
    n = (fvf & D3DFVF_TEXCOUNT_MASK) >> D3DFVF_TEXCOUNT_SHIFT;
    for (i = 0; i < n; i++) {
        switch ((fvf >> (16 + i * 2)) & 3) { case 0: s += 8; break; case 1: s += 12; break; case 2: s += 16; break; case 3: s += 4; break; }
    }
    return s;
}
__declspec(dllexport) HRESULT WINAPI D3DXGetErrorStringA(HRESULT hr, char *buf, UINT len)
{
    if (buf && len) { _snprintf(buf, len, "D3D error 0x%08lx", (unsigned long)hr); buf[len - 1] = 0; }
    return S_OK;
}

/* ---------------------------------------------------------------- textures */
static UINT levels_for(UINT w, UINT h, UINT lv)
{
    UINT n = 1; if (lv) return lv;
    while (w > 1 || h > 1) { w = w > 1 ? w / 2 : 1; h = h > 1 ? h / 2 : 1; n++; }
    return n;
}
__declspec(dllexport) HRESULT WINAPI D3DXCreateTexture(IDirect3DDevice8 *dev, UINT w, UINT h, UINT lv, DWORD usage,
    D3DFORMAT fmt, D3DPOOL pool, IDirect3DTexture8 **out)
{
    if (!dev || !out) return D3DERR_INVALIDCALL;
    if (!w) w = 256; if (!h) h = 256;
    return IDirect3DDevice8_CreateTexture(dev, w, h, levels_for(w, h, lv), usage, fmt, pool, out);
}
__declspec(dllexport) HRESULT WINAPI D3DXCreateCubeTexture(IDirect3DDevice8 *dev, UINT size, UINT lv, DWORD usage,
    D3DFORMAT fmt, D3DPOOL pool, IDirect3DCubeTexture8 **out)
{
    if (!dev || !out) return D3DERR_INVALIDCALL;
    if (!size) size = 256;
    return IDirect3DDevice8_CreateCubeTexture(dev, size, levels_for(size, size, lv), usage, fmt, pool, out);
}
__declspec(dllexport) HRESULT WINAPI D3DXCreateVolumeTexture(IDirect3DDevice8 *dev, UINT w, UINT h, UINT d, UINT lv,
    DWORD usage, D3DFORMAT fmt, D3DPOOL pool, IDirect3DVolumeTexture8 **out)
{
    if (!dev || !out) return D3DERR_INVALIDCALL;
    return IDirect3DDevice8_CreateVolumeTexture(dev, w, h, d, lv ? lv : 1, usage, fmt, pool, out);
}
__declspec(dllexport) HRESULT WINAPI D3DXCreateTextureFromFileExA(IDirect3DDevice8 *dev, const char *file, UINT w, UINT h,
    UINT lv, DWORD usage, D3DFORMAT fmt, D3DPOOL pool, DWORD filter, DWORD mip, DWORD key, void *info, void *pal,
    IDirect3DTexture8 **out)
{
    /* The engine loads its textures itself; file loading through D3DX is not supported in the shim. */
    if (out) *out = NULL;
    return D3DERR_NOTAVAILABLE;
}

static int bpp(D3DFORMAT f)
{
    switch (f) {
        case D3DFMT_A8R8G8B8: case D3DFMT_X8R8G8B8: return 4;
        case D3DFMT_R5G6B5: case D3DFMT_X1R5G5B5: case D3DFMT_A1R5G5B5: case D3DFMT_A4R4G4B4: return 2;
        case D3DFMT_A8: case D3DFMT_L8: case D3DFMT_P8: return 1;
        case D3DFMT_R8G8B8: return 3;
        default: return 0;
    }
}
static DWORD read_argb(const BYTE *p, D3DFORMAT f)
{
    WORD v;
    switch (f) {
        case D3DFMT_A8R8G8B8: return *(const DWORD *)p;
        case D3DFMT_X8R8G8B8: return *(const DWORD *)p | 0xFF000000u;
        case D3DFMT_R8G8B8: return 0xFF000000u | (p[2] << 16) | (p[1] << 8) | p[0];
        case D3DFMT_R5G6B5: v = *(const WORD *)p;
            return 0xFF000000u | (((v >> 11) & 31) * 255 / 31) << 16 | (((v >> 5) & 63) * 255 / 63) << 8 | ((v & 31) * 255 / 31);
        case D3DFMT_X1R5G5B5: case D3DFMT_A1R5G5B5: v = *(const WORD *)p;
            return ((f == D3DFMT_A1R5G5B5 && !(v & 0x8000)) ? 0 : 0xFF000000u) |
                   (((v >> 10) & 31) * 255 / 31) << 16 | (((v >> 5) & 31) * 255 / 31) << 8 | ((v & 31) * 255 / 31);
        case D3DFMT_A4R4G4B4: v = *(const WORD *)p;
            return (((v >> 12) & 15) * 17u) << 24 | (((v >> 8) & 15) * 17) << 16 | (((v >> 4) & 15) * 17) << 8 | ((v & 15) * 17);
        case D3DFMT_A8: return (DWORD)p[0] << 24;
        case D3DFMT_L8: return 0xFF000000u | p[0] * 0x010101u;
        default: return 0xFFFF00FFu;
    }
}
static void write_argb(BYTE *p, D3DFORMAT f, DWORD c)
{
    DWORD a = c >> 24, r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255;
    switch (f) {
        case D3DFMT_A8R8G8B8: case D3DFMT_X8R8G8B8: *(DWORD *)p = c; break;
        case D3DFMT_R8G8B8: p[0] = (BYTE)b; p[1] = (BYTE)g; p[2] = (BYTE)r; break;
        case D3DFMT_R5G6B5: *(WORD *)p = (WORD)(((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)); break;
        case D3DFMT_X1R5G5B5: case D3DFMT_A1R5G5B5:
            *(WORD *)p = (WORD)(((a >= 128) << 15) | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)); break;
        case D3DFMT_A4R4G4B4: *(WORD *)p = (WORD)(((a >> 4) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)); break;
        case D3DFMT_A8: p[0] = (BYTE)a; break;
        case D3DFMT_L8: p[0] = (BYTE)((r * 77 + g * 151 + b * 28) >> 8); break;
        default: break;
    }
}

__declspec(dllexport) HRESULT WINAPI D3DXLoadSurfaceFromSurface(IDirect3DSurface8 *dst, const PALETTEENTRY *dpal,
    const RECT *drc, IDirect3DSurface8 *src, const PALETTEENTRY *spal, const RECT *src_rc, DWORD filter, DWORD key)
{
    D3DSURFACE_DESC dd, sd; D3DLOCKED_RECT dl, sl; RECT dr, sr; int x, y, dw, dh, sw, sh, db, sbp;
    if (!dst || !src) return D3DERR_INVALIDCALL;
    IDirect3DSurface8_GetDesc(dst, &dd); IDirect3DSurface8_GetDesc(src, &sd);
    if (drc) dr = *drc; else { dr.left = dr.top = 0; dr.right = dd.Width; dr.bottom = dd.Height; }
    if (src_rc) sr = *src_rc; else { sr.left = sr.top = 0; sr.right = sd.Width; sr.bottom = sd.Height; }
    db = bpp(dd.Format); sbp = bpp(sd.Format);
    if (!db || !sbp) return D3DERR_NOTAVAILABLE; /* compressed formats: not supported by the shim */
    if (FAILED(IDirect3DSurface8_LockRect(src, &sl, NULL, D3DLOCK_READONLY))) return D3DERR_INVALIDCALL;
    if (FAILED(IDirect3DSurface8_LockRect(dst, &dl, NULL, 0))) { IDirect3DSurface8_UnlockRect(src); return D3DERR_INVALIDCALL; }
    dw = dr.right - dr.left; dh = dr.bottom - dr.top; sw = sr.right - sr.left; sh = sr.bottom - sr.top;
    for (y = 0; y < dh; y++) {
        for (x = 0; x < dw; x++) {
            int sx0 = sr.left + x * sw / dw, sy0 = sr.top + y * sh / dh;
            DWORD c;
            if (dw * 2 == sw && dh * 2 == sh) { /* box filter for exact 2:1 (mip generation) */
                DWORD q[4]; int k, ch; DWORD out = 0;
                q[0] = read_argb((BYTE *)sl.pBits + sy0 * sl.Pitch + sx0 * sbp, sd.Format);
                q[1] = read_argb((BYTE *)sl.pBits + sy0 * sl.Pitch + (sx0 + 1) * sbp, sd.Format);
                q[2] = read_argb((BYTE *)sl.pBits + (sy0 + 1) * sl.Pitch + sx0 * sbp, sd.Format);
                q[3] = read_argb((BYTE *)sl.pBits + (sy0 + 1) * sl.Pitch + (sx0 + 1) * sbp, sd.Format);
                for (ch = 0; ch < 32; ch += 8) { DWORD s = 0; for (k = 0; k < 4; k++) s += (q[k] >> ch) & 255; out |= ((s + 2) / 4) << ch; }
                c = out;
            } else {
                c = read_argb((BYTE *)sl.pBits + sy0 * sl.Pitch + sx0 * sbp, sd.Format);
            }
            write_argb((BYTE *)dl.pBits + (dr.top + y) * dl.Pitch + (dr.left + x) * db, dd.Format, c);
        }
    }
    IDirect3DSurface8_UnlockRect(dst); IDirect3DSurface8_UnlockRect(src);
    return D3D_OK;
}

__declspec(dllexport) HRESULT WINAPI D3DXFilterTexture(IDirect3DBaseTexture8 *tex, const PALETTEENTRY *pal, UINT src_level, DWORD filter)
{
    IDirect3DTexture8 *t = NULL; UINT n, i;
    if (!tex) return D3DERR_INVALIDCALL;
    if (IDirect3DBaseTexture8_GetType(tex) != D3DRTYPE_TEXTURE) return D3D_OK; /* cube/volume: leave as is */
    t = (IDirect3DTexture8 *)tex;
    n = IDirect3DTexture8_GetLevelCount(t);
    for (i = src_level + 1; i < n; i++) {
        IDirect3DSurface8 *a = NULL, *b = NULL;
        if (SUCCEEDED(IDirect3DTexture8_GetSurfaceLevel(t, i - 1, &a)) && SUCCEEDED(IDirect3DTexture8_GetSurfaceLevel(t, i, &b)))
            D3DXLoadSurfaceFromSurface(b, NULL, NULL, a, NULL, NULL, filter, 0);
        if (a) IDirect3DSurface8_Release(a);
        if (b) IDirect3DSurface8_Release(b);
    }
    return D3D_OK;
}

/* ---------------------------------------------------------------- shaders: forward to Wine's d3dx9 assembler */
typedef HRESULT (WINAPI *PFN_ASM9)(const char *, UINT, const void *, void *, DWORD, void **, void **);
__declspec(dllexport) HRESULT WINAPI D3DXAssembleShader(const void *src, UINT len, DWORD flags, void **constants,
    void **compiled, void **errors)
{
    static PFN_ASM9 fn = NULL; HMODULE m;
    if (constants) *constants = NULL;
    if (!fn) {
        m = LoadLibraryA("d3dx9_36.dll");
        if (m) fn = (PFN_ASM9)GetProcAddress(m, "D3DXAssembleShader");
    }
    if (!fn) { if (compiled) *compiled = NULL; if (errors) *errors = NULL; return E_FAIL; }
    return fn((const char *)src, len, NULL, NULL, 0, compiled, errors);
}
