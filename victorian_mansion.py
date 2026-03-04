"""
ASHFORD MANOR  –  Victorian Malikane Prototipi
===============================================
Mimari Hiyerarşi:
  BODRUM   → Mutfak, Kiler, Çamaşırhane, Kömürlük, Hizmetli Yemek
  ZEMİN    → Giriş Holü, Drawing Room, Dining Room, Kütüphane, Morning Room
  1. KAT   → Üst Koridor, Master Bedroom, Giyinme Odası, Çocuk Odaları, Banyo
  ÇATI     → Hizmetli Odaları (3), Depo
  ÖZEL     → Kule, Gizli Geçit

AGENT.MD uyumlu: frame_mul, gc.disable, data-driven, Z-layer, LERP kamera
Kontroller: A/D yürü | W/Space zıpla | E etkileşim | F12 debug | ESC çık
"""

import pygame, sys, math, gc, random

# ══════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════
SW, SH   = 1280, 720
FPS      = 60
TITLE    = "Ashford Manor  –  1887"
PW, PH   = 22, 42
P_SPEED  = 200.0
JUMP_V   = -560.0
GRAV     = 1400.0
CAM_LX   = 0.09
CAM_LY   = 0.09
INTER_D  = 76

# ── Victorian Renk Paleti ─────────────────────────────
# Taş / harç
S0=(14,11,9); S1=(30,25,20); S2=(48,40,32); S3=(68,56,44); S4=(95,80,62); S5=(125,105,82)
# Ahşap
W0=(22,14,6); W1=(42,28,12); W2=(65,43,18); W3=(92,62,26); W4=(128,90,38); W5=(165,120,55)
# Bordo
BORDO_D=(55,8,8);   BORDO_M=(100,18,18); BORDO_L=(145,35,35)
# Zümrüt yeşili
ZUMRUT_D=(8,45,28); ZUMRUT_M=(18,80,50); ZUMRUT_L=(35,120,75)
# Lacivert
LACI_D=(10,15,45);  LACI_M=(18,28,80);   LACI_L=(35,55,130)
# Çiçekli duvar kağıdı renkleri
WP_BG=(32,20,28); WP_FLOWER=(90,55,70); WP_LEAF=(30,60,38)
# Mermer
MRB_W=(200,195,185); MRB_G=(160,155,145); MRB_D=(100,95,88)
# Demir
IRON=(55,55,60); IRON_L=(80,80,85)
# Alev
FL_A=(255,210,80); FL_B=(255,140,30); FL_C=(200,60,10)
# Fayans (mutfak)
TILE_W=(210,205,195); TILE_G=(160,155,148)
# Siyah-beyaz karo
KARO_W=(210,210,200); KARO_B=(25,22,18)
# UI
C_HINT=(210,190,110); C_UI=(195,175,140); C_DBG=(255,200,50)
# Oyuncu
P_SKIN=(200,175,145); P_COAT=(28,22,18); P_HAIR=(20,14,8)

gc.collect(); gc.disable()

pygame.init()
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption(TITLE)
clock  = pygame.time.Clock()
F_SM   = pygame.font.SysFont("georgia", 14)
F_MD   = pygame.font.SysFont("georgia", 19, bold=True)
F_IT   = pygame.font.SysFont("georgia", 16, italic=True)
rng    = random.Random(1337)
_ft    = 0.0

# ══════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════
def lc(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def grad(surf, r, ct, cb):
    if r.h<=0: return
    for y in range(r.h):
        pygame.draw.line(surf, lc(ct,cb,y/r.h), (r.x,r.y+y),(r.x+r.w,r.y+y))

def alpha_rect(surf, col, a, r):
    s=pygame.Surface((max(1,r.w),max(1,r.h)),pygame.SRCALPHA)
    s.fill((*col,a)); surf.blit(s,(r.x,r.y))

def clamp(v,lo,hi): return max(lo,min(v,hi))

# ══════════════════════════════════════════════════════
#  ALEV PARTİKÜL HAVUZU
# ══════════════════════════════════════════════════════
class _FP:
    __slots__=("x","y","vx","vy","life","ml","r","active")
    def __init__(self): self.active=False

_fp_pool=[_FP() for _ in range(100)]

def _spawn_flame(wx,wy,sp=5):
    for p in _fp_pool:
        if not p.active:
            p.x=wx+rng.uniform(-sp,sp); p.y=wy
            p.vx=rng.uniform(-10,10); p.vy=rng.uniform(-55,-100)
            p.ml=rng.uniform(0.22,0.50); p.life=p.ml
            p.r=rng.randint(3,6); p.active=True; return

def _draw_flames(surf,dt,cx,cy,sources):
    for (wx,wy,sp) in sources:
        if rng.random()<0.55: _spawn_flame(wx,wy,sp)
    for p in _fp_pool:
        if not p.active: continue
        p.life-=dt
        if p.life<=0: p.active=False; continue
        p.x+=p.vx*dt; p.y+=p.vy*dt; p.vy+=38*dt
        t=1-p.life/p.ml; col=lc(FL_A,lc(FL_B,FL_C,t),t)
        r=max(1,int(p.r*(1-t*0.5)))
        sx,sy=int(p.x-cx),int(p.y-cy)
        alpha_rect(surf,col,int(215*(1-t)),pygame.Rect(sx-r,sy-r,r*2,r*2))

# ══════════════════════════════════════════════════════
#  ARKAPLAN ÇİZİM SİSTEMİ
#  Her oda kendi wall_style'ına göre render edilir
# ══════════════════════════════════════════════════════
def draw_room_bg(surf, room, cx, cy):
    style = room.get("wall_style","stone")

    if style == "checkerboard":
        # Giriş holü: siyah-beyaz karo zemin (sadece alt yarı)
        # Üst: koyu ahşap panel + taş
        draw_stone_wall_bg(surf, room, cx, cy)
        # Karo bölgesi ekranda zemin platformun üstünde çizilir
        # (platforma bakıp oradan hesapla)
        floor_y = room.get("floor_world_y", 540)
        sy_floor = int(floor_y - cy)
        k = 40
        for row in range(-1, (SH - sy_floor)//k + 2):
            for col in range(-1, SW//k + 2):
                cx2 = col*k - int(cx)%k
                cy2 = sy_floor + row*k
                color = KARO_W if (row+col)%2==0 else KARO_B
                pygame.draw.rect(surf, color, (cx2,cy2,k,k))
                pygame.draw.rect(surf, (80,75,65), (cx2,cy2,k,k),1)

    elif style == "wallpaper_floral":
        # Dining/Drawing room: çiçekli duvar kağıdı
        grad(surf, pygame.Rect(0,0,SW,SH), WP_BG, lc(WP_BG,(10,8,6),0.4))
        # Duvar kağıdı deseni
        gap = 38
        for row in range(-1, SH//gap+2):
            for col in range(-1, SW//gap+2):
                wx2 = col*gap - int(cx)%gap
                wy2 = row*gap - int(cy)%gap
                # Çiçek merkezi
                pygame.draw.circle(surf,WP_FLOWER,(wx2+gap//2,wy2+gap//2),6)
                pygame.draw.circle(surf,lc(WP_FLOWER,(200,150,170),0.4),(wx2+gap//2,wy2+gap//2),3)
                # Yapraklar
                for a in range(4):
                    ang = a*math.pi/2
                    lx = wx2+gap//2+int(math.cos(ang)*11)
                    ly = wy2+gap//2+int(math.sin(ang)*11)
                    pygame.draw.line(surf,WP_LEAF,(wx2+gap//2,wy2+gap//2),(lx,ly),2)
        # Lambri alt panel
        _draw_lambri(surf, room, cx, cy)

    elif style == "dark_wood":
        # Kütüphane / çalışma: koyu ahşap panel tavan yüksekliğine
        grad(surf, pygame.Rect(0,0,SW,SH), W1, W0)
        panel_w = 55
        off = int(cx)%panel_w
        for px in range(-off, SW, panel_w):
            pygame.draw.rect(surf,(35,22,8),(px,0,2,SH))
            pygame.draw.rect(surf,(55,38,16),(px+2,0,panel_w-4,SH))
        # Yatay çıta
        for hy in [120, 280, 420]:
            sy2 = hy - int(cy)
            if 0<=sy2<SH:
                pygame.draw.rect(surf,W4,(0,sy2,SW,8))
                pygame.draw.rect(surf,W5,(0,sy2,SW,2))

    elif style == "servants":
        # Hizmetli alanları: sade beyaz badana + taş
        grad(surf, pygame.Rect(0,0,SW,SH),(185,178,165),(145,138,125))
        # İnce taş çizgi
        bs=(44,22); off_x=int(cx)%bs[0]
        for row in range(SH//bs[1]+2):
            off2=(row%2)*(bs[0]//2)
            sy2=row*bs[1]-int(cy)%bs[1]
            for col in range(-1,SW//bs[0]+2):
                bx=col*bs[0]-off_x-off2
                pygame.draw.rect(surf,(120,115,108),(bx,sy2,bs[0],bs[1]),1)

    elif style == "kitchen":
        # Mutfak: taş zemin, yarıya kadar fayans
        grad(surf, pygame.Rect(0,0,SW,SH),(55,48,40),(35,30,25))
        # Fayans (üst yarı)
        tile_h = SH//2
        ts=32
        for row in range(-1,tile_h//ts+2):
            for col in range(-1,SW//ts+2):
                tx=col*ts-int(cx)%ts; ty=row*ts
                c=TILE_W if (row+col)%2==0 else TILE_G
                pygame.draw.rect(surf,c,(tx,ty,ts,ts))
                pygame.draw.rect(surf,(160,155,148),(tx,ty,ts,ts),1)
        # Alt taş zemin
        ts2=48
        for row in range(-1,(SH-tile_h)//ts2+2):
            off3=(row%2)*(ts2//2)
            sy2=tile_h+row*ts2
            for col in range(-1,SW//ts2+2):
                bx=col*ts2-int(cx)%ts2-off3
                pygame.draw.rect(surf,(60,52,44),(bx,sy2,ts2,ts2))
                pygame.draw.rect(surf,(40,34,28),(bx,sy2,ts2,ts2),1)

    elif style == "cellar":
        # Bodrum: ham taş, rutubetli
        grad(surf, pygame.Rect(0,0,SW,SH),(22,18,14),(12,10,8))
        bs=(60,30)
        for row in range(SH//bs[1]+2):
            off2=(row%2)*(bs[0]//2)
            sy2=row*bs[1]-int(cy)%bs[1]
            for col in range(-1,SW//bs[0]+2):
                bx=col*bs[0]-int(cx)%bs[0]-off2
                pygame.draw.rect(surf,lc((28,24,20),(15,12,10),rng.random()*0.3),
                                 (bx,sy2,bs[0],bs[1]))
                pygame.draw.rect(surf,(10,8,6),(bx,sy2,bs[0],bs[1]),1)

    else:  # stone (default)
        draw_stone_wall_bg(surf, room, cx, cy)

    # Tavan kornişi (ortak)
    _draw_cornice(surf, room, cx, cy)

def draw_stone_wall_bg(surf, room, cx, cy):
    wt=room.get("wall_top",S1); wb=room.get("wall_bot",S2)
    grad(surf, pygame.Rect(0,0,SW,SH), wt, wb)
    bs=room.get("block_size",(52,26))
    for row in range(SH//bs[1]+2):
        off=(row%2)*(bs[0]//2)
        sy2=row*bs[1]-int(cy)%bs[1]
        for col in range(-1,SW//bs[0]+2):
            bx=col*bs[0]-int(cx)%bs[0]-off
            pygame.draw.rect(surf,S0,(bx,sy2,bs[0],bs[1]),1)
    _draw_lambri(surf, room, cx, cy)

def _draw_lambri(surf, room, cx, cy):
    # Ahşap lambri (alt %32)
    lam_y=int(SH*0.68)
    grad(surf,pygame.Rect(0,lam_y,SW,SH-lam_y),W1,W0)
    sw=42
    for sx2 in range(0,SW,sw):
        pygame.draw.line(surf,W0,(sx2,lam_y),(sx2,SH),1)
        pygame.draw.rect(surf,lc(W1,W2,0.3),(sx2+2,lam_y+4,sw-4,SH-lam_y-8),1)
    pygame.draw.rect(surf,W4,(0,lam_y,SW,5))
    pygame.draw.rect(surf,W3,(0,lam_y+5,SW,2))

def _draw_cornice(surf, room, cx, cy):
    style=room.get("wall_style","stone")
    if style in ("servants","kitchen","cellar"): return
    corn_y = 22 - int(cy)%1
    if corn_y >= SH: return
    pygame.draw.rect(surf,S4,(0,corn_y,SW,30))
    # Dişli korniş detayı
    tooth_w=24
    for i in range(0,SW,tooth_w*2):
        pygame.draw.rect(surf,S5,(i,corn_y+4,tooth_w,18))
        pygame.draw.rect(surf,S3,(i+tooth_w,corn_y+4,tooth_w,14))
    pygame.draw.rect(surf,S5,(0,corn_y,SW,3))
    pygame.draw.rect(surf,S2,(0,corn_y+28,SW,3))

# ══════════════════════════════════════════════════════
#  PLATFORM ÇİZİMLERİ
# ══════════════════════════════════════════════════════
def draw_floor(surf,rx,ry,rw,rh,cx,cy,style="wood"):
    sx,sy=rx-int(cx),ry-int(cy)
    if sy>SH or sy+rh<0: return
    if style=="checkerboard":
        k=40; off=int(cx)%k
        for col in range(-1,rw//k+2):
            for row in range(rh//k+2):
                tx=sx+col*k-off; ty=sy+row*k
                c=KARO_W if (col+row)%2==0 else KARO_B
                pygame.draw.rect(surf,c,(tx,ty,k,k))
                pygame.draw.rect(surf,(80,75,65),(tx,ty,k,k),1)
    elif style=="stone":
        grad(surf,pygame.Rect(sx,sy,rw,rh),S3,S1)
        for px in range(sx,sx+rw,60):
            pygame.draw.line(surf,S0,(px,sy),(px,sy+rh),1)
        pygame.draw.rect(surf,S5,(sx,sy,rw,2))
    elif style=="tile":
        ts=32
        for row in range(rh//ts+2):
            for col in range(rw//ts+2):
                tx=sx+col*ts; ty=sy+row*ts
                c=TILE_W if (col+row)%2==0 else TILE_G
                pygame.draw.rect(surf,c,(tx,ty,ts,ts))
                pygame.draw.rect(surf,(140,135,128),(tx,ty,ts,ts),1)
    else:  # wood
        grad(surf,pygame.Rect(sx,sy,rw,rh),W2,W0)
        pl=55; off=int(cx)%pl
        for px in range(sx-off,sx+rw,pl):
            pygame.draw.line(surf,W1,(px,sy),(px,sy+rh),1)
        pygame.draw.rect(surf,W4,(sx,sy,rw,2))

def draw_stone_plat(surf,rx,ry,rw,rh,cx,cy,col_t=S4,col_b=S2):
    sx,sy=rx-int(cx),ry-int(cy)
    if sy>SH or sy+rh<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),col_t,col_b)
    pygame.draw.rect(surf,S5,(sx,sy,rw,3))
    pygame.draw.rect(surf,S0,(sx,sy,rw,rh),1)

def draw_wall_col(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),S3,S1)
    bs=(46,23)
    for row in range(rh//bs[1]+2):
        off=(row%2)*23
        sy2=sy+row*bs[1]
        for col in range(-1,rw//bs[0]+2):
            pygame.draw.rect(surf,S0,(sx+col*bs[0]-off,sy2,bs[0],bs[1]),1)

# ══════════════════════════════════════════════════════
#  MERDİVEN
# ══════════════════════════════════════════════════════
def draw_staircase(surf,stair,cx,cy,near):
    rx,ry,rw,rh=stair["rect"]
    n=stair.get("steps",8); d=stair.get("dir","right")
    sw2=rw//n; sh2=rh//n
    # Basamaklar
    for i in range(n):
        bx=rx+i*sw2 if d=="right" else rx+rw-(i+1)*sw2
        by=ry+rh-(i+1)*sh2
        sx,sy=bx-int(cx),by-int(cy)
        if sy>SH or sx>SW: continue
        grad(surf,pygame.Rect(sx,sy,sw2,sh2),W3,W1)
        pygame.draw.rect(surf,W5,(sx,sy,sw2,3))   # üst kenar
        pygame.draw.rect(surf,W2,(sx,sy,2,sh2))   # yan kenar
        # Dikmeler (korkuluk)
        if i%2==0:
            px2=sx+sw2//2
            pygame.draw.line(surf,W4,(px2,sy),(px2,sy-int(rh*0.45)),2)
            # Süslemeli top
            pygame.draw.circle(surf,W4,(px2,sy-int(rh*0.45)),4)
    # Korkuluk ana rayı
    if d=="right":
        p1=(rx-int(cx), ry+rh-int(cy))
        p2=(rx+rw-int(cx), ry-int(cy))
    else:
        p1=(rx+rw-int(cx), ry+rh-int(cy))
        p2=(rx-int(cx), ry-int(cy))
    pygame.draw.line(surf,W5,p1,p2,4)
    pygame.draw.line(surf,W3,(p1[0],p1[1]+4),(p2[0],p2[1]+4),2)
    # Halı şeridi
    if d=="right":
        for i in range(n):
            bx=rx+i*sw2; by=ry+rh-(i+1)*sh2
            sx2,sy2=bx-int(cx)+sw2//4,by-int(cy)+2
            pygame.draw.rect(surf,BORDO_M,(sx2,sy2,sw2//2,sh2-3))
    if near:
        lbl=stair.get("label","Merdiven")
        hint=F_SM.render(f"[ E ]  {lbl}",True,C_HINT)
        mx=rx+rw//2-int(cx); my=ry-36-int(cy)
        alpha_rect(surf,(0,0,0),160,
            pygame.Rect(mx-hint.get_width()//2-6,my-2,hint.get_width()+12,hint.get_height()+4))
        surf.blit(hint,(mx-hint.get_width()//2,my))

# ══════════════════════════════════════════════════════
#  KAPI
# ══════════════════════════════════════════════════════
def draw_door(surf,door,cx,cy,near):
    rx,ry,rw,rh=door["rect"]
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    secret=door.get("secret",False)
    if secret and not near:
        # Gizli kapı: sadece duvar gibi görünür
        draw_wall_col(surf,rx,ry,rw,rh,cx,cy)
        return
    # Taş söve
    pygame.draw.rect(surf,S4,(sx,sy,rw,rh))
    # Ahşap panel
    inner=pygame.Rect(sx+5,sy+5,rw-10,rh-5)
    grad(surf,inner,W2,W0)
    # Gotik kemer
    arch_h=int(rw*0.52); cx2=sx+rw//2
    pts=[]
    for i in range(21):
        a=math.pi*i/20
        pts.append((cx2+int((rw//2-5)*math.sin(a)*0.55),
                    sy+int(arch_h*(1-math.cos(a)*0.6))))
    pts+=[(sx+rw-5,sy+arch_h),(sx+5,sy+arch_h)]
    if len(pts)>=3:
        pygame.draw.polygon(surf,W1,pts)
        pygame.draw.lines(surf,W4,False,pts[:21],3)
    # Panel çıtaları
    mid_y=sy+arch_h+(rh-arch_h)//2
    pygame.draw.line(surf,W3,(sx+5,sy+arch_h),(sx+rw-5,sy+arch_h),3)
    pygame.draw.line(surf,W3,(sx+rw//2,sy+arch_h+4),(sx+rw//2,sy+rh-5),2)
    pygame.draw.line(surf,W3,(sx+5,mid_y),(sx+rw-5,mid_y),2)
    # Kapı kolu
    knob_x=sx+rw-13; knob_y=sy+int(rh*0.62)
    pygame.draw.ellipse(surf,(160,130,35),(knob_x-5,knob_y-8,10,16))
    pygame.draw.ellipse(surf,(200,170,50),(knob_x-3,knob_y-5,6,10))
    # Söve süsü
    pygame.draw.rect(surf,S5,(sx,sy,rw,rh),4)
    pygame.draw.rect(surf,S5,(sx,sy,4,rh))
    pygame.draw.rect(surf,S5,(sx+rw-4,sy,4,rh))
    if near:
        lbl=door.get("label","Kapı")
        if secret: lbl="⚠ "+lbl
        hint=F_SM.render(f"[ E ]  {lbl}",True,C_HINT)
        mx=sx+rw//2; my=sy-32
        alpha_rect(surf,(0,0,0),160,
            pygame.Rect(mx-hint.get_width()//2-6,my-2,hint.get_width()+12,hint.get_height()+4))
        surf.blit(hint,(mx-hint.get_width()//2,my))

# ══════════════════════════════════════════════════════
#  DEKOR ÇİZİMLERİ
# ══════════════════════════════════════════════════════
def draw_fireplace(surf,rx,ry,rw,rh,cx,cy, marble=False):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    col_t=MRB_W if marble else S4
    col_b=MRB_G if marble else S2
    grad(surf,pygame.Rect(sx,sy,rw,rh),col_t,col_b)
    if marble:
        for i in range(0,rh,14):
            pygame.draw.line(surf,lc(MRB_G,MRB_D,rng.random()*0.4),
                             (sx+rng.randint(0,rw//3),sy+i),
                             (sx+rng.randint(rw//2,rw),sy+i+rng.randint(-5,5)),1)
    cw=max(8,rw//8)
    pygame.draw.rect(surf,lc(col_t,(255,255,255),0.2),(sx,sy,cw,rh))
    pygame.draw.rect(surf,lc(col_t,(255,255,255),0.2),(sx+rw-cw,sy,cw,rh))
    pygame.draw.rect(surf,lc(col_t,(255,255,255),0.25),(sx-cw//2,sy,rw+cw,10))
    cap_h=rh//5
    grad(surf,pygame.Rect(sx+cw,sy+10,rw-cw*2,cap_h),
         lc(col_t,(255,255,255),0.15),col_b)
    ix,iy=sx+cw,sy+10+cap_h
    iw,ih=rw-cw*2,rh-10-cap_h-10
    pygame.draw.rect(surf,(8,4,2),(ix,iy,iw,ih))
    for i in range(4):
        ex=ix+8+i*(iw-16)//3; ey=iy+ih-10
        pygame.draw.ellipse(surf,(180,50,10),(ex,ey,14,7))
        pygame.draw.ellipse(surf,(220,100,20),(ex+2,ey+1,10,4))
    alpha_rect(surf,(255,140,30),20,pygame.Rect(ix,iy,iw,ih))
    bw=iw//2
    pygame.draw.rect(surf,S2,(sx+rw//2-bw//2,sy-40,bw,44))
    pygame.draw.rect(surf,S3,(sx+rw//2-bw//2,sy-40,bw,44),2)

def draw_window(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    pygame.draw.rect(surf,S4,(sx,sy,rw,rh),6)
    pygame.draw.rect(surf,S5,(sx,sy,4,rh))
    pygame.draw.rect(surf,S5,(sx+rw-4,sy,4,rh))
    ix,iy=sx+6,sy+6; iw,ih=rw-12,rh-12
    grad(surf,pygame.Rect(ix,iy,iw,ih),(20,35,55),(10,20,38))
    cx2=ix+iw//2
    pts=[]
    for i in range(13):
        a=math.pi*i/12
        pts.append((cx2+int((iw//2)*math.sin(a)),
                    iy+int((ih//3)*(1-math.cos(a)*0.7))))
    if len(pts)>=3: pygame.draw.polygon(surf,(40,65,100),pts)
    pygame.draw.line(surf,S4,(ix+iw//2,iy),(ix+iw//2,iy+ih),3)
    pygame.draw.line(surf,S4,(ix,iy+ih//2),(ix+iw,iy+ih//2),3)
    alpha_rect(surf,(100,150,220),20,pygame.Rect(ix,iy,iw,ih//2))
    pygame.draw.line(surf,(120,160,220),(ix+4,iy+6),(ix+iw//3,iy+ih//4),2)

def draw_bookshelf(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),W1,W0)
    pygame.draw.rect(surf,W3,(sx,sy,rw,rh),5)
    pygame.draw.rect(surf,W4,(sx,sy,rw,6))
    pygame.draw.rect(surf,W4,(sx,sy+rh-6,rw,6))
    for cx2 in range(sx,sx+rw,95):
        pygame.draw.rect(surf,W2,(cx2,sy,4,rh))
    BC=[(130,25,25),(25,70,130),(35,90,35),(110,80,15),(70,25,70),
        (140,80,20),(20,80,90),(100,40,10),(160,140,30),(50,50,100),(90,60,20)]
    sh2=52
    for row,sy2 in enumerate(range(sy+8,sy+rh-10,sh2)):
        pygame.draw.rect(surf,W4,(sx+5,sy2+sh2-6,rw-10,6))
        bx2=sx+8; bi=0
        while bx2<sx+rw-14:
            bw2=rng.randint(10,20); bh2=rng.randint(30,sh2-10)
            bcol=BC[(row*7+bi)%len(BC)]; by2=sy2+sh2-6-bh2
            pygame.draw.rect(surf,bcol,(bx2,by2,bw2-1,bh2))
            pygame.draw.rect(surf,lc(bcol,(255,255,255),0.28),(bx2,by2,bw2-1,3))
            pygame.draw.line(surf,(0,0,0),(bx2+bw2-1,by2),(bx2+bw2-1,by2+bh2),1)
            bx2+=bw2; bi+=1

def draw_portrait(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    pygame.draw.rect(surf,(75,55,12),(sx,sy,rw,rh),border_radius=2)
    pygame.draw.rect(surf,(165,132,38),(sx,sy,rw,rh),5)
    pygame.draw.rect(surf,(200,168,52),(sx+2,sy+2,rw-4,4))
    pygame.draw.rect(surf,(200,168,52),(sx+2,sy+rh-6,rw-4,4))
    inner=pygame.Rect(sx+10,sy+10,rw-20,rh-20)
    grad(surf,inner,(35,28,22),(22,17,12))
    cx2=inner.centerx
    pts=[(cx2-inner.w//4,inner.bottom),(cx2+inner.w//4,inner.bottom),
         (cx2+inner.w//5,inner.centery+5),(cx2-inner.w//5,inner.centery+5)]
    pygame.draw.polygon(surf,(25,20,15),pts)
    pygame.draw.rect(surf,(180,165,140),(cx2-5,inner.centery,10,12))
    pygame.draw.ellipse(surf,(180,155,125),(cx2-12,inner.y+8,24,30))
    pygame.draw.ellipse(surf,(20,14,8),(cx2-12,inner.y+8,24,14))
    for (ox,oy) in [(0,0),(rw-10,0),(0,rh-10),(rw-10,rh-10)]:
        pygame.draw.rect(surf,(200,170,55),(sx+ox,sy+oy,10,10))

def draw_candelabra(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    pygame.draw.ellipse(surf,W3,(cx2-18,sy+rh-12,36,12))
    for i in range(rh-12):
        t=i/(rh-12); w2=max(2,int(8*(1-t*0.6)))
        pygame.draw.line(surf,lc(W3,W2,t),(cx2-w2,sy+i),(cx2+w2,sy+i))
    pygame.draw.ellipse(surf,W4,(cx2-10,sy+rh//2-8,20,16))
    for (ax,ay) in [(-22,0),(0,-8),(22,0)]:
        ax2=cx2+ax; ay2=sy+14+ay
        pygame.draw.line(surf,W3,(cx2,sy+22),(ax2,ay2),2)
        pygame.draw.rect(surf,W4,(ax2-4,ay2,8,10))
        pygame.draw.rect(surf,(210,200,185),(ax2-3,ay2-12,6,14))
        fk=math.sin(_ft*8+ax)*2
        pygame.draw.polygon(surf,FL_A,[(ax2-4,ay2-12),(ax2+4,ay2-12),(ax2,int(ay2-24+fk))])
        pygame.draw.polygon(surf,FL_B,[(ax2-2,ay2-12),(ax2+2,ay2-12),(ax2,int(ay2-18+fk))])
        alpha_rect(surf,(255,200,80),14,pygame.Rect(ax2-16,ay2-24,32,32))

def draw_carpet(surf,rx,ry,rw,rh,cx,cy,color=None):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cm=color if color else BORDO_M
    cd=lc(cm,(0,0,0),0.4)
    grad(surf,pygame.Rect(sx,sy,rw,rh),cm,cd)
    pygame.draw.rect(surf,(160,130,40),(sx,sy,rw,rh),3)
    pygame.draw.rect(surf,BORDO_L,(sx+5,sy+2,rw-10,rh-4),1)
    gap=max(12,rh//3)
    for i in range(sx+20,sx+rw-10,gap*2):
        pygame.draw.line(surf,BORDO_L,(i,sy+3),(i,sy+rh-3),1)
    for (ox,oy) in [(8,2),(rw-14,2)]:
        pygame.draw.circle(surf,(160,130,40),(sx+ox,sy+oy+2),4)

def draw_sconce(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    pygame.draw.rect(surf,S3,(sx,sy,rw,rh),border_radius=3)
    pygame.draw.rect(surf,S4,(sx,sy,rw,rh),2)
    pygame.draw.line(surf,W3,(cx2,sy+rh),(cx2,sy+rh-rh//2),3)
    pygame.draw.line(surf,W3,(cx2,sy+rh-rh//2),(cx2+rw//2,sy+8),2)
    pygame.draw.rect(surf,(210,200,185),(cx2+rw//2-3,sy,6,12))
    fk=math.sin(_ft*9+rx*0.01)*2
    pygame.draw.polygon(surf,FL_A,[(cx2+rw//2-4,sy),(cx2+rw//2+4,sy),(cx2+rw//2,int(sy-14+fk))])
    pygame.draw.polygon(surf,FL_B,[(cx2+rw//2-2,sy),(cx2+rw//2+2,sy),(cx2+rw//2,int(sy-9+fk))])
    alpha_rect(surf,(255,200,80),18,pygame.Rect(cx2+rw//2-20,sy-20,40,30))

def draw_chandelier(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    for i in range(0,sy+rh-2,7):
        pygame.draw.ellipse(surf,W3,(cx2-2,i,4,6))
    pygame.draw.circle(surf,W3,(cx2,sy+rh),rw//4)
    pygame.draw.circle(surf,W4,(cx2,sy+rh),rw//4,2)
    ring_y=sy+rh+rw//4
    pygame.draw.ellipse(surf,W4,(cx2-rw//2,ring_y-4,rw,8),2)
    for i in range(6):
        a=2*math.pi*i/6
        ax2=cx2+int(math.cos(a)*rw//2); ay2=ring_y+int(math.sin(a)*4)
        pygame.draw.line(surf,W3,(cx2,ring_y),(ax2,ay2),2)
        pygame.draw.rect(surf,(210,200,185),(ax2-3,ay2,6,10))
        fk=math.sin(_ft*7+i)*2
        pygame.draw.polygon(surf,FL_A,[(ax2-3,ay2),(ax2+3,ay2),(ax2,int(ay2-12+fk))])
        alpha_rect(surf,(255,210,90),12,pygame.Rect(ax2-14,ay2-16,28,24))
    alpha_rect(surf,(255,200,80),8,pygame.Rect(cx2-rw,sy+rh-20,rw*2,80))

def draw_clock(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),W2,W0)
    pygame.draw.rect(surf,W4,(sx,sy,rw,rh),3)
    hh=rh//5
    grad(surf,pygame.Rect(sx-4,sy,rw+8,hh),W3,W2)
    pygame.draw.rect(surf,W4,(sx-4,sy,rw+8,hh),2)
    pygame.draw.polygon(surf,W3,[(sx-4,sy),(sx+rw//2,sy-20),(sx+rw+4,sy)])
    pygame.draw.polygon(surf,W4,[(sx-4,sy),(sx+rw//2,sy-20),(sx+rw+4,sy)],2)
    fc=sx+rw//2; fcy=sy+hh-6; fr=min(rw//2-6,hh-8)
    pygame.draw.circle(surf,(230,220,195),(fc,fcy),fr)
    pygame.draw.circle(surf,W3,(fc,fcy),fr,2)
    for i in range(12):
        a=2*math.pi*i/12-math.pi/2
        pygame.draw.circle(surf,W0,(fc+int(math.cos(a)*(fr-4)),fcy+int(math.sin(a)*(fr-4))),2)
    for (ln,sp,col) in [(fr-6,0.5,W0),(fr-10,6,S2)]:
        a=_ft*sp-math.pi/2
        pygame.draw.line(surf,col,(fc,fcy),(fc+int(math.cos(a)*ln),fcy+int(math.sin(a)*ln)),2)
    pr=pygame.Rect(sx+rw//2-5,sy+hh+5,10,rh-hh-15)
    pygame.draw.rect(surf,(8,5,2),pr)
    pygame.draw.rect(surf,W3,pr,1)
    py2=pr.y+int(pr.h*0.4); px2=sx+rw//2+int(math.sin(_ft*2)*12)
    pygame.draw.line(surf,W4,(sx+rw//2,pr.y),(px2,py2),1)
    pygame.draw.circle(surf,(180,145,40),(px2,py2),5)

def draw_armor(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    pygame.draw.ellipse(surf,S3,(cx2-rw//2,sy+rh-12,rw,12))
    pygame.draw.line(surf,S2,(cx2-6,sy+rh-12),(cx2-8,sy+int(rh*0.6)),4)
    pygame.draw.line(surf,S2,(cx2+6,sy+rh-12),(cx2+8,sy+int(rh*0.6)),4)
    torso=pygame.Rect(cx2-rw//3,sy+int(rh*0.3),rw*2//3,int(rh*0.35))
    grad(surf,torso,S4,S2)
    pygame.draw.rect(surf,S5,torso,2)
    pygame.draw.line(surf,S5,(torso.centerx,torso.top+4),(torso.centerx,torso.bottom-4),2)
    for ox in [-1,1]:
        pygame.draw.ellipse(surf,S4,(cx2+ox*(rw//3+2)-8,sy+int(rh*0.28),18,10))
    pygame.draw.circle(surf,S3,(cx2,sy+int(rh*0.18)),rw//4)
    pygame.draw.circle(surf,S4,(cx2,sy+int(rh*0.18)),rw//4,2)
    pygame.draw.polygon(surf,S4,[(cx2-4,sy+int(rh*0.18)-rw//4),
                                  (cx2,sy+int(rh*0.18)-rw//4-10),
                                  (cx2+4,sy+int(rh*0.18)-rw//4)])
    pygame.draw.line(surf,S0,(cx2-6,sy+int(rh*0.18)),(cx2+6,sy+int(rh*0.18)),2)

# Yeni dekorlar ──────────────────────────────────────
def draw_piano(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    # Gövde
    grad(surf,pygame.Rect(sx,sy,rw,rh),(30,22,12),(18,12,6))
    pygame.draw.rect(surf,W3,(sx,sy,rw,rh),3)
    # Kapak (eğik)
    pts=[(sx,sy),(sx+rw,sy),(sx+rw,sy-20),(sx+rw*2//3,sy-35),(sx,sy-18)]
    pygame.draw.polygon(surf,(20,14,8),pts)
    pygame.draw.lines(surf,W3,True,pts,2)
    # Klavye
    kbd_y=sy+rh-20; kbd_h=18
    white_w=max(1,rw//14)
    for i in range(14):
        kx=sx+i*white_w
        pygame.draw.rect(surf,(220,218,210),(kx,kbd_y,white_w-1,kbd_h))
        pygame.draw.rect(surf,(100,95,88),(kx,kbd_y,white_w-1,kbd_h),1)
    # Siyah tuşlar
    black_pos=[0,1,3,4,5,7,8,10,11,12]
    for i in black_pos:
        kx=sx+i*white_w+white_w*2//3
        pygame.draw.rect(surf,(15,12,8),(kx,kbd_y,white_w//2,kbd_h*2//3))
    # Bacaklar
    for lx in [sx+8,sx+rw-14]:
        pygame.draw.rect(surf,(25,18,8),(lx,sy+rh,8,16))

def draw_dining_table(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    # Masa üstü
    grad(surf,pygame.Rect(sx,sy,rw,16),W4,W2)
    pygame.draw.rect(surf,W5,(sx,sy,rw,3))
    pygame.draw.rect(surf,W3,(sx,sy,rw,16),2)
    # Masa gövdesi
    pygame.draw.rect(surf,W1,(sx+8,sy+16,rw-16,rh-16))
    pygame.draw.rect(surf,W2,(sx+8,sy+16,rw-16,rh-16),2)
    # Bacaklar
    for lx in [sx+12,sx+rw-20]:
        grad(surf,pygame.Rect(lx,sy+rh-30,8,30),W3,W1)
    # Tabak simgeleri (üstte)
    for px in range(sx+40,sx+rw-20,80):
        pygame.draw.circle(surf,(190,185,175),(px,sy-4),12)
        pygame.draw.circle(surf,(210,205,195),(px,sy-4),10)
        pygame.draw.circle(surf,(170,165,155),(px,sy-4),10,1)
    # Şamdan ortada
    mcx=sx+rw//2
    pygame.draw.rect(surf,W4,(mcx-3,sy-20,6,20))
    pygame.draw.rect(surf,(210,200,185),(mcx-2,sy-30,4,12))
    fk=math.sin(_ft*8)*2
    pygame.draw.polygon(surf,FL_A,[(mcx-3,sy-30),(mcx+3,sy-30),(mcx,int(sy-42+fk))])

def draw_iron_range(surf,rx,ry,rw,rh,cx,cy):
    """Dökme demir mutfak ocağı."""
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),IRON_L,IRON)
    pygame.draw.rect(surf,(40,40,45),(sx,sy,rw,rh),3)
    # Ocak yüzeyi
    top_h=rh//4
    pygame.draw.rect(surf,(50,50,55),(sx,sy,rw,top_h))
    # Halka (burner)
    for i in range(3):
        bx=sx+20+i*(rw-30)//2
        pygame.draw.circle(surf,(30,30,35),(bx,sy+top_h//2),14)
        pygame.draw.circle(surf,(65,65,70),(bx,sy+top_h//2),14,3)
        pygame.draw.circle(surf,(25,25,28),(bx,sy+top_h//2),7)
        fk=math.sin(_ft*6+i)*1.5
        alpha_rect(surf,FL_C,25,pygame.Rect(bx-10,sy+top_h//2-10,20,20))
    # Fırın kapısı
    door_y=sy+top_h+4
    grad(surf,pygame.Rect(sx+6,door_y,rw-12,rh-top_h-8),IRON_L,IRON)
    pygame.draw.rect(surf,(40,40,45),(sx+6,door_y,rw-12,rh-top_h-8),2)
    pygame.draw.ellipse(surf,(80,80,85),(sx+rw//2-6,door_y+(rh-top_h-8)//2-4,12,8))
    # Baca
    baca_w=rw//3
    pygame.draw.rect(surf,IRON,(sx+rw//2-baca_w//2,sy-40,baca_w,44))
    pygame.draw.rect(surf,IRON_L,(sx+rw//2-baca_w//2,sy-40,baca_w,44),2)

def draw_canopy_bed(surf,rx,ry,rw,rh,cx,cy):
    """Dört direkli yatak."""
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    # Yatak tabanı
    grad(surf,pygame.Rect(sx,sy+rh//2,rw,rh//2),W2,W0)
    pygame.draw.rect(surf,W3,(sx,sy+rh//2,rw,rh//2),2)
    # Yatak yorgan
    grad(surf,pygame.Rect(sx+6,sy+rh//3,rw-12,rh//3),(180,155,160),(130,100,110))
    pygame.draw.rect(surf,BORDO_D,(sx+6,sy+rh//3,rw-12,rh//3),2)
    # Yastık
    grad(surf,pygame.Rect(sx+12,sy+rh//3-12,rw-24,20),(210,200,195),(180,170,165))
    # 4 direk
    for px2 in [sx+4,sx+rw-10]:
        pygame.draw.rect(surf,W3,(px2,sy,6,rh))
        pygame.draw.rect(surf,W4,(px2,sy,6,rh),1)
        # Tepe topu
        pygame.draw.circle(surf,W4,(px2+3,sy),8)
    # Saçak (üst çerçeve)
    pygame.draw.rect(surf,W3,(sx,sy,rw,6))
    # Perde
    for px2 in [sx,sx+rw-6]:
        perde=pygame.Rect(px2,sy+6,6,rh//2-6)
        grad(surf,perde,BORDO_M,BORDO_D)
        # Perde kıvrımları
        for i in range(0,perde.h,12):
            pygame.draw.line(surf,BORDO_L,(perde.x,perde.y+i),(perde.x+perde.w,perde.y+i),1)

def draw_globe(surf,rx,ry,rw,rh,cx,cy):
    """Dünya küresi."""
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2; cy2=sy+rh//2-8
    r=rw//2-4
    # Standart (metal çerçeve)
    pygame.draw.circle(surf,(50,90,60),(cx2,cy2),r)
    pygame.draw.circle(surf,(40,75,50),(cx2,cy2),r,1)
    # Enlem/boylam çizgileri
    for i in range(1,4):
        ay=cy2-r+i*r//2
        rr=max(1,int(math.sqrt(max(0,r*r-(ay-cy2)**2))))
        pygame.draw.ellipse(surf,(55,110,70),(cx2-rr,ay-3,rr*2,6),1)
    pygame.draw.line(surf,(55,110,70),(cx2,cy2-r),(cx2,cy2+r),1)
    pygame.draw.line(surf,(55,110,70),(cx2-r,cy2),(cx2+r,cy2),1)
    # Parlama
    pygame.draw.circle(surf,(80,140,90),(cx2-r//3,cy2-r//3),r//4)
    # Çerçeve
    pygame.draw.circle(surf,(140,110,30),(cx2,cy2),r,3)
    # Ayak
    pygame.draw.line(surf,W3,(cx2,cy2+r),(cx2,sy+rh-6),3)
    pygame.draw.ellipse(surf,W3,(cx2-16,sy+rh-10,32,10))

def draw_pantry_shelves(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    grad(surf,pygame.Rect(sx,sy,rw,rh),W1,W0)
    pygame.draw.rect(surf,W3,(sx,sy,rw,rh),4)
    shelf_gap=55
    for row,sy2 in enumerate(range(sy+10,sy+rh,shelf_gap)):
        pygame.draw.rect(surf,W4,(sx+4,sy2+shelf_gap-8,rw-8,8))
        # Kavanoz ve kutular
        items=[(30,35,TILE_W),(20,40,(120,80,20)),(25,38,BORDO_M),
               (22,30,(80,110,40)),(18,28,(160,140,50)),(30,32,(90,70,50))]
        bx2=sx+8
        for ii,(iw2,ih2,ic) in enumerate(items):
            if bx2+iw2>sx+rw-8: break
            iy2=sy2+shelf_gap-8-ih2
            pygame.draw.rect(surf,ic,(bx2,iy2,iw2-2,ih2))
            pygame.draw.rect(surf,lc(ic,(255,255,255),0.3),(bx2,iy2,iw2-2,4))
            pygame.draw.rect(surf,(30,25,20),(bx2,iy2,iw2-2,ih2),1)
            bx2+=iw2+4

def draw_washtub(surf,rx,ry,rw,rh,cx,cy):
    """Çamaşır kazanı."""
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    # Kazan gövdesi (trapez)
    pts=[(sx+8,sy+rh),(sx+rw-8,sy+rh),(sx+rw-2,sy+rh//2),(sx+2,sy+rh//2)]
    pygame.draw.polygon(surf,(90,75,55),pts)
    pygame.draw.lines(surf,(60,50,35),True,pts,3)
    # Su yüzeyi
    water_y=sy+rh//2+4
    pygame.draw.ellipse(surf,(50,80,100),(sx+2,water_y-6,rw-4,12))
    alpha_rect(surf,(60,100,140),40,pygame.Rect(sx+2,water_y-6,rw-4,12))
    # Buhar
    for i in range(3):
        steam_x=cx2-20+i*20
        for j in range(3):
            alpha_rect(surf,(200,200,220),
                       max(0,40-j*14),
                       pygame.Rect(steam_x,water_y-10-j*8,8,8))
    # Ayaklar
    for lx in [sx+10,sx+rw-18]:
        pygame.draw.rect(surf,(65,50,30),(lx,sy+rh,8,12))

def draw_bell_pull(surf,rx,ry,rw,rh,cx,cy):
    """Çan ipi (hizmetli çağırma)."""
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2
    # İp
    for i in range(0,rh-10,8):
        sway=int(math.sin(_ft*1.5+i*0.1)*2)
        pygame.draw.line(surf,BORDO_M,(cx2+sway,sy+i),(cx2+sway,sy+i+8),2)
    # Alt tutamak
    pygame.draw.ellipse(surf,BORDO_L,(cx2-8,sy+rh-10,16,12))
    pygame.draw.ellipse(surf,BORDO_M,(cx2-6,sy+rh-8,12,8))
    # Çan ikonu
    pygame.draw.arc(surf,(180,150,40),
        pygame.Rect(cx2-6,sy-14,12,12),math.pi,0,3)
    pygame.draw.line(surf,(180,150,40),(cx2-6,sy-8),(cx2+6,sy-8),2)

def draw_coal_pile(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    # Yığın silüeti
    for i in range(8):
        cx2=sx+i*(rw//8)+rng.randint(-3,3)
        cy2=sy+rh-rng.randint(10,rh//2)
        r=rng.randint(8,18)
        pygame.draw.circle(surf,(28,26,24),(cx2,cy2),r)
        pygame.draw.circle(surf,(40,38,35),(cx2-r//3,cy2-r//3),r//3)

def draw_secret_door_hint(surf,rx,ry,rw,rh,cx,cy):
    """Gizli geçit göstergesi (çok yakın olunca fark edilir)."""
    sx,sy=rx-int(cx),ry-int(cy)
    draw_wall_col(surf,rx,ry,rw,rh,cx,cy)
    # Çok ince outline (oyuncu fark etmeli)
    pygame.draw.rect(surf,lc(S3,S5,0.3),(sx,sy,rw,rh),1)

# Dekor dispatcher
def draw_decor(surf,d,cx,cy):
    rx,ry,rw,rh=d["rect"]; t=d["type"]
    kw=d.get("kw",{})
    if   t=="fireplace":    draw_fireplace(surf,rx,ry,rw,rh,cx,cy,**kw)
    elif t=="window":       draw_window(surf,rx,ry,rw,rh,cx,cy)
    elif t=="bookshelf":    draw_bookshelf(surf,rx,ry,rw,rh,cx,cy)
    elif t=="portrait":     draw_portrait(surf,rx,ry,rw,rh,cx,cy)
    elif t=="candelabra":   draw_candelabra(surf,rx,ry,rw,rh,cx,cy)
    elif t=="carpet":       draw_carpet(surf,rx,ry,rw,rh,cx,cy,**kw)
    elif t=="sconce":       draw_sconce(surf,rx,ry,rw,rh,cx,cy)
    elif t=="chandelier":   draw_chandelier(surf,rx,ry,rw,rh,cx,cy)
    elif t=="clock":        draw_clock(surf,rx,ry,rw,rh,cx,cy)
    elif t=="armor":        draw_armor(surf,rx,ry,rw,rh,cx,cy)
    elif t=="piano":        draw_piano(surf,rx,ry,rw,rh,cx,cy)
    elif t=="dining_table": draw_dining_table(surf,rx,ry,rw,rh,cx,cy)
    elif t=="iron_range":   draw_iron_range(surf,rx,ry,rw,rh,cx,cy)
    elif t=="canopy_bed":   draw_canopy_bed(surf,rx,ry,rw,rh,cx,cy)
    elif t=="globe":        draw_globe(surf,rx,ry,rw,rh,cx,cy)
    elif t=="pantry":       draw_pantry_shelves(surf,rx,ry,rw,rh,cx,cy)
    elif t=="washtub":      draw_washtub(surf,rx,ry,rw,rh,cx,cy)
    elif t=="bell_pull":    draw_bell_pull(surf,rx,ry,rw,rh,cx,cy)
    elif t=="coal":         draw_coal_pile(surf,rx,ry,rw,rh,cx,cy)

# ══════════════════════════════════════════════════════
#  ODA VERİSİ  –  TAM MİMARİ HİYERARŞİ
# ══════════════════════════════════════════════════════
#  KAT HİYERARŞİSİ:
#  BODRUM  : mutfak, kiler, camasirhane, komurluk, hizmetli_yemek
#  ZEMİN   : giris_holu, drawing_room, dining_room, kutuphane, morning_room
#  1.KAT   : ust_koridor, master_bedroom, giyinme_odasi, cocuk_odasi_1,
#             cocuk_odasi_2, banyo
#  ÇATI    : cati_koridor, hizmetli_1, hizmetli_2, hizmetli_3, depo
#  ÖZEL    : kule, gizli_gecit

ROOM_DEFS = {

# ══════════════════════════════════════════════════════
# BODRUM — SERVİS KATI
# ══════════════════════════════════════════════════════
"mutfak":{
  "name":"Mutfak  (Bodrum Kat)",
  "floor":"bodrum",
  "wall_style":"kitchen",
  "w":1800,"h":560,
  "wall_top":(42,34,26),"wall_bot":(28,22,16),"block_size":(44,22),
  "floor_style":"stone","floor_world_y":480,
  "platforms":[
    {"rect":(0,480,1800,80),"type":"floor"},
    {"rect":(0,0,1800,22),"type":"ceil"},
    {"rect":(0,0,22,560),"type":"wall"},
    {"rect":(1778,0,22,560),"type":"wall"},
    {"rect":(200,390,300,22),"type":"stone"},   # tezgah sol
    {"rect":(750,410,220,22),"type":"stone"},   # tezgah orta
    {"rect":(1100,390,320,22),"type":"stone"},  # tezgah sağ
    {"rect":(200,300,120,14),"type":"stone"},   # raf sol
    {"rect":(1280,300,120,14),"type":"stone"},  # raf sağ
  ],
  "stairs":[],
  "doors":[
    {"rect":(22,340,64,140),"target_room":"kiler","target_spawn":(1600,400),"label":"Kiler"},
    {"rect":(1714,340,64,140),"target_room":"giris_holu","target_spawn":(200,500),"label":"Giriş Holü ↑","secret":False},
  ],
  "decor":[
    {"type":"iron_range","rect":(780,250,240,230)},
    {"type":"window","rect":(350,30,80,140)},
    {"type":"window","rect":(1280,30,80,140)},
    {"type":"sconce","rect":(180,120,28,44)},
    {"type":"sconce","rect":(900,120,28,44)},
    {"type":"sconce","rect":(1540,120,28,44)},
    {"type":"bell_pull","rect":(650,60,14,160)},
    {"type":"bell_pull","rect":(1100,60,14,160)},
  ],
  "fire_sources":[(900,450,18),(902,445,12)],
  "spawn":(120,400),
},

"kiler":{
  "name":"Kiler  (Bodrum)",
  "floor":"bodrum",
  "wall_style":"cellar",
  "w":900,"h":500,
  "wall_top":(25,20,15),"wall_bot":(16,13,10),"block_size":(48,24),
  "floor_style":"stone","floor_world_y":420,
  "platforms":[
    {"rect":(0,420,900,80),"type":"floor"},
    {"rect":(0,0,900,22),"type":"ceil"},
    {"rect":(0,0,22,500),"type":"wall"},
    {"rect":(878,0,22,500),"type":"wall"},
    {"rect":(100,300,180,14),"type":"stone"},
    {"rect":(100,220,180,14),"type":"stone"},
    {"rect":(550,310,180,14),"type":"stone"},
    {"rect":(550,230,180,14),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(814,300,64,120),"target_room":"mutfak","target_spawn":(1640,420),"label":"Mutfak →"},
    {"rect":(22,300,64,120),"target_room":"komurluk","target_spawn":(600,380),"label":"← Kömürlük"},
  ],
  "decor":[
    {"type":"pantry","rect":(80,60,220,360)},
    {"type":"pantry","rect":(530,60,240,360)},
    {"type":"sconce","rect":(330,120,28,44)},
    {"type":"clock","rect":(390,240,50,180)},
  ],
  "fire_sources":[], "spawn":(700,360),
},

"komurluk":{
  "name":"Kömürlük  (Bodrum)",
  "floor":"bodrum",
  "wall_style":"cellar",
  "w":700,"h":480,
  "wall_top":(18,15,12),"wall_bot":(12,10,8),"block_size":(46,23),
  "floor_style":"stone","floor_world_y":400,
  "platforms":[
    {"rect":(0,400,700,80),"type":"floor"},
    {"rect":(0,0,700,22),"type":"ceil"},
    {"rect":(0,0,22,480),"type":"wall"},
    {"rect":(678,0,22,480),"type":"wall"},
  ],
  "stairs":[], "doors":[
    {"rect":(614,280,64,120),"target_room":"kiler","target_spawn":(80,360),"label":"Kiler →"},
    {"rect":(22,280,64,120),"target_room":"camasirhane","target_spawn":(600,380),"label":"← Çamaşırhane"},
  ],
  "decor":[
    {"type":"coal","rect":(80,300,200,100)},
    {"type":"coal","rect":(350,320,180,80)},
    {"type":"coal","rect":(500,310,150,90)},
    {"type":"sconce","rect":(320,120,28,44)},
  ],
  "fire_sources":[], "spawn":(560,340),
},

"camasirhane":{
  "name":"Çamaşırhane  (Bodrum)",
  "floor":"bodrum",
  "wall_style":"servants",
  "w":1000,"h":500,
  "wall_top":(160,155,148),"wall_bot":(130,125,118),"block_size":(42,21),
  "floor_style":"stone","floor_world_y":420,
  "platforms":[
    {"rect":(0,420,1000,80),"type":"floor"},
    {"rect":(0,0,1000,22),"type":"ceil"},
    {"rect":(0,0,22,500),"type":"wall"},
    {"rect":(978,0,22,500),"type":"wall"},
  ],
  "stairs":[], "doors":[
    {"rect":(914,300,64,120),"target_room":"komurluk","target_spawn":(80,340),"label":"Kömürlük →"},
    {"rect":(22,300,64,120),"target_room":"hizmetli_yemek","target_spawn":(880,380),"label":"Hizmetli Yemek →"},
  ],
  "decor":[
    {"type":"washtub","rect":(200,300,140,120)},
    {"type":"washtub","rect":(420,310,120,110)},
    {"type":"washtub","rect":(620,300,140,120)},
    {"type":"sconce","rect":(180,140,28,44)},
    {"type":"sconce","rect":(800,140,28,44)},
    {"type":"window","rect":(430,30,80,100)},
  ],
  "fire_sources":[], "spawn":(860,360),
},

"hizmetli_yemek":{
  "name":"Hizmetli Yemek Salonu  (Bodrum)",
  "floor":"bodrum",
  "wall_style":"servants",
  "w":1200,"h":540,
  "wall_top":(158,150,142),"wall_bot":(128,122,115),"block_size":(42,21),
  "floor_style":"wood","floor_world_y":460,
  "platforms":[
    {"rect":(0,460,1200,80),"type":"floor"},
    {"rect":(0,0,1200,22),"type":"ceil"},
    {"rect":(0,0,22,540),"type":"wall"},
    {"rect":(1178,0,22,540),"type":"wall"},
  ],
  "stairs":[
    # Zemin kata çıkış — hizmetli servis merdiveni
    {"rect":(50,300,160,160),"steps":5,"dir":"right",
     "target_room":"giris_holu","target_spawn":(1840,440),"label":"Zemin Kat  ↑"},
  ],
  "doors":[
    {"rect":(22,320,64,140),"target_room":"camasirhane","target_spawn":(900,360),"label":"← Çamaşırhane"},
  ],
  "decor":[
    {"type":"dining_table","rect":(300,380,600,80)},
    {"type":"sconce","rect":(200,140,28,44)},
    {"type":"sconce","rect":(600,140,28,44)},
    {"type":"sconce","rect":(950,140,28,44)},
    {"type":"window","rect":(500,30,80,100)},
    {"type":"clock","rect":(1050,280,50,180)},
  ],
  "fire_sources":[], "spawn":(150,400),
},

# ══════════════════════════════════════════════════════
# ZEMİN KAT — KAMUSAL ALAN
# ══════════════════════════════════════════════════════
"giris_holu":{
  "name":"Giriş Holü  (Zemin Kat)",
  "floor":"zemin",
  "wall_style":"checkerboard",
  "w":2000,"h":640,
  "wall_top":S1,"wall_bot":S2,"block_size":(56,28),
  "floor_style":"checkerboard","floor_world_y":560,
  "platforms":[
    {"rect":(0,560,2000,80),"type":"floor"},
    {"rect":(0,0,2000,22),"type":"ceil"},
    {"rect":(0,0,22,640),"type":"wall"},
    {"rect":(1978,0,22,640),"type":"wall"},
    # Ana merdiven sahanlığı
    {"rect":(780,330,440,18),"type":"stone"},
    # Merdiven ara basamakları
    {"rect":(940,440,100,14),"type":"stone"},
  ],
  "stairs":[
    # Ana merdiven SOL kolu — Zemin → 1. Kat
    {"rect":(540,330,240,230),"steps":8,"dir":"right",
     "target_room":"ust_koridor","target_spawn":(200,480),"label":"Birinci Kat  ↑"},
    # Ana merdiven SAĞ kolu — simetrik
    {"rect":(1220,330,240,230),"steps":8,"dir":"left",
     "target_room":"ust_koridor","target_spawn":(1800,480),"label":"Birinci Kat  ↑"},
    # Servis merdiveni — sağ arka köşe, dar
    {"rect":(1820,420,100,140),"steps":5,"dir":"left",
     "target_room":"hizmetli_yemek","target_spawn":(100,400),"label":"[Servis] Bodrum  ↓"},
  ],
  "doors":[
    {"rect":(22,400,72,160),"target_room":"drawing_room","target_spawn":(80,480),"label":"Drawing Room"},
    {"rect":(1906,400,72,160),"target_room":"dining_room","target_spawn":(80,480),"label":"Yemek Odası"},
    {"rect":(900,260,72,72),"target_room":"kutuphane","target_spawn":(80,440),"label":"Kütüphane ↑"},
  ],
  "decor":[
    {"type":"chandelier","rect":(960,22,120,130)},
    {"type":"portrait","rect":(200,80,120,160)},   # av hayvanı başı / portre
    {"type":"portrait","rect":(1650,80,120,160)},
    {"type":"portrait","rect":(880,80,110,140)},
    {"type":"armor","rect":(440,400,75,160)},       # zırh standı
    {"type":"armor","rect":(1460,400,75,160)},
    {"type":"sconce","rect":(380,210,30,50)},
    {"type":"sconce","rect":(1550,210,30,50)},
    {"type":"window","rect":(300,40,100,240)},
    {"type":"window","rect":(1580,40,100,240)},
    {"type":"carpet","rect":(350,540,1300,20),"kw":{"color":BORDO_M}},
    {"type":"clock","rect":(660,370,65,190)},
    {"type":"bell_pull","rect":(1700,80,14,180)},
  ],
  "fire_sources":[(1000,540,14)],
  "spawn":(200,500),
},

"drawing_room":{
  "name":"Drawing Room  (Zemin Kat)",
  "floor":"zemin",
  "wall_style":"wallpaper_floral",
  "w":1600,"h":600,
  "wall_top":WP_BG,"wall_bot":WP_BG,"block_size":(38,38),
  "floor_style":"wood","floor_world_y":520,
  "platforms":[
    {"rect":(0,520,1600,80),"type":"floor"},
    {"rect":(0,0,1600,22),"type":"ceil"},
    {"rect":(0,0,22,600),"type":"wall"},
    {"rect":(1578,0,22,600),"type":"wall"},
    {"rect":(200,380,180,16),"type":"stone"},  # pencere pervazı oturma
    {"rect":(1200,380,180,16),"type":"stone"},
  ],
  "stairs":[],
  "doors":[
    {"rect":(1506,360,72,160),"target_room":"giris_holu","target_spawn":(60,480),"label":"Giriş Holü"},
    {"rect":(22,360,72,160),"target_room":"morning_room","target_spawn":(1500,460),"label":"Morning Room"},
  ],
  "decor":[
    {"type":"chandelier","rect":(760,22,100,120)},
    {"type":"fireplace","rect":(690,300,160,220),"kw":{"marble":True}},
    {"type":"window","rect":(160,40,110,300)},
    {"type":"window","rect":(1320,40,110,300)},
    {"type":"portrait","rect":(480,50,120,160)},
    {"type":"portrait","rect":(960,50,120,160)},
    {"type":"sconce","rect":(360,180,30,50)},
    {"type":"sconce","rect":(1180,180,30,50)},
    {"type":"candelabra","rect":(500,450,30,70)},
    {"type":"candelabra","rect":(1060,450,30,70)},
    {"type":"carpet","rect":(180,500,1240,20),"kw":{"color":ZUMRUT_M}},
    {"type":"piano","rect":(1280,360,200,160)},
    {"type":"bell_pull","rect":(280,60,14,180)},
    {"type":"bell_pull","rect":(1280,60,14,180)},
  ],
  "fire_sources":[(770,510,14)],
  "spawn":(1440,460),
},

"morning_room":{
  "name":"Morning Room  (Zemin Kat)",
  "floor":"zemin",
  "wall_style":"wallpaper_floral",
  "w":1100,"h":560,
  "wall_top":(35,22,30),"wall_bot":(25,16,22),"block_size":(38,38),
  "floor_style":"wood","floor_world_y":480,
  "platforms":[
    {"rect":(0,480,1100,80),"type":"floor"},
    {"rect":(0,0,1100,22),"type":"ceil"},
    {"rect":(0,0,22,560),"type":"wall"},
    {"rect":(1078,0,22,560),"type":"wall"},
    {"rect":(200,340,180,16),"type":"stone"},
    {"rect":(700,340,180,16),"type":"stone"},
  ],
  "stairs":[],
  "doors":[
    {"rect":(1006,320,72,160),"target_room":"drawing_room","target_spawn":(80,460),"label":"Drawing Room"},
  ],
  "decor":[
    {"type":"chandelier","rect":(520,22,90,110)},
    {"type":"window","rect":(120,30,120,320)},   # geniş güneşli pencere
    {"type":"window","rect":(860,30,120,320)},
    {"type":"fireplace","rect":(490,310,120,170),"kw":{"marble":True}},
    {"type":"portrait","rect":(380,50,100,130)},
    {"type":"sconce","rect":(300,160,28,44)},
    {"type":"sconce","rect":(740,160,28,44)},
    {"type":"candelabra","rect":(440,410,28,70)},
    {"type":"carpet","rect":(150,460,800,20),"kw":{"color":LACI_M}},
    {"type":"bell_pull","rect":(900,80,14,160)},
  ],
  "fire_sources":[(550,465,12)],
  "spawn":(1500,420),
},

"dining_room":{
  "name":"Yemek Odası  (Zemin Kat)",
  "floor":"zemin",
  "wall_style":"wallpaper_floral",
  "w":1800,"h":620,
  "wall_top":(28,18,22),"wall_bot":(20,13,16),"block_size":(38,38),
  "floor_style":"wood","floor_world_y":540,
  "platforms":[
    {"rect":(0,540,1800,80),"type":"floor"},
    {"rect":(0,0,1800,22),"type":"ceil"},
    {"rect":(0,0,22,620),"type":"wall"},
    {"rect":(1778,0,22,620),"type":"wall"},
    {"rect":(200,420,140,16),"type":"stone"},   # büfe üstü
    {"rect":(1440,420,160,16),"type":"stone"},
  ],
  "stairs":[],
  "doors":[
    {"rect":(22,380,72,160),"target_room":"giris_holu","target_spawn":(1860,480),"label":"Giriş Holü"},
    {"rect":(1706,380,72,160),"target_room":"kutuphane","target_spawn":(80,440),"label":"Kütüphane"},
    # Servis kapısı (mutfaktan gelen)
    {"rect":(860,460,52,80),"target_room":"mutfak","target_spawn":(1640,420),
     "label":"[Servis] Mutfak","secret":True},
  ],
  "decor":[
    {"type":"chandelier","rect":(860,22,130,140)},
    {"type":"dining_table","rect":(300,440,1200,100)},
    {"type":"fireplace","rect":(820,300,160,240),"kw":{"marble":False}},
    {"type":"window","rect":(200,40,100,260)},
    {"type":"window","rect":(1480,40,100,260)},
    {"type":"portrait","rect":(550,50,120,160)},
    {"type":"portrait","rect":(1100,50,120,160)},
    {"type":"sconce","rect":(380,180,30,50)},
    {"type":"sconce","rect":(800,180,30,50)},
    {"type":"sconce","rect":(1000,180,30,50)},
    {"type":"sconce","rect":(1380,180,30,50)},
    {"type":"clock","rect":(1600,330,65,210)},
    {"type":"carpet","rect":(250,520,1300,20),"kw":{"color":BORDO_M}},
    {"type":"bell_pull","rect":(1700,80,14,200)},
  ],
  "fire_sources":[(900,530,16)],
  "spawn":(80,480),
},

"kutuphane":{
  "name":"Kütüphane  (Zemin Kat)",
  "floor":"zemin",
  "wall_style":"dark_wood",
  "w":2000,"h":640,
  "wall_top":W1,"wall_bot":W0,"block_size":(50,25),
  "floor_style":"wood","floor_world_y":560,
  "platforms":[
    {"rect":(0,560,2000,80),"type":"floor"},
    {"rect":(0,0,2000,22),"type":"ceil"},
    {"rect":(0,0,22,640),"type":"wall"},
    {"rect":(1978,0,22,640),"type":"wall"},
    # Galeri katı
    {"rect":(100,320,450,18),"type":"stone"},
    {"rect":(650,360,380,18),"type":"stone"},
    {"rect":(1150,310,380,18),"type":"stone"},
    {"rect":(1640,340,320,18),"type":"stone"},
  ],
  "stairs":[],
  # Not: Galeri katına ulaşım platformlara zıplayarak sağlanır (E kapısı yok)
  "doors":[
    {"rect":(22,400,72,160),"target_room":"dining_room","target_spawn":(1700,480),"label":"Yemek Odası"},
    {"rect":(1906,400,72,160),"target_room":"giris_holu","target_spawn":(1800,480),"label":"Giriş Holü"},
    # Gizli kasa kapısı (kitaplığın arkasında)
    {"rect":(1050,380,52,80),"target_room":"gizli_gecit",
     "target_spawn":(80,340),"label":"Gizli Geçit","secret":True},
  ],
  "decor":[
    {"type":"chandelier","rect":(980,22,120,130)},
    {"type":"bookshelf","rect":(22,60,240,500)},
    {"type":"bookshelf","rect":(500,60,200,500)},
    {"type":"bookshelf","rect":(960,60,200,500)},
    {"type":"bookshelf","rect":(1420,60,200,500)},
    {"type":"bookshelf","rect":(1758,60,220,500)},
    {"type":"globe","rect":(660,450,80,100)},
    {"type":"clock","rect":(1640,360,65,200)},
    {"type":"portrait","rect":(770,80,110,145)},
    {"type":"portrait","rect":(1060,80,110,145)},
    {"type":"sconce","rect":(380,220,30,50)},
    {"type":"sconce","rect":(760,220,30,50)},
    {"type":"sconce","rect":(1180,220,30,50)},
    {"type":"sconce","rect":(1600,220,30,50)},
    {"type":"candelabra","rect":(640,490,30,70)},
    {"type":"candelabra","rect":(1300,490,30,70)},
    {"type":"carpet","rect":(200,540,1600,20),"kw":{"color":BORDO_D}},
    {"type":"bell_pull","rect":(1800,80,14,200)},
  ],
  "fire_sources":[(1000,545,14)],
  "spawn":(80,480),
},

"gizli_gecit":{
  "name":"Gizli Geçit",
  "floor":"zemin",
  "wall_style":"cellar",
  "w":800,"h":500,
  "wall_top":(20,16,12),"wall_bot":(12,10,8),"block_size":(44,22),
  "floor_style":"stone","floor_world_y":420,
  "platforms":[
    {"rect":(0,420,800,80),"type":"floor"},
    {"rect":(0,0,800,22),"type":"ceil"},
    {"rect":(0,0,22,500),"type":"wall"},
    {"rect":(778,0,22,500),"type":"wall"},
  ],
  "stairs":[
    {"rect":(580,280,180,140),"steps":5,"dir":"left",
     "target_room":"ust_koridor","target_spawn":(1600,460),"label":"Üst Kat [Gizli]"},
  ],
  "doors":[
    {"rect":(22,300,52,120),"target_room":"kutuphane","target_spawn":(1080,440),"label":"← Kütüphane","secret":True},
  ],
  "decor":[
    {"type":"sconce","rect":(380,140,28,44)},
    {"type":"portrait","rect":(200,80,90,120)},
  ],
  "fire_sources":[], "spawn":(80,360),
},

# ══════════════════════════════════════════════════════
# 1. KAT — AİLE ÖZEL ALANI
# ══════════════════════════════════════════════════════
"ust_koridor":{
  "name":"Üst Kat Koridoru  (1. Kat)",
  "floor":"birinci",
  "wall_style":"stone",
  "w":2600,"h":600,
  "wall_top":(20,16,24),"wall_bot":(30,24,36),"block_size":(54,27),
  "floor_style":"wood","floor_world_y":520,
  "platforms":[
    {"rect":(0,520,2600,80),"type":"floor"},
    {"rect":(0,0,2600,22),"type":"ceil"},
    {"rect":(0,0,22,600),"type":"wall"},
    {"rect":(2578,0,22,600),"type":"wall"},
    # Üst balustrade (korkuluk platformu)
    {"rect":(900,360,800,16),"type":"stone"},
    {"rect":(820,400,80,16),"type":"stone"},
    {"rect":(1700,400,80,16),"type":"stone"},
  ],
  "stairs":[
    # Ana merdiven iniş — 1.Kat → Zemin
    {"rect":(80,380,240,140),"steps":6,"dir":"right",
     "target_room":"giris_holu","target_spawn":(580,330),"label":"Zemin Kat  ↓"},
    # Dar servis merdiveni — 1.Kat → Çatı
    {"rect":(2320,360,180,160),"steps":6,"dir":"left",
     "target_room":"cati_koridor","target_spawn":(180,360),"label":"Çatı Katı  ↑"},
  ],
  "doors":[
    {"rect":(22,360,72,160),"target_room":"giyinme_odasi","target_spawn":(800,460),"label":"Giyinme Odası"},
    {"rect":(2506,360,72,160),"target_room":"master_bedroom","target_spawn":(80,480),"label":"Master Bedroom"},
    {"rect":(900,260,72,80),"target_room":"banyo","target_spawn":(80,400),"label":"Banyo"},
    {"rect":(1400,260,72,80),"target_room":"cocuk_odasi_1","target_spawn":(80,460),"label":"Çocuk Odası 1"},
    {"rect":(1700,260,72,80),"target_room":"cocuk_odasi_2","target_spawn":(80,460),"label":"Çocuk Odası 2"},
    # Gizli servis merdiveni kapısı
    {"rect":(1550,380,52,80),"target_room":"gizli_gecit","target_spawn":(700,360),
     "label":"[Servis] Gizli Geçit","secret":True},
  ],
  "decor":[
    {"type":"chandelier","rect":(1240,22,120,130)},
    {"type":"portrait","rect":(300,50,110,145)},
    {"type":"portrait","rect":(700,50,110,145)},
    {"type":"portrait","rect":(1600,50,110,145)},
    {"type":"portrait","rect":(2100,50,110,145)},
    {"type":"sconce","rect":(220,200,30,50)},
    {"type":"sconce","rect":(660,200,30,50)},
    {"type":"sconce","rect":(1180,200,30,50)},
    {"type":"sconce","rect":(1720,200,30,50)},
    {"type":"sconce","rect":(2260,200,30,50)},
    {"type":"armor","rect":(470,360,75,160)},
    {"type":"armor","rect":(2040,360,75,160)},
    {"type":"clock","rect":(2200,330,65,190)},
    {"type":"carpet","rect":(200,500,2200,20),"kw":{"color":BORDO_M}},
    {"type":"window","rect":(1400,30,100,220)},
    {"type":"bell_pull","rect":(1460,80,14,180)},
  ],
  "fire_sources":[], "spawn":(200,460),
},

"master_bedroom":{
  "name":"Master Bedroom  (1. Kat)",
  "floor":"birinci",
  "wall_style":"wallpaper_floral",
  "w":1800,"h":620,
  "wall_top":(22,16,28),"wall_bot":(16,12,20),"block_size":(50,25),
  "floor_style":"wood","floor_world_y":540,
  "platforms":[
    {"rect":(0,540,1800,80),"type":"floor"},
    {"rect":(0,0,1800,22),"type":"ceil"},
    {"rect":(0,0,22,620),"type":"wall"},
    {"rect":(1778,0,22,620),"type":"wall"},
    {"rect":(900,460,320,18),"type":"stone"},   # yatak yükseltmesi
    {"rect":(160,330,120,16),"type":"stone"},   # pencere pervazı
    {"rect":(1520,330,120,16),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(22,380,72,160),"target_room":"ust_koridor","target_spawn":(2440,460),"label":"Koridor"},
    {"rect":(1706,380,72,160),"target_room":"giyinme_odasi","target_spawn":(80,460),"label":"Giyinme Odası"},
  ],
  "decor":[
    {"type":"chandelier","rect":(860,22,100,120)},
    {"type":"canopy_bed","rect":(880,380,280,160)},
    {"type":"window","rect":(130,40,120,320)},
    {"type":"window","rect":(1550,40,120,320)},
    {"type":"fireplace","rect":(750,310,140,230),"kw":{"marble":True}},
    {"type":"portrait","rect":(520,50,130,170)},
    {"type":"portrait","rect":(1120,50,130,170)},
    {"type":"sconce","rect":(370,200,30,50)},
    {"type":"sconce","rect":(1360,200,30,50)},
    {"type":"candelabra","rect":(560,470,30,70)},
    {"type":"clock","rect":(330,350,60,190)},
    {"type":"carpet","rect":(260,520,1280,20),"kw":{"color":BORDO_M}},
    {"type":"bookshelf","rect":(1550,120,200,420)},
    {"type":"bell_pull","rect":(1680,80,14,200)},
  ],
  "fire_sources":[(820,520,14)],
  "spawn":(80,480),
},

"giyinme_odasi":{
  "name":"Giyinme Odası  (1. Kat)",
  "floor":"birinci",
  "wall_style":"wallpaper_floral",
  "w":900,"h":560,
  "wall_top":(25,18,30),"wall_bot":(18,13,22),"block_size":(44,22),
  "floor_style":"wood","floor_world_y":480,
  "platforms":[
    {"rect":(0,480,900,80),"type":"floor"},
    {"rect":(0,0,900,22),"type":"ceil"},
    {"rect":(0,0,22,560),"type":"wall"},
    {"rect":(878,0,22,560),"type":"wall"},
    {"rect":(200,360,160,14),"type":"stone"},   # gardırop üstü
    {"rect":(520,360,160,14),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(22,340,72,140),"target_room":"ust_koridor","target_spawn":(80,460),"label":"Koridor"},
    {"rect":(806,340,72,140),"target_room":"master_bedroom","target_spawn":(1640,460),"label":"Master Bedroom"},
  ],
  "decor":[
    {"type":"chandelier","rect":(420,22,85,100)},
    {"type":"window","rect":(350,40,100,200)},
    {"type":"portrait","rect":(120,60,100,130)},
    {"type":"sconce","rect":(200,160,28,44)},
    {"type":"sconce","rect":(620,160,28,44)},
    {"type":"bookshelf","rect":(680,120,200,360)},
    {"type":"carpet","rect":(150,460,600,20),"kw":{"color":LACI_M}},
    {"type":"bell_pull","rect":(780,80,14,160)},
    {"type":"candelabra","rect":(150,410,28,70)},
  ],
  "fire_sources":[], "spawn":(800,420),
},

"cocuk_odasi_1":{
  "name":"Çocuk Odası  (1. Kat)",
  "floor":"birinci",
  "wall_style":"wallpaper_floral",
  "w":1000,"h":560,
  "wall_top":(28,20,32),"wall_bot":(20,15,24),"block_size":(44,22),
  "floor_style":"wood","floor_world_y":480,
  "platforms":[
    {"rect":(0,480,1000,80),"type":"floor"},
    {"rect":(0,0,1000,22),"type":"ceil"},
    {"rect":(0,0,22,560),"type":"wall"},
    {"rect":(978,0,22,560),"type":"wall"},
    {"rect":(200,360,180,14),"type":"stone"},
    {"rect":(600,330,180,14),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(22,340,72,140),"target_room":"ust_koridor","target_spawn":(1340,460),"label":"Koridor"},
  ],
  "decor":[
    {"type":"chandelier","rect":(480,22,85,100)},
    {"type":"window","rect":(120,40,100,240)},
    {"type":"window","rect":(780,40,100,240)},
    {"type":"fireplace","rect":(440,320,120,160)},
    {"type":"sconce","rect":(280,160,28,44)},
    {"type":"sconce","rect":(660,160,28,44)},
    {"type":"portrait","rect":(380,50,100,130)},
    {"type":"carpet","rect":(150,460,700,20),"kw":{"color":ZUMRUT_M}},
    {"type":"bell_pull","rect":(880,80,14,160)},
    {"type":"candelabra","rect":(150,410,28,70)},
  ],
  "fire_sources":[(500,460,10)],
  "spawn":(80,420),
},

"cocuk_odasi_2":{
  "name":"Çocuk Odası 2  (1. Kat)",
  "floor":"birinci",
  "wall_style":"wallpaper_floral",
  "w":1000,"h":560,
  "wall_top":(28,20,32),"wall_bot":(20,15,24),"block_size":(44,22),
  "floor_style":"wood","floor_world_y":480,
  "platforms":[
    {"rect":(0,480,1000,80),"type":"floor"},
    {"rect":(0,0,1000,22),"type":"ceil"},
    {"rect":(0,0,22,560),"type":"wall"},
    {"rect":(978,0,22,560),"type":"wall"},
    {"rect":(200,360,180,14),"type":"stone"},
    {"rect":(600,340,180,14),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(22,340,72,140),"target_room":"ust_koridor","target_spawn":(1640,460),"label":"Koridor"},
  ],
  "decor":[
    {"type":"chandelier","rect":(480,22,85,100)},
    {"type":"window","rect":(120,40,100,240)},
    {"type":"window","rect":(780,40,100,240)},
    {"type":"fireplace","rect":(440,320,120,160)},
    {"type":"sconce","rect":(280,160,28,44)},
    {"type":"sconce","rect":(660,160,28,44)},
    {"type":"portrait","rect":(380,50,100,130)},
    {"type":"carpet","rect":(150,460,700,20),"kw":{"color":LACI_M}},
    {"type":"bell_pull","rect":(880,80,14,160)},
    {"type":"candelabra","rect":(150,410,28,70)},
  ],
  "fire_sources":[(500,460,10)],
  "spawn":(80,420),
},

"banyo":{
  "name":"Banyo  (1. Kat)",
  "floor":"birinci",
  "wall_style":"servants",
  "w":800,"h":520,
  "wall_top":(155,148,140),"wall_bot":(120,115,108),"block_size":(40,20),
  "floor_style":"tile","floor_world_y":440,
  "platforms":[
    {"rect":(0,440,800,80),"type":"floor"},
    {"rect":(0,0,800,22),"type":"ceil"},
    {"rect":(0,0,22,520),"type":"wall"},
    {"rect":(778,0,22,520),"type":"wall"},
    {"rect":(200,350,260,16),"type":"stone"},  # küvet platformu
  ],
  "stairs":[], "doors":[
    {"rect":(22,300,72,140),"target_room":"ust_koridor","target_spawn":(850,460),"label":"Koridor"},
  ],
  "decor":[
    {"type":"window","rect":(330,40,120,200)},
    {"type":"sconce","rect":(200,140,28,44)},
    {"type":"sconce","rect":(540,140,28,44)},
    {"type":"washtub","rect":(200,280,250,120)},
    {"type":"candelabra","rect":(560,370,28,70)},
    {"type":"bell_pull","rect":(680,80,14,140)},
  ],
  "fire_sources":[], "spawn":(80,380),
},

# ══════════════════════════════════════════════════════
# ÇATI KATI — HİZMETLİ ODALARI
# ══════════════════════════════════════════════════════
"cati_koridor":{
  "name":"Çatı Katı Koridoru",
  "floor":"cati",
  "wall_style":"servants",
  "w":1400,"h":480,
  "wall_top":(148,142,135),"wall_bot":(118,114,108),"block_size":(40,20),
  "floor_style":"wood","floor_world_y":400,
  "platforms":[
    {"rect":(0,400,1400,80),"type":"floor"},
    {"rect":(0,0,1400,22),"type":"ceil"},
    {"rect":(0,0,22,480),"type":"wall"},
    {"rect":(1378,0,22,480),"type":"wall"},
    # Çatı eğimi hissi (tavan daha alçak görünüm)
    {"rect":(0,0,1400,8),"type":"ceil"},
  ],
  "stairs":[
    # Alt kata iniş — dar servis merdiveni
    {"rect":(1160,260,160,140),"steps":5,"dir":"left",
     "target_room":"ust_koridor","target_spawn":(2360,460),"label":"Alt Kat  ↓"},
  ],
  "doors":[
    {"rect":(22,260,60,140),"target_room":"hizmetli_1","target_spawn":(80,360),"label":"Oda 1"},
    {"rect":(500,260,60,140),"target_room":"hizmetli_2","target_spawn":(80,360),"label":"Oda 2"},
    {"rect":(900,260,60,140),"target_room":"hizmetli_3","target_spawn":(80,360),"label":"Oda 3"},
    {"rect":(1240,260,60,140),"target_room":"depo","target_spawn":(80,340),"label":"Depo"},
    {"rect":(700,260,60,80),"target_room":"kule","target_spawn":(180,1260),"label":"Kule  ↑"},
  ],
  "decor":[
    {"type":"sconce","rect":(200,120,26,40)},
    {"type":"sconce","rect":(600,120,26,40)},
    {"type":"sconce","rect":(1000,120,26,40)},
    {"type":"carpet","rect":(100,380,1200,20),"kw":{"color":BORDO_D}},
  ],
  "fire_sources":[], "spawn":(180,340),
},

"hizmetli_1":{
  "name":"Hizmetli Odası 1  (Çatı)",
  "floor":"cati",
  "wall_style":"servants",
  "w":600,"h":440,
  "wall_top":(148,142,135),"wall_bot":(115,110,104),"block_size":(38,19),
  "floor_style":"wood","floor_world_y":360,
  "platforms":[
    {"rect":(0,360,600,80),"type":"floor"},
    {"rect":(0,0,600,22),"type":"ceil"},
    {"rect":(0,0,22,440),"type":"wall"},
    {"rect":(578,0,22,440),"type":"wall"},
  ],
  "stairs":[], "doors":[
    {"rect":(514,220,60,140),"target_room":"cati_koridor","target_spawn":(80,340),"label":"Koridor"},
  ],
  "decor":[
    {"type":"window","rect":(240,40,100,160)},
    {"type":"sconce","rect":(150,140,26,40)},
    {"type":"candelabra","rect":(300,290,26,70)},
    {"type":"portrait","rect":(130,60,80,105)},
  ],
  "fire_sources":[], "spawn":(80,300),
},

"hizmetli_2":{
  "name":"Hizmetli Odası 2  (Çatı)",
  "floor":"cati",
  "wall_style":"servants",
  "w":600,"h":440,
  "wall_top":(148,142,135),"wall_bot":(115,110,104),"block_size":(38,19),
  "floor_style":"wood","floor_world_y":360,
  "platforms":[
    {"rect":(0,360,600,80),"type":"floor"},
    {"rect":(0,0,600,22),"type":"ceil"},
    {"rect":(0,0,22,440),"type":"wall"},
    {"rect":(578,0,22,440),"type":"wall"},
  ],
  "stairs":[], "doors":[
    {"rect":(514,220,60,140),"target_room":"cati_koridor","target_spawn":(540,340),"label":"Koridor"},
  ],
  "decor":[
    {"type":"window","rect":(240,40,100,160)},
    {"type":"sconce","rect":(150,140,26,40)},
    {"type":"candelabra","rect":(300,290,26,70)},
  ],
  "fire_sources":[], "spawn":(80,300),
},

"hizmetli_3":{
  "name":"Hizmetli Odası 3  (Çatı)",
  "floor":"cati",
  "wall_style":"servants",
  "w":600,"h":440,
  "wall_top":(148,142,135),"wall_bot":(115,110,104),"block_size":(38,19),
  "floor_style":"wood","floor_world_y":360,
  "platforms":[
    {"rect":(0,360,600,80),"type":"floor"},
    {"rect":(0,0,600,22),"type":"ceil"},
    {"rect":(0,0,22,440),"type":"wall"},
    {"rect":(578,0,22,440),"type":"wall"},
  ],
  "stairs":[], "doors":[
    {"rect":(514,220,60,140),"target_room":"cati_koridor","target_spawn":(940,340),"label":"Koridor"},
  ],
  "decor":[
    {"type":"window","rect":(240,40,100,160)},
    {"type":"sconce","rect":(150,140,26,40)},
  ],
  "fire_sources":[], "spawn":(80,300),
},

"depo":{
  "name":"Depo  (Çatı)",
  "floor":"cati",
  "wall_style":"cellar",
  "w":700,"h":440,
  "wall_top":(25,20,15),"wall_bot":(15,12,8),"block_size":(44,22),
  "floor_style":"wood","floor_world_y":360,
  "platforms":[
    {"rect":(0,360,700,80),"type":"floor"},
    {"rect":(0,0,700,22),"type":"ceil"},
    {"rect":(0,0,22,440),"type":"wall"},
    {"rect":(678,0,22,440),"type":"wall"},
    {"rect":(200,270,180,14),"type":"stone"},
    {"rect":(480,270,180,14),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(614,220,60,140),"target_room":"cati_koridor","target_spawn":(1280,340),"label":"Koridor"},
  ],
  "decor":[
    {"type":"pantry","rect":(80,60,180,300)},
    {"type":"pantry","rect":(440,60,200,300)},
    {"type":"sconce","rect":(300,120,26,40)},
    {"type":"coal","rect":(300,290,150,70)},
  ],
  "fire_sources":[], "spawn":(80,300),
},

# ══════════════════════════════════════════════════════
# KULE
# ══════════════════════════════════════════════════════
"kule":{
  "name":"Kule  (Turret)",
  "floor":"ozel",
  "wall_style":"stone",
  "w":700,"h":1500,
  "wall_top":(12,9,18),"wall_bot":(20,16,28),"block_size":(46,23),
  "floor_style":"stone","floor_world_y":1440,
  "platforms":[
    {"rect":(0,1440,700,60),"type":"floor"},
    {"rect":(0,0,700,22),"type":"ceil"},
    {"rect":(0,0,22,1500),"type":"wall"},
    {"rect":(678,0,22,1500),"type":"wall"},
    # Sarmal basamaklar
    {"rect":(50,1320,280,16),"type":"stone"},
    {"rect":(370,1200,280,16),"type":"stone"},
    {"rect":(50,1080,280,16),"type":"stone"},
    {"rect":(370,960,280,16),"type":"stone"},
    {"rect":(50,840,280,16),"type":"stone"},
    {"rect":(370,720,280,16),"type":"stone"},
    {"rect":(50,600,280,16),"type":"stone"},
    {"rect":(370,480,280,16),"type":"stone"},
    {"rect":(50,360,280,16),"type":"stone"},
    {"rect":(370,240,280,16),"type":"stone"},
    {"rect":(50,120,280,16),"type":"stone"},
  ],
  "stairs":[], "doors":[
    {"rect":(22,1360,64,80),"target_room":"cati_koridor","target_spawn":(740,340),"label":"Koridor"},
  ],
  "decor":[
    {"type":"window","rect":(260,50,180,220)},
    {"type":"window","rect":(260,550,180,140)},
    {"type":"window","rect":(260,950,180,140)},
    {"type":"window","rect":(260,1350,180,80)},
    {"type":"sconce","rect":(580,1300,28,44)},
    {"type":"sconce","rect":(90,1100,28,44)},
    {"type":"sconce","rect":(580,900,28,44)},
    {"type":"sconce","rect":(90,700,28,44)},
    {"type":"sconce","rect":(580,500,28,44)},
    {"type":"portrait","rect":(540,300,95,125)},
    {"type":"candelabra","rect":(310,1370,30,70)},
    {"type":"globe","rect":(450,80,80,100)},
  ],
  "fire_sources":[], "spawn":(180,1260),
},

}  # ROOM_DEFS sonu

# Merdiven basamaklarını platform listesine ekle
def _stair_plats(s):
    rx,ry,rw,rh=s["rect"]; n=s.get("steps",8); d=s.get("dir","right")
    sw2=rw//n; sh2=rh//n; out=[]
    for i in range(n):
        bx=rx+i*sw2 if d=="right" else rx+rw-(i+1)*sw2
        by=ry+rh-(i+1)*sh2
        out.append({"rect":(bx,by,sw2,sh2),"type":"stone"})
    return out

for rd in ROOM_DEFS.values():
    for s in rd.get("stairs",[]):
        rd["platforms"].extend(_stair_plats(s))

# ══════════════════════════════════════════════════════
#  OYUNCU
# ══════════════════════════════════════════════════════
class Player:
    __slots__=("wx","wy","vx","vy","on_ground","facing",
               "anim_tick","squash","stretch","interact_ev")
    def __init__(self,wx,wy):
        self.wx=float(wx); self.wy=float(wy)
        self.vx=self.vy=0.0; self.on_ground=False; self.facing=1
        self.anim_tick=0.0; self.squash=1.0; self.stretch=1.0
        self.interact_ev=False

    def update(self,dt,platforms,keys,ie):
        self.interact_ev=ie; self.vx=0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.vx=-P_SPEED; self.facing=-1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx= P_SPEED; self.facing= 1
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy=JUMP_V; self.on_ground=False; self.stretch=1.28
        self.vy+=GRAV*dt
        # X
        self.wx+=self.vx*dt
        rx=pygame.Rect(int(self.wx),int(self.wy),PW,PH)
        for p in platforms:
            if p["type"]!="wall": continue
            pr=pygame.Rect(*p["rect"])
            if rx.colliderect(pr):
                self.wx=pr.left-PW if self.vx>0 else pr.right
                self.vx=0; rx.x=int(self.wx)
        # Y
        self.on_ground=False; self.wy+=self.vy*dt
        ry=pygame.Rect(int(self.wx),int(self.wy),PW,PH)
        for p in platforms:
            if p["type"]=="wall": continue
            pr=pygame.Rect(*p["rect"])
            if not ry.colliderect(pr): continue
            if self.vy>=0:
                self.wy=pr.top-PH
                if self.vy>180: self.squash=0.75
                self.vy=0; self.on_ground=True
            elif p["type"]=="ceil":
                self.wy=pr.bottom; self.vy=0
            ry.y=int(self.wy)
        if self.on_ground and abs(self.vx)>1: self.anim_tick+=dt*7
        else: self.anim_tick=0.0
        self.squash+=(1-self.squash)*min(1,dt*16)
        self.stretch+=(1-self.stretch)*min(1,dt*16)

    def get_rect(self): return pygame.Rect(int(self.wx),int(self.wy),PW,PH)

    def draw(self,surf,cx,cy):
        sx=int(self.wx-cx); sy=int(self.wy-cy)
        dw=int(PW*self.squash); dh=int(PH*self.stretch)
        dx=sx+(PW-dw)//2; dy=sy+(PH-dh)
        grad(surf,pygame.Rect(dx,dy,dw,dh),lc(P_COAT,(45,35,28),0.3),P_COAT)
        pygame.draw.rect(surf,P_SKIN,(dx+dw//4,dy,dw//2,int(dh*0.28)))
        hr=int(dw*0.52)
        pygame.draw.circle(surf,P_SKIN,(dx+dw//2,dy-hr//2),hr)
        pygame.draw.arc(surf,P_HAIR,pygame.Rect(dx+dw//2-hr,dy-hr,hr*2,hr*2),0,math.pi,4)
        ex=dx+dw//2+self.facing*int(hr*0.4)
        pygame.draw.circle(surf,(50,35,20),(ex,dy-hr//2+2),3)
        pygame.draw.circle(surf,(220,200,170),(ex-self.facing,dy-hr//2+2),1)
        lk=int(math.sin(self.anim_tick)*5); ly=sy+PH-6
        pygame.draw.line(surf,W0,(sx+PW//3,ly),(sx+PW//3,ly+10+lk),3)
        pygame.draw.line(surf,W0,(sx+2*PW//3,ly),(sx+2*PW//3,ly+10-lk),3)
        pygame.draw.rect(surf,W1,(sx+PW//3-3,ly+8+lk,10,4))
        pygame.draw.rect(surf,W1,(sx+2*PW//3-3,ly+8-lk,10,4))

# ══════════════════════════════════════════════════════
#  KAMERA
# ══════════════════════════════════════════════════════
class Camera:
    __slots__=("x","y")
    def __init__(self): self.x=self.y=0.0
    def update(self,pwx,pwy,rw,rh,dt):
        tx=clamp(pwx-SW*0.38,0,max(0,rw-SW))
        ty=clamp(pwy-SH*0.52,0,max(0,rh-SH))
        self.x+=(tx-self.x)*min(1,CAM_LX*dt*60)
        self.y+=(ty-self.y)*min(1,CAM_LY*dt*60)

# ══════════════════════════════════════════════════════
#  ETKİLEŞİM
# ══════════════════════════════════════════════════════
def check_interact(player,rdef):
    if not player.interact_ev: return None
    pc=player.get_rect().center
    for d in rdef.get("doors",[]):
        rx,ry,rw,rh=d["rect"]
        if math.hypot(pc[0]-(rx+rw//2),pc[1]-(ry+rh//2))<INTER_D:
            return d["target_room"],d["target_spawn"]
    for s in rdef.get("stairs",[]):
        if "target_room" not in s: continue
        rx,ry,rw,rh=s["rect"]
        if math.hypot(pc[0]-(rx+rw//2),pc[1]-(ry+rh//2))<INTER_D*1.4:
            return s["target_room"],s["target_spawn"]
    return None

def get_near(player,rdef):
    pc=player.get_rect().center; nd=[]; ns=[]
    for d in rdef.get("doors",[]):
        rx,ry,rw,rh=d["rect"]
        if math.hypot(pc[0]-(rx+rw//2),pc[1]-(ry+rh//2))<INTER_D*1.8: nd.append(d)
    for s in rdef.get("stairs",[]):
        if "target_room" not in s: continue
        rx,ry,rw,rh=s["rect"]
        if math.hypot(pc[0]-(rx+rw//2),pc[1]-(ry+rh//2))<INTER_D*2: ns.append(s)
    return nd,ns

# ══════════════════════════════════════════════════════
#  FADE
# ══════════════════════════════════════════════════════
class Fade:
    __slots__=("a","dir","active")
    def __init__(self): self.a=0; self.dir=1; self.active=False
    def start(self): self.active=True; self.a=0; self.dir=1
    def update(self,dt):
        if not self.active: return False
        self.a+=self.dir*int(700*dt)
        if self.dir==1 and self.a>=255: self.a=255; self.dir=-1; return True
        if self.dir==-1 and self.a<=0: self.a=0; self.active=False
        return False
    def draw(self,surf):
        if self.active and self.a>0:
            alpha_rect(surf,(0,0,0),self.a,pygame.Rect(0,0,SW,SH))

# ══════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════
FLOOR_LABEL={"bodrum":"▼ Bodrum Kat","zemin":"● Zemin Kat",
             "birinci":"▲ 1. Kat","cati":"▲▲ Çatı Katı","ozel":"◆ Özel"}
_ui_s=None; _ui_f=0; _ui_room=""

def render_ui(surf,room_id,fps,debug,player,cam):
    global _ui_s,_ui_f,_ui_room
    _ui_f+=1
    if _ui_s is None or _ui_f%10==0 or room_id!=_ui_room:
        _ui_room=room_id
        _ui_s=pygame.Surface((SW,56),pygame.SRCALPHA)
        _ui_s.fill((0,0,0,155))
        pygame.draw.line(_ui_s,(100,85,55,200),(0,0),(SW,0),1)
        rd=ROOM_DEFS.get(room_id,{})
        rn=rd.get("name",room_id)
        fl=FLOOR_LABEL.get(rd.get("floor",""),"")
        s1=F_MD.render(f"✦  {rn}",True,C_UI)
        s2=F_IT.render(fl,True,(150,135,100))
        ctrl=F_SM.render("A/D: Yürü  |  W/Space: Zıpla  |  E: Etkileşim  |  F12: Debug",True,(120,108,80))
        _ui_s.blit(s1,(20,8)); _ui_s.blit(s2,(20,32))
        _ui_s.blit(ctrl,(SW-ctrl.get_width()-18,20))
    surf.blit(_ui_s,(0,SH-56))
    if debug:
        lines=[f"[F12 DEBUG]",f"  oda: {room_id}",
               f"  wx/wy: {player.wx:.0f}/{player.wy:.0f}",
               f"  vy:{player.vy:.0f}  zemin:{player.on_ground}",
               f"  fps:{fps:.0f}  cam:{cam.x:.0f}/{cam.y:.0f}"]
        for i,l in enumerate(lines):
            surf.blit(F_SM.render(l,True,C_DBG),(SW-265,10+i*19))

# ══════════════════════════════════════════════════════
#  ANA DÖNGÜ
# ══════════════════════════════════════════════════════
def main():
    global _ft
    cur_id="giris_holu"; rdef=ROOM_DEFS[cur_id]
    player=Player(*rdef["spawn"]); camera=Camera(); fade=Fade()
    pending=None; debug=False
    camera.x=clamp(player.wx-SW*0.38,0,max(0,rdef["w"]-SW))
    camera.y=clamp(player.wy-SH*0.52,0,max(0,rdef["h"]-SH))

    floors={"bodrum":0,"zemin":0,"birinci":0,"cati":0,"ozel":0}
    for rd in ROOM_DEFS.values(): floors[rd.get("floor","ozel")]+=1
    print(f"[ASHFORD MANOR  1887]  {len(ROOM_DEFS)} oda yüklendi.")
    for k,v in floors.items():
        if v: print(f"  {FLOOR_LABEL.get(k,k):28s}: {v} oda")
    print("  A/D yürü | W/Space zıpla | E etkileşim | F12 debug | ESC çık")

    BACK_D={"window","carpet","bookshelf","clock"}
    FORE_D={"fireplace","portrait","candelabra","sconce","chandelier",
            "armor","piano","dining_table","iron_range","canopy_bed",
            "globe","pantry","washtub","bell_pull","coal"}

    running=True
    while running:
        dt=min(clock.tick(FPS)/1000.0,0.05); _ft+=dt
        ie=False
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: running=False
                if ev.key==pygame.K_F12: debug=not debug
                if ev.key==pygame.K_e: ie=True

        keys=pygame.key.get_pressed()
        if not fade.active:
            player.update(dt,rdef["platforms"],keys,ie)
            camera.update(player.wx,player.wy,rdef["w"],rdef["h"],dt)
            res=check_interact(player,rdef)
            if res:
                pending=res; fade.start()
                print(f"  [→] {pending[0]}")

        if fade.update(dt) and pending:
            cur_id=pending[0]; rdef=ROOM_DEFS[cur_id]
            player.wx=float(pending[1][0]); player.wy=float(pending[1][1])
            player.vx=player.vy=0.0; player.on_ground=False
            camera.x=clamp(player.wx-SW*0.38,0,max(0,rdef["w"]-SW))
            camera.y=clamp(player.wy-SH*0.52,0,max(0,rdef["h"]-SH))
            pending=None

        nd,ns=get_near(player,rdef); cx,cy=camera.x,camera.y

        # ── RENDER ─────────────────────────────────────
        # Z-0/1: Arkaplan
        draw_room_bg(surf=screen,room=rdef,cx=cx,cy=cy)

        # Z-2: Arka dekorlar
        for d in rdef["decor"]:
            if d["type"] in BACK_D: draw_decor(screen,d,cx,cy)

        # Z-3: Platformlar
        fstyle=rdef.get("floor_style","wood")
        for p in rdef["platforms"]:
            rx,ry,rw,rh=p["rect"]; pt=p["type"]
            if   pt=="floor": draw_floor(screen,rx,ry,rw,rh,cx,cy,fstyle)
            elif pt in ("stone","ceil"): draw_stone_plat(screen,rx,ry,rw,rh,cx,cy)
            elif pt=="wall":  draw_wall_col(screen,rx,ry,rw,rh,cx,cy)

        # Z-3b: Merdivenler
        for s in rdef.get("stairs",[]):
            if "target_room" in s:
                draw_staircase(screen,s,cx,cy,s in ns)

        # Z-4: Kapılar
        for d in rdef.get("doors",[]): draw_door(screen,d,cx,cy,d in nd)

        # Z-4b: Ön dekorlar
        for d in rdef["decor"]:
            if d["type"] in FORE_D: draw_decor(screen,d,cx,cy)

        # Z-5: Oyuncu
        player.draw(screen,cx,cy)

        # Z-6: Ateş partikülleri
        _draw_flames(screen,dt,cx,cy,rdef.get("fire_sources",[]))

        fade.draw(screen)
        render_ui(screen,cur_id,clock.get_fps(),debug,player,camera)
        pygame.display.flip()

    gc.enable(); gc.collect(); pygame.quit(); sys.exit()

if __name__=="__main__":
    main()