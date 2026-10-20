"""Varese scouting plots from Synergy Sports data (Italian Serie A / LBA 2026-27), BC Roma vs OpenJobMetis Varese.

    python notebooks/varese_synergy_plots.py

Reads the CSVs in data/synergy/varese_lba_2026-10-20/ (pulled from the Synergy web app, Serie A games only:
Varese 4 games, BC Roma 4 logged games; team-tendency gauges in plot 01 use all games played) and writes the PNGs to
reports/synergy_varese_lba_2026-10-20/plots/.

  01   team radar, z-scores vs the 16 LBA teams, team values from all games played
  01b  same, Serie A games only (like for like)
  02   Varese play types run / faced
  03   offensive PPP by play type, BC Roma vs Varese
  04   Varese players, possessions used vs eFG% (number in bubble = points per game)
  05   one figure per player: FG made/attempted by shot location and play type, plus shot type for play types
       with more than 10 attempts (05_player_<name>_shot_profile.png)
  05b  player radars, percentile rank within the Varese roster
  06   possessions used by play type, per player
  07   lineups: usage vs points per possession
  08   lineups: points scored vs allowed per possession
  09   lineups: shot-profile differences

Descriptive only, based solely on the data. Every figure carries the date and the author; BC Roma is always yellow.
"""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'/'synergy'/'varese_lba_2026-10-20'
OUT=ROOT/'reports'/'synergy_varese_lba_2026-10-20'; P=OUT/'plots'; P.mkdir(parents=True,exist_ok=True)
D,P=str(D)+'/',str(P)+'/'; L=D; O=D
Y='#F2B705'; V='#1F3A5F'; G='#8A8F98'
plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#BBBBBB'})
FOOT='Giulia Martini · 20 Oct 2026 · Source: Synergy Sports, 2026-27 · '
SA='Italian Serie A only: Varese 4 games, BC Roma 4 logged games'
pc=lambda s: pd.to_numeric(s.astype(str).str.rstrip('%'),errors='coerce')
def foot(fig,t,y=.008): fig.text(.01,y,FOOT+t,fontsize=7,color='#555')

# ---------- league (16 LBA teams, Serie A, 4 games each) ----------
lo=pd.read_csv(D+'league_LBA_team_offense_SerieA.csv'); ld=pd.read_csv(D+'league_LBA_team_defense_SerieA.csv')
MET=['PPP','eFG%','TO%','%FT','Score%','FG%']; col={'PPP':'ppp','eFG%':'efg','TO%':'to','%FT':'ft','Score%':'score','FG%':'fg'}
SIGN={'offense':{'PPP':1,'eFG%':1,'TO%':-1,'%FT':1,'Score%':1,'FG%':1},'defense':{'PPP':-1,'eFG%':-1,'TO%':1,'%FT':-1,'Score%':-1,'FG%':-1}}
def stats(df,m): x=df[col[m]]; return x.mean(), x.std(ddof=1)
s=pd.read_csv(D+'scouting_report_league_context_VAR_vs_BCR_2026-27.csv')   # all games played (Varese 6, BC Roma 7)
def val_allgames(team,side,m):
    r=s[(s.team==team)&(s.side==side)&(s.metric==m)].value.iloc[0]
    return r
def val_serieA(team,side,m):
    df=lo if side=='offense' else ld; k='VAR' if team=='Varese' else 'BCR'
    return df[df.team==k][col[m]].iloc[0]

def fmt(m,v): return f'{v:.2f}' if m=='PPP' else f'{v:.1f}%'

def team_radar(getter,fname,title,note):
    fig,axs=plt.subplots(1,2,figsize=(12.5,6.6),subplot_kw=dict(polar=True)); ang=np.r_[np.linspace(0,2*np.pi,6,endpoint=False),0]
    out=[]
    for ax,side in zip(axs,['offense','defense']):
        df=lo if side=='offense' else ld
        for t,c in [('BC Roma',Y),('Varese',V)]:
            z=[]
            for m in MET:
                mu,sd=stats(df,m); v=getter(t,side,m); z.append(SIGN[side][m]*(v-mu)/sd); out.append((t,side,m,v,mu,sd,z[-1]))
            z=np.clip(np.array(z),-3,3); zz=np.r_[z,z[0]]
            ax.plot(ang,zz,color=c,lw=2.2); ax.fill(ang,zz,color=c,alpha=.18); ax.scatter(ang,zz,color=c,s=30,zorder=3,edgecolor='white')
        ax.set_ylim(-3,3); ax.set_yticks([-2,-1,0,1,2]); ax.set_yticklabels(['-2','-1','0','+1','+2'],fontsize=7,color='#666')
        ax.plot(np.linspace(0,2*np.pi,200),[0]*200,color=G,lw=1,ls='--'); ax.set_xticks(ang[:-1]); ax.set_xticklabels([])
        ax.set_title(side.capitalize()+'  (higher z = better for that side)',fontsize=11,pad=40)
        for a,m in zip(ang[:-1],MET):
            sn,cs=np.sin(a),np.cos(a)
            if sn>0.25: offs=(46,28,10); ha='center'; dx=0
            elif sn<-0.25: offs=(-10,-28,-46); ha='center'; dx=0
            else: offs=(18,0,-18); ha='left' if cs>0 else 'right'; dx=10*np.sign(cs)
            for k,(txt,fc,tc) in enumerate([(m,None,'black'),('BCR '+fmt(m,getter('BC Roma',side,m)),Y,'black'),('VAR '+fmt(m,getter('Varese',side,m)),V,'white')]):
                ax.annotate(txt,xy=(a,3.0),xycoords='data',xytext=(dx,offs[k]),textcoords='offset points',ha=ha,va='center',fontsize=9.5 if k==0 else 8,
                            fontweight='bold' if k==0 else 'normal',color=tc,annotation_clip=False,
                            bbox=None if fc is None else dict(boxstyle='round,pad=.25',fc=fc,ec='none'))
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([0],[0],color=Y,lw=3,label='BC Roma'),Line2D([0],[0],color=V,lw=3,label='Varese')],loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.045))
    fig.suptitle(title,fontsize=13,fontweight='bold',x=.02,ha='left',y=.985)
    fig.text(.02,.93,'Radar = z-score vs the 16 LBA teams (0 = LBA mean, one unit = one standard deviation); values in the chips are the raw numbers.',fontsize=8.5,color='#444')
    fig.text(.01,.028,'Score% = share of possessions with at least one point scored. TO% = turnovers per possession. %FT = share of possessions ending in free throws. Defense is sign-flipped so higher is better for that side.',fontsize=7,color='#555')
    foot(fig,note); fig.tight_layout(rect=(0,.07,1,.93)); fig.savefig(P+fname,dpi=160); plt.close()
    return pd.DataFrame(out,columns=['team','side','metric','value','league_mean','league_sd','z_better_is_higher'])

zA=team_radar(val_allgames,'01_team_radar_zscore_LBA_all_games.png','Team tendency vs LBA teams, z-scores (team values: ALL games played)',
    'LBA distribution: 16 teams, Serie A, 4 games each · team values: all games (Varese 6, BC Roma 7)')
zS=team_radar(val_serieA,'01b_team_radar_zscore_LBA_SerieA_only.png','Team tendency vs LBA teams, z-scores (like for like: Serie A only)',
    'LBA distribution: 16 teams, Serie A, 4 games each · Varese 4 games, BC Roma 4 logged games')
pd.concat([zA.assign(basis='all_games'),zS.assign(basis='serieA_only')]).round(3).to_csv(str(OUT)+'/team_zscores_vs_LBA_teams.csv',index=False)


# 02 varese playtypes LBA
vo=pd.read_csv(L+'varese_LBA_playtypes_offense.csv'); vd=pd.read_csv(L+'varese_LBA_playtypes_defense.csv')
fig,axs=plt.subplots(1,2,figsize=(12,5.6))
for ax,d,t in [(axs[0],vo[vo.poss>=10].sort_values('poss'),'Varese offense: play types run'),(axs[1],vd[vd.poss>=10].sort_values('poss'),'Opponents vs Varese: play types faced')]:
    ax.barh(d.play_type,d.poss,color=V,height=.6)
    for i,(p,q) in enumerate(zip(d.poss,d.ppp)): ax.text(p+1,i,f'{p}  ·  {q:.2f} PPP',va='center',fontsize=8)
    ax.set_xlim(0,d.poss.max()*1.4); ax.set_title(t,fontsize=11,loc='left'); ax.set_xlabel('Possessions (label: poss · PPP)')
fig.suptitle('Varese (Serie A, 4 games): possessions by play type and what they yielded',fontsize=13,fontweight='bold',x=.02,ha='left'); foot(fig,SA+' · plays ≥10 poss'); fig.tight_layout(rect=(0,.03,1,.94)); fig.savefig(P+'02_varese_LBA_playtypes.png',dpi=160); plt.close()
# 03 BCR vs VAR offense
bo=pd.read_csv(D+'bcroma_playtypes_offense_2026-27.csv'); m=bo.merge(vo,on='play_type',suffixes=('_b','_v')); m=m[(m.poss_b>=10)&(m.poss_v>=10)].sort_values('poss_v')
fig,ax=plt.subplots(figsize=(10,5.8)); y=np.arange(len(m)); h=.36
ax.barh(y+h/2,m.ppp_b,height=h,color=Y,label='BC Roma (4 Serie A games)'); ax.barh(y-h/2,m.ppp_v,height=h,color=V,label='Varese (4 Serie A games)')
for i,(a,b,pa,pb) in enumerate(zip(m.ppp_b,m.ppp_v,m.poss_b,m.poss_v)): ax.text(a+.02,i+h/2,f'{a:.2f} ({pa})',va='center',fontsize=8); ax.text(b+.02,i-h/2,f'{b:.2f} ({pb})',va='center',fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(m.play_type); ax.set_xlim(0,2.1); ax.set_xlabel('Points per possession (possessions in brackets); sorted by Varese volume'); ax.legend(frameon=False,loc='lower right')
ax.set_title('Offensive PPP by play type: BC Roma vs Varese (Serie A only)',fontsize=13,fontweight='bold',loc='left'); foot(fig,SA+' · plays ≥10 poss for both'); fig.tight_layout(rect=(0,.03,1,1)); fig.savefig(P+'03_playtype_ppp_bcr_vs_var_LBA.png',dpi=160); plt.close()
# players
b=pd.read_csv(L+'varese_LBA_players_cumulative_box.csv'); b=b[b.PLAYER!='TEAM TOTAL'].copy()
for c in ['EFG%','TO%','TS%','%FT']: b[c]=pc(b[c])
b['AST/TO']=pd.to_numeric(b['AST/TO'],errors='coerce'); b['SSM']=pd.to_numeric(b['SSM'])
b=b[~b.PLAYER.str.contains('Della Valle')] if False else b
# ---------- 04 players volume vs efficiency ----------
b['ppg']=b.PTS/b.GP
z=b[b.POSS>=20]; lg=np.average(lo.efg,weights=lo.poss_pg)
fig,ax=plt.subplots(figsize=(9.8,6.2)); ax.axhline(lg,color=G,ls='--',lw=1.2)
ax.text(98,lg+.7,f'LBA average eFG% {lg:.1f} (16 teams, possession-weighted)',fontsize=8,color='#555',ha='right')
ax.scatter(z.POSS,z['EFG%'],s=z.ppg*70,color=V,alpha=.9,edgecolor='white',linewidth=1.5,zorder=3)
for _,r in z.iterrows():
    ax.text(r.POSS,r['EFG%'],f'{r.ppg:.1f}',ha='center',va='center',color='white',fontsize=8,fontweight='bold',zorder=4)
    nm=r.PLAYER.split()[-1]; off={'Renfro':(18,-3,'left'),'Nikolic':(-16,-3,'right'),'Kamagate':(-16,3,'right'),'Alviti':(18,3,'left')}.get(nm,(0,-17-np.sqrt(r.ppg)*3.2,'center'))
    ax.annotate(nm,(r.POSS,r['EFG%']),xytext=off[:2],textcoords='offset points',ha=off[2],va='center',fontsize=9)
ax.set_xlabel('Possessions used (Serie A, 4 games)'); ax.set_ylabel('eFG%'); ax.set_xlim(8,100); ax.set_ylim(28,82)
ax.set_title('Varese players (≥20 poss): volume vs efficiency, Serie A only',fontsize=13,fontweight='bold',loc='left')
ax.text(.99,.02,'number in bubble = points per game (bubble area proportional to it)',transform=ax.transAxes,ha='right',fontsize=8,color='#555')
foot(fig,'Italian Serie A only: Varese 4 games · dashed line = LBA team-level eFG% average'); fig.tight_layout(rect=(0,.03,1,1)); fig.savefig(P+'04_varese_LBA_players_volume_efficiency.png',dpi=160); plt.close()

# 05 radars
r=b[(b.POSS>=25)].copy(); r['TOinv']=-r['TO%']; cols=['PPP','EFG%','TS%','TOinv','AST/TO','%FT','SSM']; labs=['PPP','eFG%','TS%','TO% (inv.)','AST/TO','%FT','Shot making']; R=r[cols].rank(pct=True)
ang=np.r_[np.linspace(0,2*np.pi,len(cols),endpoint=False),0]; n=len(r); fig,axs=plt.subplots(2,4,figsize=(13,8.4),subplot_kw=dict(polar=True))
for ax,(i,q) in zip(axs.flat,r.iterrows()):
    v=np.r_[R.loc[i].values,R.loc[i].values[0]]; ax.plot(ang,v,color=V,lw=2); ax.fill(ang,v,color=V,alpha=.2); ax.set_xticks(ang[:-1]); ax.set_xticklabels(labs,fontsize=6.5); ax.set_yticks([.5]); ax.set_yticklabels([]); ax.set_ylim(0,1)
    ax.set_title(f"{q.PLAYER.split(' ',1)[1]}\n{q['OFFENSIVE ROLE']} · {int(q.POSS)} poss",fontsize=8.5,pad=20)
for ax in axs.flat[n:]: ax.axis('off')
fig.suptitle('Varese players (≥25 poss, Serie A): percentile rank within the Varese roster, not vs league',fontsize=13,fontweight='bold',x=.02,ha='left'); foot(fig,SA+' · ring = roster median; role labels as shown by Synergy for Serie A games'); fig.tight_layout(rect=(0,.03,1,.95)); fig.savefig(P+'05b_varese_LBA_player_radars_roster_percentile.png',dpi=160); plt.close()
# 06 mix
pp=pd.read_csv(L+'varese_LBA_players_playtypes_offense.csv'); pv=pp.pivot_table(index='player',columns='play_type',values='poss',aggfunc='sum',fill_value=0); pv=pv[pv.sum(axis=1)>=25]; pv=pv.loc[pv.sum(axis=1).sort_values().index]; order=pv.sum().sort_values(ascending=False).index; pv=pv[order]
pal=['#1F3A5F','#3E6DA8','#7FA6D6','#B9CFEA','#4C4C4C','#8A8F98','#C2C5CA','#2E7D6B','#7BB5A6','#B04A3A','#D99A8F']
fig,ax=plt.subplots(figsize=(11,5.8)); left=np.zeros(len(pv))
for c,col in zip(order,pal): ax.barh(pv.index,pv[c],left=left,color=col,edgecolor='white',linewidth=1,label=c,height=.65); left+=pv[c].values
ax.set_xlabel('Possessions used by play type (possessions ended by the player: shot, turnover or free-throw trip; not time on court)'); ax.legend(frameon=False,fontsize=7.5,ncol=3,loc='lower right'); ax.set_title('Varese players: possessions used by play type (≥25 poss, Serie A)',fontsize=13,fontweight='bold',loc='left'); foot(fig,SA+' · possessions = ones the player ended (shot, TO, FT trip)'); fig.tight_layout(rect=(0,.03,1,1)); fig.savefig(P+'06_varese_LBA_player_playtype_mix.png',dpi=160); plt.close()
# ---------- 05 player radars: shot zones and play types, attempted vs made ----------
PL=['Hale','Duke','Alviti','Renfro','Nikolic','Kamagate','Librizzi','Roby']
ZG_ORDER=['Paint','Mid-range','Corner 3','Wing 3','Top 3']
zp=pd.read_csv(D+'varese_LBA_players_fg_by_zone_and_playtype.csv')
PT_ORDER=['Spot Up','Transition','P&R Ball Handler','P&R Roll Man','Cut','Offensive Rebounds (Put Backs)','Isolation','Off Screen','Other']
PT_LAB=['Spot up','Transition','P&R ball\nhandler','P&R roll','Cut','Put backs','Isolation','Off screen','Other*']
def _grp(p,dim,order):
    d=zp[(zp.player==p)&(zp.dimension==dim)].set_index('category'); return [(int(d.loc[g,'fgm']),int(d.loc[g,'fga'])) for g in order]
def zgrp(p): return _grp(p,'shot_location',ZG_ORDER)
def ptgrp(p): return _grp(p,'play_type',PT_ORDER)
def radar(ax,labels,mades_atts,title):
    n=len(labels); ang=np.r_[np.linspace(0,2*np.pi,n,endpoint=False),0]
    M=np.array([x[0] for x in mades_atts],float); A=np.array([x[1] for x in mades_atts],float); mx=max(A.max(),1)
    ax.plot(ang,np.r_[A,A[0]],color=V,lw=1.2); ax.fill(ang,np.r_[A,A[0]],color=V,alpha=.15)
    ax.plot(ang,np.r_[M,M[0]],color=Y,lw=1.6); ax.fill(ang,np.r_[M,M[0]],color=Y,alpha=.55)
    ax.set_ylim(0,mx*1.28); ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels,fontsize=7.5); ax.set_yticks([mx]); ax.set_yticklabels([f'{int(mx)}'],fontsize=6.5,color='#777'); ax.tick_params(axis='x',pad=14)
    for a_,m_,at in zip(ang[:-1],M,A):
        if at>0: ax.text(a_,mx*1.13,f'{int(m_)}/{int(at)}',ha='center',va='center',fontsize=7,color='#222',fontweight='bold')
    ax.set_title(title,fontsize=8,pad=14,color='#444')
st=pd.read_csv(D+'varese_LBA_players_shottype_within_playtype_over10.csv'); SHOT={}
for r_ in st.itertuples(): SHOT.setdefault((r_.player,r_.play_type),[]).append((r_.shot_type,r_.fga,r_.fgm))
meta=b.set_index(b.PLAYER.str.split(' ').str[-1])
from matplotlib.patches import Patch
from matplotlib.gridspec import GridSpec
PTL={'Spot Up':'Spot up','P&R Ball Handler':'P&R ball handler','Isolation':'Isolation'}
for p in PL:
    ex=[k for k in SHOT if k[0]==p]; n=2+len(ex)
    fig=plt.figure(figsize=(max(5.3*n,12.5),6.8)); gs=GridSpec(1,n,figure=fig,wspace=.6,left=.05,right=.95 if n==2 else .985,top=.78,bottom=.19)
    a1=fig.add_subplot(gs[0,0],projection='polar'); a2=fig.add_subplot(gs[0,1],projection='polar')
    radar(a1,ZG_ORDER,zgrp(p),'Shot location (made/attempted)'); radar(a2,PT_LAB,ptgrp(p),'Play type (made/attempted)')
    for j,k in enumerate(ex):
        ax=fig.add_subplot(gs[0,2+j]); d=sorted(SHOT[k],key=lambda x:-x[1]); y=np.arange(len(d))[::-1]
        ax.barh(y,[x[1] for x in d],color=V,alpha=.25,height=.62); ax.barh(y,[x[2] for x in d],color=Y,height=.62)
        for yy,x in zip(y,d): ax.text(x[1]+.2,yy,f'{x[2]}/{x[1]}',va='center',fontsize=8,fontweight='bold')
        ax.set_yticks(y); ax.set_yticklabels([x[0] for x in d],fontsize=8); ax.set_xlim(0,max(x[1] for x in d)*1.25); ax.set_xlabel('Field goal attempts',fontsize=8)
        tot=sum(x[1] for x in d); ax.set_title(f'Shot type within {PTL[k[1]]}\n({tot} attempts; made/attempted)',fontsize=8.5,pad=14,color='#444')
        ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0)
    fga=int(sum(a_ for _,a_ in zgrp(p)))
    fig.text(.02,.955,f'{p}: field goals attempted vs made',fontsize=14,fontweight='bold',ha='left')
    fig.text(.02,.905,f'{fga} FGA, {int(meta.loc[p,"FG MADE"])} made, {int(meta.loc[p,"POSS"])} possessions used · Italian Serie A, Varese 4 games',fontsize=9,color='#444')
    fig.legend(handles=[Patch(fc=V,alpha=.3,label='Attempted'),Patch(fc=Y,alpha=.8,label='Made')],loc='lower left',ncol=2,frameon=False,bbox_to_anchor=(.02,.085))
    note='*Other = handoffs, post-ups, miscellaneous plays. Zones: Synergy 11-zone chart grouped as Paint (incl. rim), Mid-range (other two-point zones), Corner 3, Wing 3, Top 3. Outer ring label = max attempts. Free throws excluded.'
    if ex: note+=' Shot-type panels shown only for play types with more than 10 attempts.'
    else: note+=' No play type has more than 10 attempts, so no shot-type panel.'
    import textwrap; fig.text(.02,.075,textwrap.fill(note,width=int(max(5.3*n,12.5)*13.5)),fontsize=6.8,color='#555',va='top'); foot(fig,'Italian Serie A only',y=.008)
    fig.savefig(P+f'05_player_{p.lower()}_shot_profile.png',dpi=150); plt.close()


m=pd.read_csv(L+'varese_LBA_lineups_noDellaValle_off_def.csv')
short=lambda s:'-'.join(p.split()[0][:3] for p in s.split(' / ')); m['k']=m.lineup.map(short)
VAR_PPP=324/366   # Varese team offense, Serie A, 4 games: 324 pts / 366 poss
# ---- 07
o=m.dropna(subset=['poss']).copy()
fig,ax=plt.subplots(figsize=(11.5,6.6)); ax.axhline(VAR_PPP,color='#555',ls='--',lw=1.2)
ax.text(39.5,VAR_PPP-.035,f'Varese whole-team offense in Serie A: {VAR_PPP:.2f} points per possession\n(324 points in 366 possessions, all lineups together, including those not shown)',ha='right',va='top',fontsize=8.5,color='#333')
ax.scatter(o.poss,o.ppp,s=o.pts*22,color=V,alpha=.85,edgecolor='white',linewidth=1.3,zorder=3)
for _,q in o[o.pts>=12].iterrows(): ax.text(q.poss,q.ppp,f'{int(q.pts)}',ha='center',va='center',color='white',fontsize=8.5,fontweight='bold',zorder=4)
OFF={'Alv-Duk-Hal-Kam-Rob':(30,-20,'left'),'Alv-Duk-Nik-Hal-Ren':(12,8,'left'),'Alv-Duk-Nik-Hal-Rob':(-8,10,'right'),'Alv-Hal-Ren-Rob-Ika':(10,8,'left'),'Duk-Lib-Ren-Rob-Ika':(40,-52,'left'),'Alv-Duk-Hal-Ren-Rob':(14,6,'left')}
for _,q in o[(o.poss>=12)|(o.ppp>=1.25)].iterrows():
    dx,dy,ha=OFF.get(q.k,(8,8,'left')); ax.annotate(q.k,(q.poss,q.ppp),xytext=(dx,dy),textcoords='offset points',fontsize=7.5,ha=ha,arrowprops=dict(arrowstyle='-',color='#999',lw=.7,shrinkA=0,shrinkB=6) if abs(dx)>=30 else None)
ax.set_xlabel('Offensive possessions with the lineup on court (usage)'); ax.set_ylabel('Points per possession (lineup on court)')
ax.set_title('Varese 5-man lineups (Serie A): usage vs scoring efficiency',fontsize=13,fontweight='bold',loc='left')
ax.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=V,markersize=m_,label=l) for m_,l in [(7,'~5 pts'),(11,'~13 pts'),(17,'~27 pts')]]+[Line2D([0],[0],color='#555',ls='--',label='Varese whole-team offense PPP (0.89)')],
          title='Bubble area = points scored by the lineup',loc='upper right',frameon=False,fontsize=8,title_fontsize=8,labelspacing=1.2,borderpad=1)
ax.text(.99,.02,'number in bubble = points scored (shown for lineups with ≥12 points); small samples below ~15 poss',transform=ax.transAxes,ha='right',fontsize=7.5,color='#555')
foot(fig,'Serie A, Varese 4 games · lineups with ≥5 offensive possessions, excl. Della Valle (22 lineups)'); fig.tight_layout(rect=(0,.03,1,1)); fig.savefig(P+'07_lineups_usage_vs_ppp_LBA.png',dpi=160); plt.close()
# ---- 08
b2=m.dropna(subset=['poss','def_poss']); b2=b2[(b2.poss>=5)&(b2.def_poss>=5)].copy()
fig,ax=plt.subplots(figsize=(13.2,7.2)); ax.plot([.2,1.9],[.2,1.9],color=G,ls='--',lw=1,zorder=1)
ax.scatter(b2.ppp,b2.opp_ppp,s=(b2.poss+b2.def_poss)*5,color=V,alpha=.8,edgecolor='white',linewidth=1.3,zorder=3)
full=lambda s:' / '.join(s.split(' / '))
def lab(q,txt,xy,ha):
    ax.annotate(txt,(q.ppp,q.opp_ppp),xytext=xy,textcoords='offset points',fontsize=8,ha=ha,va='center',arrowprops=dict(arrowstyle='-',color='#777',lw=.8),bbox=dict(boxstyle='round,pad=.3',fc='white',ec='#CCCCCC'))
qx=b2.loc[b2.ppp.idxmax()]; qy=b2.loc[b2.opp_ppp.idxmax()]; qm=b2.loc[b2.opp_ppp.idxmin()]
if qx.lineup==qy.lineup: lab(qx,f'Highest x and highest y (1.83 scored / 1.60 allowed):\n{full(qx.lineup)}\n{int(qx.poss)} off. / {int(qx.def_poss)} def. poss',(-110,-12),'right')
else:
    lab(qx,f'Highest x: {full(qx.lineup)} ({qx.ppp:.2f})',(-130,-20),'right'); lab(qy,f'Highest y: {full(qy.lineup)} ({qy.opp_ppp:.2f})',(-130,10),'right')
b2['tot']=b2.poss+b2.def_poss; big=b2[b2.tot>=25].sort_values('tot',ascending=False).reset_index(drop=True)
for i,q in big.iterrows(): ax.text(q.ppp,q.opp_ppp,str(i+1),ha='center',va='center',color='white',fontsize=8.5,fontweight='bold',zorder=5)
key='Largest bubbles (≥25 total possessions)\n'+'\n'.join(f'{i+1}  {q.lineup.replace(" / ",", ")}\n     {int(q.poss)} off. / {int(q.def_poss)} def. poss · {q.ppp:.2f} scored / {q.opp_ppp:.2f} allowed' for i,q in big.iterrows())
fig.text(.70,.86,key,fontsize=8,va='top',ha='left',linespacing=1.45,bbox=dict(boxstyle='round,pad=.6',fc='#F7F7F7',ec='#DDDDDD'))
lab(qm,f'Lowest y (best defense, {qm.opp_ppp:.2f}):\n{full(qm.lineup)}\n{int(qm.poss)} off. / {int(qm.def_poss)} def. poss',(110,12),'left')
ax.set_xlabel('Points scored per possession (lineup on court)'); ax.set_ylabel('Points allowed per possession (lineup on court)'); ax.invert_yaxis()
ax.set_title('Varese lineups: scoring vs allowing (Serie A)',fontsize=13,fontweight='bold',loc='left')
ax.legend(handles=[Line2D([0],[0],color=G,ls='--',label='Points scored = points allowed (below the line: scores more than allows)'),
                   Line2D([0],[0],marker='o',color='w',markerfacecolor=V,markersize=5,label='Bubble area = offensive + defensive possessions (10 to 66)')],loc='lower left',frameon=False,fontsize=8)
fig.text(.01,.035,f'Included: lineups with at least 5 possessions on BOTH offense and defense ({len(b2)} lineups), excluding Della Valle. Y axis inverted (better defense is higher on the chart).',fontsize=7.5,color='#444')
foot(fig,'Serie A, Varese 4 games'); fig.tight_layout(rect=(0,.06,.68,1)); fig.savefig(P+'08_lineups_offense_vs_defense_LBA.png',dpi=160); plt.close()
# 09 style
zz=o[o.poss>=10].sort_values('tpa_rate'); fig,axs=plt.subplots(1,5,figsize=(14,5),sharey=True)
for ax,(c,t) in zip(axs,[('tpa_rate','3PA / FGA'),('ft_rate','FTA / FGA'),('to_pct','TO% (Synergy)'),('efg','eFG%'),('ssm','Shot making (SSM)')]):
    v=zz[c]/100 if c=='to_pct' else zz[c]; ax.barh(range(len(zz)),v,color=V,height=.6); ax.axvline(v.mean(),color=G,ls='--',lw=1); ax.set_title(t,fontsize=10)
    for i,x in enumerate(v): ax.text(max(x,0),i,f' {x:.2f}',va='center',fontsize=7)
axs[0].set_yticks(range(len(zz))); axs[0].set_yticklabels([f'{k} ({int(p)})' for k,p in zip(zz.k,zz.poss)],fontsize=7.5)
fig.suptitle('Lineup shot-profile differences (Serie A, ≥10 off. poss; dashed = mean of these lineups; poss in brackets)',fontsize=12,fontweight='bold',x=.02,ha='left'); foot(fig,'Serie A, Varese 4 games · excl. Della Valle'); fig.tight_layout(rect=(0,.03,1,.95)); fig.savefig(P+'09_lineups_style_profile_LBA.png',dpi=160); plt.close()
