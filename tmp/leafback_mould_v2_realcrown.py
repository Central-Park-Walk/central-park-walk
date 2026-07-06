#!/usr/bin/env python3
"""Step 2: rebuild the SAME one mould against a REAL crown outline (iNat-derived),
side-by-side with the v1 placeholder dome. Same representative specimen
(H 14.4 m, DBH 15 in), same sprig fill + leaf-back merge — only the crown
envelope changes, so the comparison isolates the crown-shape effect.

Real crown profile: table sampled by eye from the clean full-crown iNat specimen
obs75867287 (early-spring, outline readable), broadened toward the measured
CP crown-form distribution (aspect ~1.0; low-spreading lower-mid fullness seen
in obs122865830 grove-edge + obs11670158 veteran). Data notes in the report.
"""
import numpy as np, math, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

H, DBH_M = 14.4, 15*0.0254
SPRIG_SPACE, SHELL_THICK = 0.65, 1.3

def crown_dome(t, RX=5.3):
    a=(t-0.55); prof=np.sqrt(np.clip(1-(a/max(0.55,0.45))**2,0,1)); prof*=np.clip(t*3,0,1)**0.5
    return RX*prof
DOME=dict(base=0.37*H, rx=5.3, fn=crown_dome, name="v1 placeholder dome")

# v2 REAL crown: table-interpolated profile from iNat obs75867287, broadened to
# the CP distribution. t=frac up crown (0=fork,1=apex); p=half-width/RX (peak 1.0)
_T = np.array([0.00, 0.12, 0.25, 0.40, 0.50, 0.62, 0.75, 0.88, 1.00])
_P = np.array([0.14, 0.55, 0.82, 0.98, 1.00, 0.95, 0.80, 0.55, 0.18])
def crown_real(t, RX=5.04):
    return RX*np.interp(np.clip(t,0,1), _T, _P)
REAL=dict(base=0.30*H, rx=5.04, fn=crown_real, name="v2 iNat-derived crown")

def build(cfg, seed=20260706):
    rng=np.random.default_rng(seed)
    CB, RX, cr = cfg['base'], cfg['rx'], cfg['fn']; CH=H-CB
    def sample(n=60000):
        ts=rng.uniform(0,1,n); y=CB+ts*CH; R=cr(ts,RX)
        keep=R>0.15; ts,y,R=ts[keep],y[keep],R[keep]
        th=rng.uniform(0,2*math.pi,len(ts)); depth=rng.uniform(0,1,len(ts))**1.6*SHELL_THICK
        rr=np.clip(R-depth,0.05,None); return np.stack([rr*np.cos(th),y,rr*np.sin(th)],1)
    P=sample(); cell=SPRIG_SPACE; grid={}; keep=[]
    for p in P:
        c=(int(p[0]//cell),int(p[1]//cell),int(p[2]//cell)); ok=True
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                for dz in(-1,0,1):
                    for q in grid.get((c[0]+dx,c[1]+dy,c[2]+dz),()):
                        if np.sum((p-q)**2)<cell*cell: ok=False;break
                    if not ok:break
                if not ok:break
            if not ok:break
        if ok: grid.setdefault(c,[]).append(p); keep.append(p)
    sprigs=np.array(keep)
    FORK=np.array([0.0,CB,0.0]); edges=[]; hop=np.zeros(len(sprigs),int)
    nodes=[{"pos":sprigs[i].copy(),"origins":{i}} for i in range(len(sprigs))]
    cell0=SPRIG_SPACE*2.0; g=1.55; L=0; log=[]
    while len(nodes)>4 and L<12:
        cs=cell0*(g**L); bins={}
        for nd in nodes:
            k=(int(nd["pos"][0]//cs),int(nd["pos"][1]//cs),int(nd["pos"][2]//cs)); bins.setdefault(k,[]).append(nd)
        nn=[]
        for grp in bins.values():
            if len(grp)==1: nn.append(grp[0]); continue
            cen=np.mean([q["pos"] for q in grp],0); pa=min(.20+.06*L,.6); pd=min(.12+.05*L,.5)
            par=cen.copy(); par[0]*=(1-pa); par[2]*=(1-pa); par[1]=max(cen[1]-pd*(cen[1]-CB),CB+0.3)
            org=set()
            for q in grp: edges.append((q["pos"].copy(),par.copy(),L)); org|=q["origins"]
            for oi in org: hop[oi]+=1
            nn.append({"pos":par,"origins":org})
        nodes=nn; log.append((L,cs,len(nodes))); L+=1
    for nd in nodes:
        edges.append((nd["pos"].copy(),FORK.copy(),L))
        for oi in nd["origins"]: hop[oi]+=1
    edges.append((FORK.copy(),np.array([0.,0.,0.]),L+1))
    return dict(sprigs=sprigs,edges=edges,hop=hop,prim=len(nodes),base=CB,log=log,name=cfg['name'])

R1=build(DOME); R2=build(REAL)
for R in (R1,R2):
    print(f"\n{R['name']}: {len(R['sprigs'])} sprigs, {R['prim']} primaries, base {R['base']:.2f}m")
    for L,cs,n in R['log']: print(f"   L{L} cell {cs:.2f} -> {n}")
    print(f"   hops: min {R['hop'].min()} med {int(np.median(R['hop']))} max {R['hop'].max()} mean {R['hop'].mean():.2f}")

fig=plt.figure(figsize=(14,8))
for si,R in enumerate((R1,R2)):
    ax=fig.add_subplot(1,2,si+1,projection='3d'); ed=R['edges']; lm=max(e[2] for e in ed); cm=plt.cm.YlGn
    for a,b,lv in ed:
        ax.plot([a[0],b[0]],[a[1],b[1]],[a[2],b[2]],color=cm(0.25+0.7*(lv/lm)),lw=0.4+2.6*(1-lv/lm))
    s=R['sprigs']; ax.scatter(s[:,0],s[:,1],s[:,2],s=3,c='#2e7d32',alpha=0.5)
    ax.set_title(f"{R['name']}\n{len(s)} sprigs · {R['prim']} primaries · hops med {int(np.median(R['hop']))} (range {R['hop'].min()}-{R['hop'].max()})")
    ax.set_box_aspect((1,1,1)); ax.view_init(elev=5,azim=-90)
    ax.set_xlim(-7,7); ax.set_zlim(-7,7); ax.set_ylim(0,15); ax.set_xlabel('x'); ax.set_ylabel('y')
plt.tight_layout(); plt.savefig("/home/chris/central-park-walk/tmp/leafback_v2_compare.png",dpi=110)
print("\n[render] tmp/leafback_v2_compare.png")

fig2,ax=plt.subplots(figsize=(5,7)); tt=np.linspace(0,1,100)
ax.plot( crown_dome(tt), DOME['base']+tt*(H-DOME['base']),'--',c='#999',label='v1 dome')
ax.plot(-crown_dome(tt), DOME['base']+tt*(H-DOME['base']),'--',c='#999')
ax.plot( crown_real(tt), REAL['base']+tt*(H-REAL['base']),'-',c='#2e7d32',label='v2 iNat-derived')
ax.plot(-crown_real(tt), REAL['base']+tt*(H-REAL['base']),'-',c='#2e7d32')
ax.plot([0,0],[0,REAL['base']],'-',c='#795548',lw=3)
ax.set_aspect('equal'); ax.legend(); ax.set_title('Crown envelope: placeholder vs iNat-derived'); ax.set_xlim(-7,7); ax.set_ylim(0,15)
plt.tight_layout(); plt.savefig("/home/chris/central-park-walk/tmp/leafback_v2_envelope.png",dpi=110)
print("[render] tmp/leafback_v2_envelope.png")

json.dump({"dome":{"sprigs":len(R1['sprigs']),"primaries":R1['prim'],"hops":{"min":int(R1['hop'].min()),"med":int(np.median(R1['hop'])),"max":int(R1['hop'].max()),"mean":round(float(R1['hop'].mean()),2)},"crown_base_m":round(R1['base'],2),"aspect_WH":1.16},
           "real":{"sprigs":len(R2['sprigs']),"primaries":R2['prim'],"hops":{"min":int(R2['hop'].min()),"med":int(np.median(R2['hop'])),"max":int(R2['hop'].max()),"mean":round(float(R2['hop'].mean()),2)},"crown_base_m":round(R2['base'],2),"aspect_WH":1.00,"profile_source":"iNat obs75867287 + distribution (122865830,11670158)"}},
          open("/home/chris/central-park-walk/tmp/leafback_v2_stats.json","w"),indent=2)
print("[stats] tmp/leafback_v2_stats.json")
