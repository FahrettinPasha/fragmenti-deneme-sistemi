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
PW, PH   = 44, 84
P_SPEED  = 200.0
JUMP_V   = -560.0
GRAV     = 1400.0
CAM_LX   = 0.09
CAM_LY   = 0.09
INTER_D  = 76

# Desert Eagle
DE_DAMAGE   = 80
DE_INTERVAL = 0.35
DE_SPEED    = 900.0
DE_MAG      = 7
DE_RELOAD_T = 1.8
# Ray Düşmanı
RE_SPEED    = 75.0
RE_HP_MAX   = 100
RE_W, RE_H  = 40, 76

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
# Desert Eagle / mermi
BULLET_COL=(255,230,80); MUZZLE_COL=(255,200,60)
DE_STEEL=(55,55,60); DE_GRIP=(30,22,12)
# Ray düşmanı
EN_COAT=(60,15,15); EN_SKIN=(185,155,125); EN_HAIR=(15,10,5); EN_LIGHT=(100,30,30)

gc.collect(); gc.disable()

pygame.init()
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption(TITLE)
clock  = pygame.time.Clock()
pygame.mouse.set_visible(False)
game_surf = pygame.Surface((SW, SH))   # tüm dünya buraya çizilir, zoom ile screen'e basılır
_zoom     = 1.0                         # mevcut zoom (LERP ile güncellenir)
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

def _rot_rect(cx,cy,w,h,angle):
    """Döndürülmüş dikdörtgenin 4 köşe noktası (int tuple list)."""
    ca,sa=math.cos(angle),math.sin(angle)
    hw,hh=w/2,h/2
    return [(int(cx+dx*ca-dy*sa),int(cy+dx*sa+dy*ca))
            for (dx,dy) in [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]]

# ══════════════════════════════════════════════════════
#  ALEV PARTİKÜL HAVUZU
# ══════════════════════════════════════════════════════
class _FP:
    __slots__=("x","y","vx","vy","life","ml","r","active")
    def __init__(self): self.active=False

_fp_pool=[_FP() for _ in range(100)]

# ══════════════════════════════════════════════════════
#  MERMİ HAVUZU  –  CCD balistik (AGENT.MD uyumlu)
# ══════════════════════════════════════════════════════
class _Bullet:
    __slots__=("wx","wy","ox","oy","vx","vy","active")
    def __init__(self): self.active=False

_bullet_pool=[_Bullet() for _ in range(24)]

def _fire_bullet(wx,wy,angle):
    for b in _bullet_pool:
        if not b.active:
            b.wx=float(wx); b.wy=float(wy)
            b.ox=float(wx); b.oy=float(wy)
            b.vx=DE_SPEED*math.cos(angle)
            b.vy=DE_SPEED*math.sin(angle)
            b.active=True; return

def _update_bullets(dt,platforms,enemy_pool,cur_id,floor_y):
    for b in _bullet_pool:
        if not b.active: continue
        b.ox=b.wx; b.oy=b.wy
        b.wx+=b.vx*dt; b.wy+=b.vy*dt
        if b.wx<-400 or b.wx>12000 or b.wy<-400 or b.wy>floor_y+200:
            b.active=False; continue
        dist=math.hypot(b.wx-b.ox,b.wy-b.oy)
        steps=max(1,int(dist/4))
        dx2=(b.wx-b.ox)/steps; dy2=(b.wy-b.oy)/steps
        hit=False
        for s in range(steps):
            cx_=b.ox+dx2*s; cy_=b.oy+dy2*s
            tr=pygame.Rect(int(cx_)-3,int(cy_)-3,6,6)
            for p in platforms:
                if p["type"]=="wall" and tr.colliderect(pygame.Rect(*p["rect"])):
                    b.active=False; hit=True; break
            if hit: break
            for e in enemy_pool:
                if not e.active or e.room_id!=cur_id: continue
                if tr.colliderect(pygame.Rect(int(e.wx),int(e.wy),RE_W,RE_H)):
                    e.hp-=DE_DAMAGE; e.hit_flash=0.20
                    if e.hp<=0:
                        _spawn_ragdoll(e.wx,e.wy,floor_y,b.vx*0.25)
                        e.active=False
                    b.active=False; hit=True; break
            if hit: break

def _draw_bullets(surf,cx,cy):
    for b in _bullet_pool:
        if not b.active: continue
        sx=int(b.wx-cx); sy=int(b.wy-cy)
        angle=math.atan2(b.vy,b.vx)
        pts=_rot_rect(sx,sy,14,4,angle)
        pygame.draw.polygon(surf,BULLET_COL,pts)
        alpha_rect(surf,MUZZLE_COL,28,pygame.Rect(sx-12,sy-6,24,12))

# ══════════════════════════════════════════════════════
#  RAGDOLL FİZİK SİSTEMİ  (agent.md: pool, dt, sıfır alloc)
# ══════════════════════════════════════════════════════
class _RagPart:
    __slots__=("wx","wy","vx","vy","rot","rot_vel","life","ml",
               "shape","col","sz","floor_y","active")
    def __init__(self): self.active=False

_rag_pool=[_RagPart() for _ in range(100)]   # 5 parça × 20 düşman

def _rag_spawn(wx,wy,floor_y,ivx,ivy,shape,col,sz):
    for p in _rag_pool:
        if not p.active:
            p.wx=float(wx); p.wy=float(wy)
            p.vx=float(ivx); p.vy=float(ivy)
            p.rot=rng.uniform(0,math.pi*2)
            p.rot_vel=rng.uniform(-9,9)
            p.ml=rng.uniform(2.2,3.8); p.life=p.ml
            p.shape=shape; p.col=col; p.sz=sz
            p.floor_y=float(floor_y); p.active=True; return

def _spawn_ragdoll(ex,ey,floor_y,impact_vx):
    """Düşman ölünce 5 parça fırlat."""
    bx=ex+RE_W/2; by=ey+RE_H/2
    iv=impact_vx
    # baş
    _rag_spawn(bx, ey-4,          floor_y,
               iv*0.5+rng.uniform(-40,40), rng.uniform(-340,-460),
               0, EN_SKIN, 7)
    # gövde
    _rag_spawn(bx, ey+RE_H*0.35,  floor_y,
               iv*0.3+rng.uniform(-20,20), rng.uniform(-200,-310),
               1, EN_COAT, (RE_W,int(RE_H*0.45)))
    # sol bacak
    _rag_spawn(ex+RE_W*0.3, ey+RE_H*0.75, floor_y,
               iv*0.2+rng.uniform(-30,-10), rng.uniform(-80,-160),
               2, lc(EN_COAT,(0,0,0),0.5), 16)
    # sağ bacak
    _rag_spawn(ex+RE_W*0.7, ey+RE_H*0.75, floor_y,
               iv*0.2+rng.uniform(10,30),  rng.uniform(-80,-160),
               2, lc(EN_COAT,(0,0,0),0.5), 16)
    # kol
    _rag_spawn(bx, ey+RE_H*0.3,   floor_y,
               iv*0.6+rng.uniform(-50,50), rng.uniform(-260,-380),
               2, EN_SKIN, 12)

def _update_ragdolls(dt):
    for p in _rag_pool:
        if not p.active: continue
        p.life-=dt
        if p.life<=0: p.active=False; continue
        p.vy+=GRAV*dt
        p.wx+=p.vx*dt; p.wy+=p.vy*dt
        p.rot+=p.rot_vel*dt
        # zemin çarpışması + zıplama
        if p.wy>=p.floor_y:
            p.wy=p.floor_y
            p.vy*=-0.32
            p.vx*=0.78
            p.rot_vel*=0.65
            if abs(p.vy)<18: p.vy=0
        # yatay sönüm
        p.vx*=max(0.0, 1-dt*1.1)

def _draw_ragdolls(surf,cx,cy):
    for p in _rag_pool:
        if not p.active: continue
        sx=int(p.wx-cx); sy=int(p.wy-cy)
        if sx<-120 or sx>SW+120: continue
        # son %35'te solar
        fade_t=p.life/p.ml
        if fade_t<0.35:
            if int(_ft*18)%2==0: continue  # blink
        if p.shape==0:          # ── baş (daire)
            r=p.sz
            pygame.draw.circle(surf,p.col,(sx,sy),r)
            pygame.draw.arc(surf,EN_HAIR,
                pygame.Rect(sx-r,sy-r,r*2,r*2),0,math.pi,3)
            ex2=sx+int(math.cos(p.rot)*r*0.45)
            ey2=sy+int(math.sin(p.rot)*r*0.45)
            pygame.draw.circle(surf,(160,25,25),(ex2,ey2),2)
        elif p.shape==1:        # ── gövde (dönen dikdörtgen)
            w,h=p.sz
            pts=_rot_rect(sx,sy,w,h,p.rot)
            pygame.draw.polygon(surf,p.col,pts)
            pygame.draw.polygon(surf,lc(p.col,(200,200,200),0.25),pts,1)
        elif p.shape==2:        # ── uzuv (çizgi)
            ln=p.sz
            x1=sx+int(math.cos(p.rot)*ln//2); y1=sy+int(math.sin(p.rot)*ln//2)
            x2=sx-int(math.cos(p.rot)*ln//2); y2=sy-int(math.sin(p.rot)*ln//2)
            pygame.draw.line(surf,p.col,(x1,y1),(x2,y2),3)

# ══════════════════════════════════════════════════════
#  DESERT EAGLE
# ══════════════════════════════════════════════════════
class DesertEagle:
    __slots__=("ammo","reloading","reload_timer","fire_timer","muzzle_flash","recoil","body_recoil")
    def __init__(self):
        self.ammo=DE_MAG; self.reloading=False
        self.reload_timer=0.0; self.fire_timer=0.0
        self.muzzle_flash=0.0; self.recoil=0.0; self.body_recoil=0.0

    def update(self,dt,fire,reload,player,aim_angle):
        if self.reloading:
            self.reload_timer-=dt
            if self.reload_timer<=0:
                self.ammo=DE_MAG; self.reloading=False
        if self.fire_timer>0: self.fire_timer-=dt
        if self.muzzle_flash>0: self.muzzle_flash-=dt*10
        if self.recoil>0:      self.recoil-=dt*9
        if self.body_recoil>0: self.body_recoil-=dt*7
        if reload and not self.reloading and self.ammo<DE_MAG:
            self.reloading=True; self.reload_timer=DE_RELOAD_T
        if fire and not self.reloading and self.ammo>0 and self.fire_timer<=0:
            sh_wx=player.wx+PW/2; sh_wy=player.wy+PH*0.32
            muz_x=sh_wx+math.cos(aim_angle)*30
            muz_y=sh_wy+math.sin(aim_angle)*30
            _fire_bullet(muz_x,muz_y,aim_angle)
            self.ammo-=1; self.fire_timer=DE_INTERVAL
            self.muzzle_flash=0.20; self.recoil=0.32; self.body_recoil=0.30
            # Geri tepme: atış yönünün TAM TERSİ
            rf = 42 if player.on_ground else 20
            player.vx += -math.cos(aim_angle)*rf
            player.vy += -math.sin(aim_angle)*rf*0.35
            # Lean: atış yönünün tersine eğil
            player.lean        = -math.cos(aim_angle) * player.facing * 0.9
            player.recoil_tilt = 0.85
            return True
        return False

    def draw(self,surf,player,cx,cy,aim_angle):
        sx=int(player.wx-cx); sy=int(player.wy-cy)
        f=player.facing
        lean_px=int(player.lean*8)
        tilt_py=int(player.recoil_tilt*5)

        # Omuz noktası (lean/tilt ile birlikte hareket eder)
        shx=sx+PW//2+lean_px
        shy=sy+int(PH*0.30)-tilt_py

        ca=math.cos(aim_angle); sa=math.sin(aim_angle)

        # ── 2-segment IK: omuz → dirsek → bilek
        L1,L2=22,20                        # uzatıldı
        reach=(L1+L2)*0.86
        rec=self.recoil

        # Bilek hedefi — recoil silahı geri çeker
        wx_t=shx+ca*(reach-rec*14)
        wy_t=shy+sa*(reach-rec*14)

        # Cosine rule → dirsek noktası
        d2=math.hypot(wx_t-shx,wy_t-shy)
        d2=clamp(d2,abs(L1-L2)+0.5,L1+L2-0.5)
        cos_a=clamp((d2*d2+L1*L1-L2*L2)/(2*d2*L1),-1.0,1.0)
        a1=math.acos(cos_a)
        base_ang=math.atan2(wy_t-shy,wx_t-shx)
        # Dirsek her zaman AŞAĞI bükülür (f yönünden bağımsız)
        elbow_ang=base_ang+a1
        ex_=int(shx+math.cos(elbow_ang)*L1)
        ey_=int(shy+math.sin(elbow_ang)*L1)
        wx_i=int(wx_t); wy_i=int(wy_t)

        # ── İSKELET KOL (nişan kolu) ──
        C_BONE  = (195,225,255)
        C_GLOW  = ( 80,160,255)
        _bone(surf,(shx,shy),(ex_,ey_), 4,3, C_BONE)
        _bone(surf,(ex_,ey_),(wx_i,wy_i),3,2, C_BONE)
        _jnt(surf,(shx,shy), 4, C_GLOW)
        _jnt(surf,(ex_,ey_), 5, C_GLOW)   # dirsek büyük
        _jnt(surf,(wx_i,wy_i),3, C_GLOW)

        # ── Silah (bilek noktasından)
        rcx=wx_i; rcy=wy_i
        tip_x=int(rcx+ca*22); tip_y=int(rcy+sa*22)
        # Gövde
        body_pts=_rot_rect(rcx,rcy,34,9,aim_angle)
        pygame.draw.polygon(surf,DE_STEEL,body_pts)
        pygame.draw.polygon(surf,lc(DE_STEEL,(230,230,230),0.3),body_pts,1)
        # Sürgü
        slide_pts=_rot_rect(int(rcx+ca*4),int(rcy+sa*4),26,5,aim_angle)
        pygame.draw.polygon(surf,lc(DE_STEEL,(160,160,160),0.18),slide_pts)
        # Kabza — facing yönüne göre açı çevrilir
        grip_pts=_rot_rect(int(rcx-ca*9),int(rcy-sa*9)+5,10,14,aim_angle+f*0.22)
        pygame.draw.polygon(surf,DE_GRIP,grip_pts)
        pygame.draw.polygon(surf,lc(DE_GRIP,(120,90,50),0.4),grip_pts,1)
        # Namlu ucu
        pygame.draw.circle(surf,(30,30,30),(tip_x,tip_y),4)
        pygame.draw.circle(surf,(10,10,10),(tip_x,tip_y),2)

        # ── Muzzle flash
        if self.muzzle_flash>0:
            t=self.muzzle_flash/0.20
            r2=max(2,int(16*t))
            alpha_rect(surf,FL_A,int(210*t),pygame.Rect(tip_x-r2*2,tip_y-r2*2,r2*4,r2*4))
            pygame.draw.circle(surf,FL_B,(tip_x,tip_y),r2)
            pygame.draw.circle(surf,FL_A,(tip_x,tip_y),r2//2)

# ══════════════════════════════════════════════════════
#  RAY DÜŞMANI  (RailEnemy)
# ══════════════════════════════════════════════════════
class RailEnemy:
    __slots__=("wx","wy","vx","hp","facing","rail_x1","rail_x2",
               "hit_flash","anim_tick","active","room_id")

    def __init__(self): self.active=False

    def spawn(self,wx,wy,rail_x1,rail_x2,room_id):
        self.wx=float(wx); self.wy=float(wy)
        self.vx=RE_SPEED; self.hp=RE_HP_MAX; self.facing=1
        self.rail_x1=float(rail_x1); self.rail_x2=float(rail_x2)
        self.hit_flash=0.0; self.anim_tick=0.0
        self.active=True; self.room_id=room_id

    def update(self,dt):
        if not self.active: return
        if self.hp<=0: self.active=False; return
        self.wx+=self.vx*dt
        if self.wx>=self.rail_x2:
            self.wx=self.rail_x2; self.vx=-RE_SPEED; self.facing=-1
        elif self.wx<=self.rail_x1:
            self.wx=self.rail_x1; self.vx=RE_SPEED;  self.facing=1
        if self.hit_flash>0: self.hit_flash-=dt*5
        self.anim_tick+=dt*7

    def draw(self,surf,cx,cy):
        if not self.active: return
        sx=int(self.wx-cx); sy=int(self.wy-cy)
        if sx>SW+80 or sx<-80: return
        # ── İSKELET MOD: basit stick figure ──
        flash = self.hit_flash > 0
        col = (220,60,60) if flash else (160,220,160)
        cx2=sx+RE_W//2
        hr=int(RE_W*0.52)
        # Baş
        pygame.draw.circle(surf,col,(cx2,sy-hr//2),hr,1)
        # Boyun → gövde
        pygame.draw.line(surf,col,(cx2,sy-hr//2+hr),(cx2,sy+int(RE_H*0.55)),2)
        # Omuzlar
        pygame.draw.line(surf,col,(cx2-RE_W//2,sy+int(RE_H*0.30)),(cx2+RE_W//2,sy+int(RE_H*0.30)),2)
        # Kollar
        pygame.draw.line(surf,col,(cx2-RE_W//2,sy+int(RE_H*0.30)),(cx2-RE_W//2+4,sy+int(RE_H*0.58)),2)
        pygame.draw.line(surf,col,(cx2+RE_W//2,sy+int(RE_H*0.30)),(cx2+RE_W//2-4,sy+int(RE_H*0.58)),2)
        # Bacaklar animasyonlu
        lk=int(math.sin(self.anim_tick)*6)
        pygame.draw.line(surf,col,(cx2,sy+int(RE_H*0.55)),(cx2-RE_W//3,sy+RE_H+lk),2)
        pygame.draw.line(surf,col,(cx2,sy+int(RE_H*0.55)),(cx2+RE_W//3,sy+RE_H-lk),2)
        # HP bar (sadece hasar aldıktan sonra)
        if self.hp<RE_HP_MAX:
            bw=RE_W+10; bx2=sx-5; by2=sy-hr-12
            pygame.draw.rect(surf,(30,8,8),(bx2,by2,bw,5))
            ratio=max(0,self.hp/RE_HP_MAX)
            pygame.draw.rect(surf,lc((200,30,30),(30,180,30),ratio),(bx2,by2,int(bw*ratio),5))
            pygame.draw.rect(surf,(80,60,40),(bx2,by2,bw,5),1)

# Ray düşmanı oda tanımları  (wx, wy, rail_x1, rail_x2)
#  wy = floor_y - RE_H  (zeminde ayakta dursunlar)
RAIL_ENEMY_DEFS = {
    "giris_holu":  [(300,484,120,700),(900,484,700,1500),(1500,484,1200,1850)],
    "drawing_room":[(350,444,100,700),(900,444,700,1450)],
    "dining_room": [(300,404,100,750),(900,404,700,1400)],
    "kutuphane":   [(400,464,100,800)],
    "ust_koridor": [(400,344,100,900),(1200,344,900,1800)],
}

_enemy_pool=[RailEnemy() for _ in range(20)]

def _spawn_room_enemies(room_id):
    for e in _enemy_pool: e.active=False
    pool_i=0
    for (wx,wy,rx1,rx2) in RAIL_ENEMY_DEFS.get(room_id,[]):
        while pool_i<len(_enemy_pool):
            if not _enemy_pool[pool_i].active:
                _enemy_pool[pool_i].spawn(wx,wy,rx1,rx2,room_id)
                pool_i+=1; break
            pool_i+=1

def _spawn_flame(wx,wy,sp=5):
    for p in _fp_pool:
        if not p.active:
            p.x=wx+rng.uniform(-sp,sp); p.y=wy
            p.vx=rng.uniform(-10,10); p.vy=rng.uniform(-55,-100)
            p.ml=rng.uniform(0.22,0.50); p.life=p.ml
            p.r=rng.randint(3,6); p.active=True; return

def _draw_flames(surf,dt,cx,cy,sources):
    pass  # iskelet mod — alev efektleri kaldırıldı

# ══════════════════════════════════════════════════════
#  ARKAPLAN ÇİZİM SİSTEMİ
#  Her oda kendi wall_style'ına göre render edilir
# ══════════════════════════════════════════════════════
def draw_room_bg(surf, room, cx, cy):
    # ── İSKELET MOD: düz koyu arka plan ──
    surf.fill((18, 16, 14))

def draw_stone_wall_bg(surf, room, cx, cy):
    surf.fill((18, 16, 14))
    _draw_lambri(surf, room, cx, cy)

def _draw_lambri(surf, room, cx, cy):
    pass  # iskelet mod — kaldırıldı

def _draw_cornice(surf, room, cx, cy):
    pass  # iskelet mod — kaldırıldı

# ══════════════════════════════════════════════════════
#  PLATFORM ÇİZİMLERİ
# ══════════════════════════════════════════════════════
def draw_floor(surf,rx,ry,rw,rh,cx,cy,style="wood"):
    sx,sy=rx-int(cx),ry-int(cy)
    if sy>SH or sy+rh<0: return
    pygame.draw.rect(surf,(50,50,55),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(100,100,110),(sx,sy,rw,rh),1)

def draw_stone_plat(surf,rx,ry,rw,rh,cx,cy,col_t=S4,col_b=S2):
    sx,sy=rx-int(cx),ry-int(cy)
    if sy>SH or sy+rh<0: return
    pygame.draw.rect(surf,(40,40,45),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(90,90,100),(sx,sy,rw,rh),1)

def draw_wall_col(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    pygame.draw.rect(surf,(35,35,40),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(80,80,90),(sx,sy,rw,rh),1)

# ══════════════════════════════════════════════════════
#  MERDİVEN
# ══════════════════════════════════════════════════════
def draw_staircase(surf,stair,cx,cy,near):
    rx,ry,rw,rh=stair["rect"]
    n=stair.get("steps",8); d=stair.get("dir","right")
    sw2=rw//n; sh2=rh//n
    for i in range(n):
        bx=rx+i*sw2 if d=="right" else rx+rw-(i+1)*sw2
        by=ry+rh-(i+1)*sh2
        sx,sy=bx-int(cx),by-int(cy)
        if sy>SH or sx>SW: continue
        pygame.draw.rect(surf,(40,40,45),(sx,sy,sw2,sh2))
        pygame.draw.rect(surf,(90,90,100),(sx,sy,sw2,sh2),1)
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
        draw_wall_col(surf,rx,ry,rw,rh,cx,cy)
        return
    pygame.draw.rect(surf,(30,30,35),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(120,120,140),(sx,sy,rw,rh),2)
    # Kapı kolu basit nokta
    pygame.draw.circle(surf,(160,160,80),(sx+rw-10,sy+int(rh*0.62)),4)
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
def _skeleton_box(surf,sx,sy,rw,rh,label=""):
    pygame.draw.rect(surf,(30,30,35),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(80,80,100),(sx,sy,rw,rh),1)
    if label:
        lbl=F_SM.render(label,True,(70,70,90))
        surf.blit(lbl,(sx+2,sy+2))

def draw_fireplace(surf,rx,ry,rw,rh,cx,cy, marble=False):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"fireplace")

def draw_window(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"window")
    pygame.draw.line(surf,(60,60,80),(sx+rw//2,sy),(sx+rw//2,sy+rh),1)
    pygame.draw.line(surf,(60,60,80),(sx,sy+rh//2),(sx+rw,sy+rh//2),1)

def draw_bookshelf(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"bookshelf")

def draw_portrait(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"portrait")

def draw_candelabra(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"candelabra")

def draw_carpet(surf,rx,ry,rw,rh,cx,cy,color=None):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    pygame.draw.rect(surf,(40,25,25),(sx,sy,rw,rh))
    pygame.draw.rect(surf,(80,50,50),(sx,sy,rw,rh),1)

def draw_sconce(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"sconce")

def draw_chandelier(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"chandelier")

def draw_clock(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"clock")

def draw_armor(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"armor")

def draw_piano(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"piano")

def draw_dining_table(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"dining_table")

def draw_iron_range(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"iron_range")

def draw_canopy_bed(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"canopy_bed")

def draw_globe(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    cx2=sx+rw//2; cy2=sy+rh//2
    pygame.draw.circle(surf,(30,30,35),(cx2,cy2),rw//2,1)

def draw_pantry_shelves(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"pantry")

def draw_washtub(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"washtub")

def draw_bell_pull(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    pygame.draw.line(surf,(80,80,100),(sx+rw//2,sy),(sx+rw//2,sy+rh),1)

def draw_coal_pile(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    if sx>SW or sx+rw<0: return
    _skeleton_box(surf,sx,sy,rw,rh,"coal")

def draw_secret_door_hint(surf,rx,ry,rw,rh,cx,cy):
    sx,sy=rx-int(cx),ry-int(cy)
    draw_wall_col(surf,rx,ry,rw,rh,cx,cy)
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
# ══════════════════════════════════════════════════════
#  İSKELET ÇİZİM YARDIMCILARI
# ══════════════════════════════════════════════════════
def _bone(surf, p1, p2, r1, r2, col, shadow=True):
    """İki nokta arası konik kemik — başta r1, sonda r2 yarıçap.
       p1/p2 ekran koordinatı (int tuple)."""
    dx = p2[0]-p1[0]; dy = p2[1]-p1[1]
    d  = math.hypot(dx, dy)
    if d < 1: return
    nx = -dy/d; ny = dx/d          # normal

    # Konik dörtgen (trapez) — gölge
    if shadow:
        pts_sh = [
            (int(p1[0]+nx*(r1+1.5)), int(p1[1]+ny*(r1+1.5))),
            (int(p2[0]+nx*(r2+1.5)), int(p2[1]+ny*(r2+1.5))),
            (int(p2[0]-nx*(r2+1.5)), int(p2[1]-ny*(r2+1.5))),
            (int(p1[0]-nx*(r1+1.5)), int(p1[1]-ny*(r1+1.5))),
        ]
        pygame.draw.polygon(surf, (0,0,0), pts_sh)
    # Ana kemik dolgusu
    pts = [
        (int(p1[0]+nx*r1), int(p1[1]+ny*r1)),
        (int(p2[0]+nx*r2), int(p2[1]+ny*r2)),
        (int(p2[0]-nx*r2), int(p2[1]-ny*r2)),
        (int(p1[0]-nx*r1), int(p1[1]-ny*r1)),
    ]
    pygame.draw.polygon(surf, col, pts)
    # Parlak kenar (üst yarı daha aydınlık)
    hi = lc(col,(255,255,255),0.45)
    pygame.draw.line(surf, hi,
        (int(p1[0]+nx*r1*0.6), int(p1[1]+ny*r1*0.6)),
        (int(p2[0]+nx*r2*0.6), int(p2[1]+ny*r2*0.6)), 1)

def _jnt(surf, pos, r, col, glow=True):
    """Eklem dairesi + isteğe bağlı yumuşak glow."""
    if glow:
        gr = r + 5
        alpha_rect(surf, col, 38,
            pygame.Rect(pos[0]-gr, pos[1]-gr, gr*2, gr*2))
    pygame.draw.circle(surf, (0,0,0), pos, r+1)   # gölge
    pygame.draw.circle(surf, col,     pos, r)
    pygame.draw.circle(surf, lc(col,(255,255,255),0.55), pos, max(1,r-2))

def _eye_glow(surf, pos, r, col):
    """Göz soketi — iç parlama."""
    for rad, a in ((r+6,30),(r+3,70),(r,140)):
        alpha_rect(surf, col, a,
            pygame.Rect(pos[0]-rad, pos[1]-rad, rad*2, rad*2))
    pygame.draw.circle(surf, col, pos, r)

class Player:
    __slots__=("wx","wy","vx","vy","on_ground","facing",
               "anim_tick","squash","stretch","interact_ev","arm",
               "lean","recoil_tilt")
    def __init__(self,wx,wy):
        self.wx=float(wx); self.wy=float(wy)
        self.vx=self.vy=0.0; self.on_ground=False; self.facing=1
        self.anim_tick=0.0; self.squash=1.0; self.stretch=1.0
        self.interact_ev=False
        self.arm=PhysicsArm(ul=10,ll=9)
        self.arm.reset(self.wx+PW/2, self.wy+PH*0.30)
        self.lean=0.0          # gövde eğimi (ateşte geriye)
        self.recoil_tilt=0.0   # omuz/baş geri itmesi

    def update(self,dt,platforms,keys,ie):
        self.interact_ev=ie; self.vx=0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.vx=-P_SPEED; self.facing=-1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx= P_SPEED; self.facing= 1
        was_ground=self.on_ground
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy=JUMP_V; self.on_ground=False; self.stretch=1.28
            self.arm.impulse(0,-130)            # zıplama → kol yukarı fırlar
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
                if self.vy>180:
                    self.squash=0.75
                    self.arm.impulse(0, self.vy*0.06)  # sert iniş → kol aşağı çarpar
                self.vy=0; self.on_ground=True
            elif p["type"]=="ceil":
                self.wy=pr.bottom; self.vy=0
            ry.y=int(self.wy)
        # Koşarken anim_tick güncelle — kola impulse verme
        if self.on_ground and abs(self.vx)>1:
            self.anim_tick+=dt*7
        else:
            self.anim_tick=0.0
        self.squash+=(1-self.squash)*min(1,dt*16)
        self.stretch+=(1-self.stretch)*min(1,dt*16)
        self.lean+=(0-self.lean)*min(1,dt*9)
        self.recoil_tilt+=(0-self.recoil_tilt)*min(1,dt*11)
        # Kol fizik güncellemesi
        shx=self.wx+PW/2; shy=self.wy+PH*0.30
        self.arm.update(dt,shx,shy)

    def get_rect(self): return pygame.Rect(int(self.wx),int(self.wy),PW,PH)

    def draw(self,surf,cx,cy):
        sx=int(self.wx-cx); sy=int(self.wy-cy)
        f=self.facing

        # ── Animasyon ──────────────────────────────────────────
        walk    = abs(self.vx) > 10
        t       = self.anim_tick
        breath  = math.sin(_ft*1.9) * (0.6 if not walk else 0.1)
        lean_px = int(self.lean * 12)
        tilt_py = int(self.recoil_tilt * 8)
        run_lx  = int(self.vx * 0.04) if walk else 0
        sq      = self.squash; st = self.stretch

        # ── PALET ──────────────────────────────────────────────
        C_BONE   = (195, 225, 255)   # kemik ana renk
        C_SPINE  = (225, 245, 255)   # omurga (en beyaz)
        C_DIM    = ( 70,  95, 135)   # arka uzuvlar
        C_GLOW   = ( 80, 160, 255)   # eklem glow rengi
        C_EYE    = ( 50, 220, 255)   # göz enerji rengi

        # ── KÖK NOKTALAR ───────────────────────────────────────
        hip_cx = sx + PW//2
        hip_cy = sy + int(PH * 0.64 * sq)
        if walk:
            hip_cy += int(math.sin(t*2) * 2.5 * st)
            hip_cx += int(math.sin(t)   * 1.8)
        hw     = int(PW * 0.33)
        l_hip  = (hip_cx - hw, hip_cy)
        r_hip  = (hip_cx + hw, hip_cy)

        # Omurga noktaları
        s0x = hip_cx + lean_px//4  + run_lx//4
        s0y = hip_cy - int(PH*0.16*st)
        s1x = hip_cx + lean_px*2//3 + run_lx//2
        s1y = hip_cy - int(PH*0.32*st)
        s2x = hip_cx + lean_px + run_lx - tilt_py//4
        s2y = hip_cy - int(PH*0.50*st) - tilt_py//2 - int(breath*2.5)

        # Omuzlar
        sh_w   = int(PW * 0.68)
        rot_r  = int(math.cos(t)*2.5) if walk else 0
        l_sh   = (s2x - sh_w//2,  s2y + rot_r)
        r_sh   = (s2x + sh_w//2,  s2y - rot_r)
        # Çalışan kol tarafi (ateş eden) ve serbest kol
        arm_sh = r_sh if f==1 else l_sh   # nişan kolu omuzu
        free_sh= l_sh if f==1 else r_sh

        # Kafa
        neck_x = s2x;  neck_y = s2y - 6
        head_r = int(PW*0.30)
        head_x = neck_x + f*2 - tilt_py//3
        head_y = neck_y - head_r - 3

        # ── BACAK IK ───────────────────────────────────────────
        thl = int(PH*0.26*st); shl = int(PH*0.26*st)
        ftl = int(PW*0.24)
        gnd = sy + int(PH*sq)

        def leg_ik(hx, hy, phase):
            if walk:
                fx = hx + int(math.sin(phase)*PW*0.42)*f
                fy = gnd - max(0, int(-math.sin(phase)*12))
            else:
                fx = hx + int(math.sin(_ft*1.9+hx)*1.0)
                fy = gnd
            d  = clamp(math.hypot(fx-hx,fy-hy), abs(thl-shl)+.5, thl+shl-.5)
            ca = clamp((d*d+thl*thl-shl*shl)/(2*d*thl),-1,1)
            ba = math.atan2(fy-hy, fx-hx)
            ka = ba - math.acos(ca)*f
            kx = int(hx+math.cos(ka)*thl); ky=int(hy+math.sin(ka)*thl)
            return (kx,ky),(int(fx),int(fy))

        (l_kn,l_ank) = leg_ik(l_hip[0],l_hip[1], t+math.pi)
        (r_kn,r_ank) = leg_ik(r_hip[0],r_hip[1], t)

        if f==1:
            bk_hip,bk_kn,bk_ank = l_hip,l_kn,l_ank
            fr_hip,fr_kn,fr_ank = r_hip,r_kn,r_ank
        else:
            bk_hip,bk_kn,bk_ank = r_hip,r_kn,r_ank
            fr_hip,fr_kn,fr_ank = l_hip,l_kn,l_ank

        # ══════════════════════════════════════════════════════
        # Z-SIRALAMA: arka → ön
        # ══════════════════════════════════════════════════════

        # 1) SERBEST KOL (Physics) — en arkada
        shx_f = self.wx + PW/2
        shy_f = self.wy + PH*0.30
        self.arm.draw(surf, shx_f, shy_f, cx, cy, C_DIM, C_DIM)

        # 2) ARKA BACAK — soluk
        bk_toe  = (bk_ank[0]+f*ftl,   bk_ank[1]+2)
        bk_heel = (bk_ank[0]-f*ftl//3, bk_ank[1]+2)
        _bone(surf, bk_hip, bk_kn,  3,2, C_DIM, shadow=False)
        _bone(surf, bk_kn,  bk_ank, 2,2, C_DIM, shadow=False)
        _bone(surf, bk_ank, bk_toe, 2,1, C_DIM, shadow=False)
        pygame.draw.circle(surf, C_DIM, bk_kn,  3)
        pygame.draw.circle(surf, C_DIM, bk_ank, 2)

        # 3) PELV kemeri + kalça eklemleri
        _bone(surf, l_hip, r_hip, 3,3, C_BONE)
        _jnt(surf, l_hip, 4, C_GLOW)
        _jnt(surf, r_hip, 4, C_GLOW)

        # 4) OMURGA (3 segment — incelip kalınlaşır)
        _bone(surf, (hip_cx,hip_cy),(s0x,s0y), 3,3, C_SPINE)
        _bone(surf, (s0x,s0y),      (s1x,s1y), 3,3, C_SPINE)
        _bone(surf, (s1x,s1y),      (s2x,s2y), 3,2, C_SPINE)
        # Omur diskleri
        for pt in ((s0x,s0y),(s1x,s1y)):
            _jnt(surf, pt, 3, C_GLOW, glow=False)
        # Kaburgalar (4 çift — eğri yay gibi)
        for i,rib_t in enumerate((0.18,0.42,0.66,0.88)):
            rx_ = int(s1x+(s2x-s1x)*rib_t)
            ry_ = int(s1y+(s2y-s1y)*rib_t)
            rw  = int(sh_w*(0.38-i*0.04))
            # Sol kaburga
            cp_l = (rx_-rw//3, ry_+4+i)
            pygame.draw.line(surf, C_DIM, (rx_,ry_), cp_l, 1)
            pygame.draw.line(surf, C_DIM, cp_l, (rx_-rw,ry_+2+i), 1)
            # Sağ kaburga
            cp_r = (rx_+rw//3, ry_+4+i)
            pygame.draw.line(surf, C_DIM, (rx_,ry_), cp_r, 1)
            pygame.draw.line(surf, C_DIM, cp_r, (rx_+rw,ry_+2+i), 1)

        # 5) KLAVİKULA
        _bone(surf, l_sh, r_sh, 3,3, C_BONE)
        _jnt(surf, l_sh, 4, C_GLOW)
        _jnt(surf, r_sh, 4, C_GLOW)
        _jnt(surf, (s2x,s2y), 4, C_GLOW)   # sternum

        # 6) BOYUN
        _bone(surf, (s2x,s2y),(neck_x,neck_y), 3,2, C_BONE)

        # 7) KAFATASI ──────────────────────────────────────────
        # Kraniyum dolgusu (koyu iç)
        pygame.draw.circle(surf, (0,0,0),   (head_x,head_y), head_r+2)
        pygame.draw.circle(surf, (15,18,28),(head_x,head_y), head_r)
        # Kafatası contour (2 kat: gölge + parlak)
        pygame.draw.circle(surf, (0,0,0),   (head_x,head_y), head_r,   3)
        pygame.draw.circle(surf, C_BONE,    (head_x,head_y), head_r,   2)
        # Alın yayı (daha kalın/parlak)
        pygame.draw.arc(surf, C_SPINE,
            pygame.Rect(head_x-head_r,head_y-head_r,head_r*2,head_r*2),
            math.pi*0.05, math.pi*0.95, 3)
        # Şakak çizgisi
        pygame.draw.arc(surf, C_DIM,
            pygame.Rect(head_x-head_r+2,head_y-head_r+2,head_r*2-4,head_r*2-4),
            math.pi*1.05, math.pi*1.60, 1)
        # Elmacık kemiği (zigoma)
        zx = head_x + f*int(head_r*0.18); zy = head_y+int(head_r*0.20)
        pygame.draw.line(surf, C_BONE,
            (zx, zy),(zx+f*int(head_r*0.52),zy+1), 2)
        # Çene (mandibula) — iki segment kırık V
        jaw_a = (head_x-f*int(head_r*0.54), head_y+int(head_r*0.38))
        jaw_b = (head_x,                     head_y+head_r-2)
        jaw_c = (head_x+f*int(head_r*0.60),  head_y+int(head_r*0.28))
        pygame.draw.line(surf, C_BONE, jaw_a, jaw_b, 2)
        pygame.draw.line(surf, C_BONE, jaw_b, jaw_c, 2)
        # Burun kemiği — üçgen
        n1=(head_x+f*int(head_r*0.10),head_y+int(head_r*0.02))
        n2=(head_x+f*int(head_r*0.38),head_y+int(head_r*0.34))
        n3=(head_x+f*int(head_r*0.22),head_y+int(head_r*0.34))
        pygame.draw.line(surf,C_DIM,n1,n2,1)
        pygame.draw.line(surf,C_DIM,n2,n3,1)
        # Göz soketi (orbita)
        ox = head_x + f*int(head_r*0.38); oy = head_y - int(head_r*0.08)
        ow = int(head_r*0.42);             oh = int(head_r*0.36)
        pygame.draw.ellipse(surf,(0,0,0),(ox-ow//2-1,oy-oh//2-1,ow+2,oh+2))
        pygame.draw.ellipse(surf,C_DIM,  (ox-ow//2,  oy-oh//2,  ow,  oh),  1)
        # Göz enerji glow
        _eye_glow(surf,(ox,oy), int(head_r*0.11), C_EYE)

        # 8) ÖN BACAK — tam parlak, volumetrik
        fr_toe  = (fr_ank[0]+f*ftl,    fr_ank[1]+2)
        fr_heel = (fr_ank[0]-f*ftl//3, fr_ank[1]+2)
        _bone(surf, fr_hip, fr_kn,  4,3, C_BONE)
        _bone(surf, fr_kn,  fr_ank, 3,2, C_BONE)
        _bone(surf, fr_ank, fr_toe, 3,1, C_BONE)
        _bone(surf, fr_ank, fr_heel,2,1, C_BONE)
        _jnt(surf, fr_hip, 4, C_GLOW)
        _jnt(surf, fr_kn,  5, C_GLOW)   # diz — büyük
        _jnt(surf, fr_ank, 4, C_GLOW)
        pygame.draw.circle(surf, C_SPINE, fr_toe, 2)  # parmak ucu

# ══════════════════════════════════════════════════════
#  FİZİK KOLU  (PhysicsArm)  — 2 segment zincir, verlet yay
# ══════════════════════════════════════════════════════
class PhysicsArm:
    """
    Serbest kol — tamamen statik IK rest-pose.
    Sadece recoil anında küçük titreme, yoksa hiç sallanmaz.
    """
    __slots__=("ox","oy","ul","ll")   # offset x/y (recoil titremesi)

    def __init__(self,ul=13,ll=12):
        self.ul=float(ul); self.ll=float(ll)
        self.ox=0.0; self.oy=0.0

    def reset(self,shx,shy): self.ox=0.0; self.oy=0.0

    def impulse(self,ix,iy):
        """Ateş tepkisi: küçük ofset ver, update'te sıfırlanır."""
        self.ox+=ix*0.12; self.oy+=iy*0.12

    def update(self,dt,shx,shy):
        # Ofseti hızla sıfırla
        self.ox+=(0-self.ox)*min(1, dt*18)
        self.oy+=(0-self.oy)*min(1, dt*18)

    def draw(self,surf,shx,shy,cx,cy,col_up,col_lo):
        # Rest-pose IK: kol aşağı sarkık, hafif öne
        # Dirsek = omuzdan ul kadar aşağı + recoil ofseti
        ex = shx + self.ox
        ey = shy + self.ul + self.oy
        # Bilek = dirsekten ll kadar aşağı
        wx = ex
        wy = ey + self.ll
        ssx=int(shx-cx); ssy=int(shy-cy)
        sex=int(ex-cx);  sey=int(ey-cy)
        swx=int(wx-cx);  swy=int(wy-cy)
        _bone(surf,(ssx,ssy),(sex,sey),3,2,col_up,shadow=False)
        _bone(surf,(sex,sey),(swx,swy),2,2,col_up,shadow=False)
        pygame.draw.circle(surf,col_lo,(ssx,ssy),3)
        pygame.draw.circle(surf,col_lo,(sex,sey),3)
        pygame.draw.circle(surf,col_lo,(swx,swy),2)

# ══════════════════════════════════════════════════════
#  KAMERA  — dinamik: shake + aim lead + velocity lookahead
# ══════════════════════════════════════════════════════
class Camera:
    __slots__=("x","y","_si","_st","_sm")
    def __init__(self):
        self.x=self.y=0.0
        self._si=0.0   # shake intensity
        self._st=0.0   # shake timer kalan
        self._sm=0.0   # shake timer max

    def shake(self,intensity,dur=0.18):
        """Titreşim tetikle. Daha güçlü istek öncekini override eder."""
        if intensity>self._si:
            self._si=intensity; self._st=dur; self._sm=max(dur,0.001)

    def update(self,pwx,pwy,rw,rh,dt,aim_angle=0.0,pvx=0.0,
               enemies=None,cur_id=""):
        # ── 1. En yakın aktif düşmanı bul, ağırlıklı odak noktası hesapla
        focus_x=pwx+PW/2
        focus_y=pwy+PH/2
        PULL_START=600   # bu mesafeden itibaren çekmeye başlar
        PULL_FULL =120   # bu mesafede tam ortalama
        enemy_near=False
        if enemies:
            best_d=PULL_START; best_ex=None; best_ey=None
            for e in enemies:
                if not e.active or e.room_id!=cur_id: continue
                d=math.hypot((e.wx+RE_W/2)-(pwx+PW/2),
                             (e.wy+RE_H/2)-(pwy+PH/2))
                if d<best_d:
                    best_d=d; best_ex=e.wx+RE_W/2; best_ey=e.wy+RE_H/2
            if best_ex is not None:
                t=clamp((PULL_START-best_d)/(PULL_START-PULL_FULL),0.0,1.0)
                w=t*0.50   # max %50 — oyuncu hep görünür kalır
                focus_x=focus_x*(1-w)+best_ex*w
                focus_y=focus_y*(1-w)+best_ey*w
                enemy_near=(t>0.05)

        # ── 2. Aim lead + velocity lookahead
        al_x=clamp(math.cos(aim_angle)*60,-60,60)
        al_y=clamp(math.sin(aim_angle)*22,-22,22)
        vl_x=clamp(pvx*0.12,-28,28)

        tx=clamp(focus_x-SW//2+al_x+vl_x, 0, max(0,rw-SW))
        ty=clamp(focus_y-SH//2+al_y,       0, max(0,rh-SH))

        # Düşman yakınken kamera daha hızlı tepki verir
        lerp_x = (0.18 if enemy_near else CAM_LX) * dt * 60
        lerp_y = (0.18 if enemy_near else CAM_LY) * dt * 60
        self.x+=(tx-self.x)*min(1, lerp_x)
        self.y+=(ty-self.y)*min(1, lerp_y)

        # ── 3. Smooth Falloff Shake
        if self._st>0:
            self._st-=dt
            if self._st<=0:
                self._si=0.0
            else:
                prog=1.0-self._st/self._sm
                mag=self._si*(1.0-prog)
                self.x+=math.sin(_ft*52.0)*mag
                self.y+=math.cos(_ft*61.0)*mag*0.65

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

def render_ui(surf,room_id,fps,debug,player,cam,gun):
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
        ctrl=F_SM.render("A/D: Yürü  |  W/Space: Zıpla  |  E: Etkileşim  |  J: Ateş  |  R: Doldur  |  F12: Debug",True,(120,108,80))
        _ui_s.blit(s1,(20,8)); _ui_s.blit(s2,(20,32))
        _ui_s.blit(ctrl,(SW-ctrl.get_width()-18,20))
    surf.blit(_ui_s,(0,SH-56))
    # Silah HUD (sol alt)
    ammo_surf=F_MD.render(f"🔫  {gun.ammo}/{DE_MAG}" if not gun.reloading
                          else f"⟳  Yükleniyor…",True,
                          (220,200,80) if not gun.reloading else (180,150,60))
    surf.blit(ammo_surf,(20,SH-90))
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
    gun=DesertEagle()
    _spawn_room_enemies(cur_id)
    fire_ev=False; reload_ev=False
    camera.x=clamp(player.wx+PW//2-SW//2,0,max(0,rdef["w"]-SW))
    camera.y=clamp(player.wy+PH//2-SH//2,0,max(0,rdef["h"]-SH))

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
        ie=False; fire_ev=False; reload_ev=False
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: running=False
                if ev.key==pygame.K_F12: debug=not debug
                if ev.key==pygame.K_e: ie=True
                if ev.key==pygame.K_r: reload_ev=True
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                fire_ev=True

        # Aim açısı: omuz (world) → fare (world)
        mx,my=pygame.mouse.get_pos()
        sh_wx=player.wx+PW/2; sh_wy=player.wy+PH*0.32
        aim_angle=math.atan2((my+camera.y)-sh_wy,(mx+camera.x)-sh_wx)
        # Oyuncu yönü fareye göre
        if mx+camera.x > sh_wx: player.facing=1
        else: player.facing=-1

        keys=pygame.key.get_pressed()
        floor_y=rdef.get("floor_world_y",580)
        if not fade.active:
            player.update(dt,rdef["platforms"],keys,ie)
            fired=gun.update(dt,fire_ev,reload_ev,player,aim_angle)
            if fired:
                camera.shake(5.5, 0.14)
                player.arm.impulse(                     # ateş tepkisi off-arm'a
                    -math.cos(aim_angle)*55,
                    -math.sin(aim_angle)*40)
            _update_bullets(dt,rdef["platforms"],_enemy_pool,cur_id,floor_y)
            for e in _enemy_pool:
                if e.active and e.room_id==cur_id: e.update(dt)
            _update_ragdolls(dt)
            camera.update(player.wx,player.wy,rdef["w"],rdef["h"],dt,
                          aim_angle,player.vx,_enemy_pool,cur_id)
            res=check_interact(player,rdef)
            if res:
                pending=res; fade.start()
                print(f"  [→] {pending[0]}")

        if fade.update(dt) and pending:
            cur_id=pending[0]; rdef=ROOM_DEFS[cur_id]
            player.wx=float(pending[1][0]); player.wy=float(pending[1][1])
            player.vx=player.vy=0.0; player.on_ground=False
            player.arm.reset(player.wx+PW/2, player.wy+PH*0.30)
            camera.x=clamp(player.wx+PW//2-SW//2,0,max(0,rdef["w"]-SW))
            camera.y=clamp(player.wy+PH//2-SH//2,0,max(0,rdef["h"]-SH))
            _spawn_room_enemies(cur_id)
            for b in _bullet_pool: b.active=False
            pending=None

        nd,ns=get_near(player,rdef); cx,cy=camera.x,camera.y

        # ── ZOOM: nişan alınan düşman var mı?
        global _zoom
        AIM_DIST   = 1100
        AIM_CONE   = 0.38
        zoom_target  = 1.0
        # Varsayılan: oyuncu merkezi
        _zoom_focus_x = player.wx + PW/2
        _zoom_focus_y = player.wy + PH/2
        for e in _enemy_pool:
            if not e.active or e.room_id!=cur_id: continue
            ex2=e.wx+RE_W/2; ey2=e.wy+RE_H/2
            dx2=ex2-(player.wx+PW/2); dy2=ey2-(player.wy+PH/2)
            d=math.hypot(dx2,dy2)
            if d<8: continue
            ang_to=math.atan2(dy2,dx2)
            diff=abs(math.atan2(math.sin(aim_angle-ang_to),
                                math.cos(aim_angle-ang_to)))
            if diff<AIM_CONE and d<AIM_DIST:
                # Tam orta nokta
                _zoom_focus_x = (player.wx+PW/2 + ex2) / 2
                _zoom_focus_y = (player.wy+PH/2 + ey2) / 2
                # İkisini de sığdıracak zoom: mesafeye göre otomatik hesapla
                # Yatay mesafe + kenar payı SW'ye sığmalı
                needed_w = abs(dx2) * 1.5 + 120   # kenar boşluğu
                needed_h = abs(dy2) * 1.5 + 120
                z_by_w = SW / max(needed_w, 1)
                z_by_h = SH / max(needed_h, 1)
                zoom_target = clamp(min(z_by_w, z_by_h), 0.55, 1.18)
                break
        _zoom+=( zoom_target-_zoom)*min(1, 5.0*dt)

        # ── RENDER — dünya game_surf'e çizilir ────────────────
        # Z-0/1: Arkaplan
        draw_room_bg(surf=game_surf,room=rdef,cx=cx,cy=cy)

        # Z-2: Arka dekorlar
        for d in rdef["decor"]:
            if d["type"] in BACK_D: draw_decor(game_surf,d,cx,cy)

        # Z-3: Platformlar
        fstyle=rdef.get("floor_style","wood")
        for p in rdef["platforms"]:
            rx,ry,rw,rh=p["rect"]; pt=p["type"]
            if   pt=="floor": draw_floor(game_surf,rx,ry,rw,rh,cx,cy,fstyle)
            elif pt in ("stone","ceil"): draw_stone_plat(game_surf,rx,ry,rw,rh,cx,cy)
            elif pt=="wall":  draw_wall_col(game_surf,rx,ry,rw,rh,cx,cy)

        # Z-3b: Merdivenler
        for s in rdef.get("stairs",[]):
            if "target_room" in s:
                draw_staircase(game_surf,s,cx,cy,s in ns)

        # Z-4: Kapılar
        for d in rdef.get("doors",[]): draw_door(game_surf,d,cx,cy,d in nd)

        # Z-4b: Ön dekorlar
        for d in rdef["decor"]:
            if d["type"] in FORE_D: draw_decor(game_surf,d,cx,cy)

        # Z-5: Oyuncu
        player.draw(game_surf,cx,cy)
        gun.draw(game_surf,player,cx,cy,aim_angle)

        # Z-5a: Ray düşmanları
        for e in _enemy_pool:
            if e.active and e.room_id==cur_id: e.draw(game_surf,cx,cy)

        # Z-5b: Ragdoll parçaları
        _draw_ragdolls(game_surf,cx,cy)

        # Z-5c: Mermiler
        _draw_bullets(game_surf,cx,cy)

        # Z-6: Ateş partikülleri
        _draw_flames(game_surf,dt,cx,cy,rdef.get("fire_sources",[]))

        fade.draw(game_surf)

        # ── ZOOM BLIT: game_surf → screen ─────────────────────
        if abs(_zoom-1.0) < 0.005:
            screen.blit(game_surf,(0,0))
        else:
            fcx = int(_zoom_focus_x - cx)
            fcy = int(_zoom_focus_y - cy)
            vw = int(SW / _zoom)
            vh = int(SH / _zoom)
            # vw/vh game_surf sınırını aşamasın
            vw = min(vw, SW)
            vh = min(vh, SH)
            src_x = clamp(fcx - vw//2, 0, SW - vw)
            src_y = clamp(fcy - vh//2, 0, SH - vh)
            sub = game_surf.subsurface((src_x, src_y, vw, vh))
            pygame.transform.scale(sub, (SW, SH), screen)

        # ── UI ve crosshair doğrudan screen'e (zoom etkilemez) ─
        render_ui(screen,cur_id,clock.get_fps(),debug,player,camera,gun)
        mx2,my2=pygame.mouse.get_pos()
        rc=14; cc=(220,200,80)
        # Nişan alındığında crosshair kırmızıya döner
        if zoom_target>1.0: cc=(255,60,60)
        pygame.draw.circle(screen,cc,(mx2,my2),rc,2)
        pygame.draw.line(screen,cc,(mx2-rc-5,my2),(mx2-rc+3,my2),2)
        pygame.draw.line(screen,cc,(mx2+rc-3,my2),(mx2+rc+5,my2),2)
        pygame.draw.line(screen,cc,(mx2,my2-rc-5),(mx2,my2-rc+3),2)
        pygame.draw.line(screen,cc,(mx2,my2+rc-3),(mx2,my2+rc+5),2)
        pygame.draw.circle(screen,cc,(mx2,my2),2)
        pygame.display.flip()

    gc.enable(); gc.collect(); pygame.quit(); sys.exit()

if __name__=="__main__":
    main()
