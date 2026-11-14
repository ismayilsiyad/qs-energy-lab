import streamlit as st, pandas as pd, numpy as np, json, os, plotly.graph_objects as go, plotly.express as px, warnings
os.environ.setdefault('AZURE_OPENAI_ENDPOINT','https://qs-energy-proxy.quanskill.workers.dev')  # course AI endpoint (class proxy)
os.environ.setdefault('AZURE_OPENAI_API_KEY','QSEnergy-CQyw8kf8')  # class passcode
warnings.filterwarnings('ignore')
from statsmodels.tsa.holtwinters import ExponentialSmoothing
_HERE=os.path.dirname(os.path.abspath(__file__))
def _bootstrap():
    import subprocess, sys, zipfile, shutil
    if os.path.exists(os.path.join(_HERE,'gold','gold_intervals.csv')): return
    try:
        import gdown
    except ImportError:
        subprocess.run([sys.executable,'-m','pip','install','-q','gdown'],check=True)
        import gdown
    zp=os.path.join(_HERE,'data','pack.zip'); os.makedirs(os.path.dirname(zp),exist_ok=True)
    gdown.download(id='1IXhnaAAXCYJbXn0CukZhDsK18VWXk3GZ', output=zp, quiet=True)
    tmp=os.path.join(_HERE,'data','pack_unpack')
    with zipfile.ZipFile(zp) as z: z.extractall(tmp)
    for root,_,fns in os.walk(tmp):
        for fn in fns:
            folder='gold' if fn in ('gold_intervals.csv','gold_gaps.csv','issues.json') else ''
            os.makedirs(os.path.join(_HERE,folder),exist_ok=True)
            shutil.move(os.path.join(root,fn), os.path.join(_HERE,folder,fn))
    shutil.rmtree(tmp)
_bootstrap()
G=os.path.join(_HERE,'gold')
# BRAND: palette and logo from quanskill.com (dark #0d0908, orange #ff9100, cream #f4efe9)
import base64 as _b64
from PIL import Image as _Im
_BR=os.path.join(_HERE,'brand')
_logo=_b64.b64encode(open(_BR+'/logo.png','rb').read()).decode()
st.set_page_config(page_title='Quanskill Energy Lab',layout='wide',page_icon=_Im.open(_BR+'/icon.png'))

# Chart display wrapper: light template, phone-friendly margins, no clashing dark theme
_pc=st.plotly_chart
def _pc2(fig,*a,**k):
    fig.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#ffffff',margin=dict(l=6,r=6,t=34,b=6),font=dict(family='JetBrains Mono, monospace',size=11,color='#14100d'),legend=dict(orientation='h',y=-0.22,x=0,title=None),autosize=True,colorway=['#27408b','#ff9100','#2e9e6b','#c2410c','#7c5cbf'],height=None if False else fig.layout.height)
    _M={'#636efa':'#27408b','#ef553b':'#ff9100','#00cc96':'#2e9e6b','#ab63fa':'#7c5cbf','#ffa15a':'#c2410c','#19d3f3':'#4a90c2'}  # palette mapping
    for _t in fig.data:
        try:
            if _t.type=='bar' and isinstance(_t.marker.color,str) and _t.marker.color.lower() in _M: _t.marker.color=_M[_t.marker.color.lower()]
            if _t.type=='scatter':
                if _t.line.color and _t.line.color.lower() in _M: _t.line.color=_M[_t.line.color.lower()]
                if isinstance(_t.marker.color,str) and _t.marker.color.lower() in _M: _t.marker.color=_M[_t.marker.color.lower()]
        except Exception: pass
    fig.update_xaxes(automargin=True); fig.update_yaxes(automargin=True)
    k['theme']=None; k['use_container_width']=True; k.setdefault('config',{'displayModeBar':False})
    return _pc(fig,*a,**k)
st.plotly_chart=_pc2
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@500;700&display=swap');
.stApp{background:#f4efe9}
.block-container{padding-top:1.4rem;max-width:1250px}
h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif;letter-spacing:-.01em;color:#14100d}
.hero{background:#0d0908;border:1px solid #ff910066;padding:20px 28px;border-radius:16px;color:#fff;margin-bottom:14px;display:flex;align-items:center;gap:26px}
.hero img{height:44px}.hero h1{color:#fff;margin:0;font-size:1.8rem;font-family:'Space Grotesk',sans-serif}
.hero p{color:#cdbfb2;margin:.3rem 0 0;font-family:'JetBrains Mono',monospace;font-size:.82rem}
.hero .tag{margin-left:auto;background:#ff9100;color:#14100d;font-family:'JetBrains Mono',monospace;font-size:.72rem;padding:6px 12px;border-radius:8px;font-weight:600;white-space:nowrap}
.card{background:#fff;border-left:5px solid #ff9100;padding:12px 16px;border-radius:8px;margin:8px 0;color:#14201b;box-shadow:0 1px 2px #0001}
.bad{border-left-color:#c2410c}.good{border-left-color:#2e9e6b}
button[data-baseweb=tab]{font-family:'JetBrains Mono',monospace;font-size:.82rem}
button[data-baseweb=tab][aria-selected=true],button[data-baseweb=tab][aria-selected=true] p{color:#e07b00!important}
div[data-baseweb=tab-highlight]{background:#ff9100!important}
.stButton>button{border:1px solid #ff9100;color:#14100d;background:#fff}.stButton>button:hover{background:#ff9100;color:#14100d;border-color:#ff9100}

/* RESP4 */ .hero *,.hero h1 span{color:inherit!important}.hero p{color:#cdbfb2!important}
[data-testid=stMetricLabel] p{white-space:normal!important;overflow:visible!important}
/* RESP6 */ .stButton>button{white-space:normal!important;height:auto!important;min-height:2.4rem;text-align:left;line-height:1.3;padding:.45rem .7rem}.stButton>button p{white-space:normal!important;text-align:left}
/* RESP3 header overlap fix */
header[data-testid=stHeader]{background:transparent!important;height:2.4rem!important}
.block-container{padding-top:3rem!important}
@media (max-width:820px){.block-container{padding-top:2.8rem!important}}
/* RESP2 responsive + light theme lock */
html,body,.stApp,[data-testid=stAppViewContainer]{color-scheme:light}
.stApp,.stApp p,.stApp label,.stApp span,.stApp li,[data-testid=stMarkdownContainer],[data-testid=stWidgetLabel] *,div[role=radiogroup] label *{color:#14100d}
.hero h1,.hero p{color:#fff!important}.hero p{color:#cdbfb2!important}
[data-testid=stMetricValue]{color:#14100d}
div[data-baseweb=tab-list]{overflow-x:auto;scrollbar-width:thin;gap:2px}
button[data-baseweb=tab]{white-space:nowrap;color:#14100d!important}
div[role=radiogroup]{gap:.4rem 1rem;flex-wrap:wrap}
@media (max-width:820px){
 .block-container{padding:.6rem .7rem 2rem!important}
 .hero{padding:12px 14px;gap:12px;flex-direction:row;align-items:center;border-radius:12px}
 .hero img{height:26px}.hero h1{font-size:1.15rem!important}
 .hero p{font-size:.68rem!important;line-height:1.35;margin:.15rem 0 0!important}
 h2,h3{font-size:1.15rem!important}
 button[data-baseweb=tab]{font-size:.72rem;padding:.4rem .55rem}
 [data-testid=stMetricValue]{font-size:1.25rem}
 .card{padding:9px 11px;font-size:.88rem}
 [data-testid=stHorizontalBlock]{flex-wrap:wrap;gap:.5rem}
 [data-testid=stHorizontalBlock]>[data-testid=stColumn]{min-width:46%!important}
}
@media (max-width:480px){.hero p{display:none}.hero img{height:24px}}
</style>""",unsafe_allow_html=True)
SLOTS=['06:00','09:30','11:30','17:00','18:00','20:00','22:00','04:00']
CONS=['LV11','LV12']
@st.cache_data
def load():
    I=pd.read_csv(G+'/gold_intervals.csv',parse_dates=['start','end'])
    Gp=pd.read_csv(G+'/gold_gaps.csv',parse_dates=['gap_start','gap_end'])
    I['pday']=(I.start-pd.Timedelta(hours=6)).dt.normalize()
    I['slot']=I.start.dt.strftime('%H:%M')
    I['weekend']=I.pday.dt.dayofweek>=5
    I['month']=I.pday.dt.to_period('M').astype(str)
    return I,Gp,json.load(open(G+'/issues.json'))
I,Gp,issues=load()
M=I[I.quality=='measured']
cons=M[M.meter.isin(CONS)]
meas={m:M[M.meter==m].kwh.sum() for m in ['LV11','LV12','SOLAR']}
brid={m:Gp[Gp.meter==m].energy_kwh.sum() for m in ['LV11','LV12','SOLAR']}
cons_meas=meas['LV11']+meas['LV12']; cons_brid=brid['LV11']+brid['LV12']
D=M.groupby(['pday','meter']).agg(kwh=('kwh','sum'),n=('kwh','count')).reset_index()
Dp=D.pivot(index='pday',columns='meter',values='kwh')
Dn=D.pivot(index='pday',columns='meter',values='n')
full=(Dn[CONS]==8).all(axis=1)
daily=Dp.loc[full,CONS].sum(axis=1)
st.markdown(f"""<div class='hero'><img src='data:image/png;base64,{_logo}'><div><h1>Energy Lab</h1><p>A wood-processing plant, 2 years of meter sheets, rebuilt from the raw registers. Every number reconciles to the meter.</p></div></div>""",unsafe_allow_html=True)
import sys; sys.path.insert(0,_HERE)
import insights as IN
_order=[(0,'Overview'),(1,'Load profile'),(2,'Cost analysis'),(7,'Bill estimator'),(8,'Peak shifting'),(9,'Solar scenarios'),(3,'Anomaly detection'),(10,'Health watch'),(4,'Data quality'),(5,'Forecasting'),(11,'Forecast tracking'),(6,'Ask the data')]
_t=st.tabs([n for _,n in _order]); tabs={k:_t[j] for j,(k,_) in enumerate(_order)}
SH={'04:00':2,'06:00':3.5,'09:30':2,'11:30':5.5,'17:00':1,'18:00':2,'20:00':2,'22:00':6}
IN.ABOUT.update({
 7:("What you are looking at","An estimate of the monthly electricity bill for the two consumption meters. Enter your tariff prices and the app multiplies them by the measured energy in each band (normal and off-peak). The default prices are <b>illustrative placeholders</b>, not a contract. Months with fewer than 25 measured days are marked partial and are left out of the typical-month figure, because missing sheets would understate their cost."),
 8:("What you are looking at","The bars compare average energy per interval across the production day, before and after moving part of the evening peak into the off-peak window (22:00 to 04:00). The slider sets the share moved. The saving uses the editable <b>illustrative</b> prices and assumes the load can really be rescheduled, which only the plant can confirm. Intervals differ in length, so the line shows average kW as well as kWh."),
 9:("What you are looking at","A what-if for a larger solar array. The measured solar output is multiplied by the chosen factor and matched, interval by interval, against measured consumption. Solar can only offset the power the plant draws at that moment: surplus is not counted, and no battery or grid export is modelled. The curve shows how the offset share grows, and flattens, as the array gets larger."),
 10:("What you are looking at","For each consumption meter, the share of readings per month that are unusual compared with that meter's own history for the same time slot and weekday or weekend (same robust z-score as Anomaly detection). A rising trend is an early warning that the plant's behaviour is drifting. It is a whole-plant signal: the sheets hold no per-machine sensors, so it cannot say which machine is responsible."),
 11:("What you are looking at","A check on how trustworthy the forecast has been. The tracked model is the current backtest winner from the Forecasting page (Holt-Winters, Prophet or gradient boosting). It is re-run on earlier data only and its week-ahead predictions are compared with what really happened. Each bar is one week of error. Drift is flagged when recent weeks are clearly worse than earlier ones, or when the model keeps over- or under-predicting in the same direction."),
})
def m_hw(tr,n):
    return ExponentialSmoothing(tr,trend=None,seasonal='add',seasonal_periods=7).fit().forecast(n).values
def m_pr(tr,n):
    from prophet import Prophet
    m=Prophet(weekly_seasonality=True,daily_seasonality=False,yearly_seasonality=False)
    m.fit(pd.DataFrame({'ds':tr.index,'y':tr.values}))
    return m.predict(m.make_future_dataframe(periods=n,freq='D')).tail(n).yhat.values
def m_gb(tr,n):
    from sklearn.ensemble import HistGradientBoostingRegressor
    def feats(idx,hist):
        X=pd.DataFrame(index=idx); X['dow']=idx.dayofweek; X['doy']=idx.dayofyear
        X['lag7']=hist.reindex(idx-pd.Timedelta(days=7)).values; X['lag14']=hist.reindex(idx-pd.Timedelta(days=14)).values
        return X
    Xtr=feats(tr.index,tr).dropna(); gbm=HistGradientBoostingRegressor(max_iter=300,learning_rate=.06).fit(Xtr,tr.loc[Xtr.index])
    cur=tr.copy(); out=[]
    for _ in range(n):
        nxt=cur.index[-1]+pd.Timedelta(days=1); out.append(float(gbm.predict(feats(pd.DatetimeIndex([nxt]),cur))[0])); cur.loc[nxt]=out[-1]
    return np.array(out)
MODELS={'Holt-Winters':m_hw,'Prophet':m_pr,'Gradient boosting':m_gb}
@st.cache_data
def backtest(s,h):
    err={k:[] for k in MODELS}; yy={k:[] for k in MODELS}; resid={k:[] for k in MODELS}; rn=[]; ry=[]
    for i in range(6):
        cut=len(s)-h*(i+1)
        if cut<28: break
        tr,te=s.iloc[:cut],s.iloc[cut:cut+h]
        nv=np.tile(tr.iloc[-7:].values,h//7+1)[:h]; rn.append(np.abs(te.values-nv).sum()); ry.append(te.values.sum())
        for k,fn in MODELS.items():
            try: p=fn(tr,h)
            except Exception: continue
            err[k].append(np.abs(te.values-p).sum()); yy[k].append(te.values.sum()); resid[k].append(te.values-p)
    wape={k:(sum(err[k])/sum(yy[k]) if err[k] else None) for k in MODELS}
    ok=[k for k in MODELS if wape[k] is not None]
    champ=min(ok,key=lambda k:wape[k]) if ok else None
    return dict(wape=wape,naive=(sum(rn)/sum(ry) if ry else None),champ=champ,resid=(np.concatenate(resid[champ]) if champ else np.array([0.])),nwin=len(ry))
@st.cache_data
def track(s,H,nw,champ):
    fn=MODELS[champ]; recs=[]; fcs=[]
    for i in range(nw,0,-1):
        cut=len(s)-H*i
        if cut<28: continue
        tr,te=s.iloc[:cut],s.iloc[cut:cut+H]
        try: p=fn(tr,H)
        except Exception: continue
        recs.append(dict(week=str(te.index[0].date()),wape=float(np.abs(te.values-p).sum()/te.values.sum()*100),bias=float((p-te.values).sum()/te.values.sum()*100)))
        fcs.append(pd.DataFrame({'actual':te.values,'forecast':p},index=te.index))
    return recs,fcs
with tabs[0]:
    IN.begin(0)
    c=st.columns(4)
    c[0].metric('Measured consumption',f'{cons_meas/1e6:,.2f} GWh')
    c[1].metric('Bridged gaps (LV11+LV12)',f'{cons_brid/1e6:,.2f} GWh',help='Consumption meters LV11 + LV12 only. Energy the register proves was used on days with no sheet. The solar meter has its own small gaps (generation), shown separately.')
    c[2].metric('Solar generated',f'{meas["SOLAR"]/1e3:,.0f} MWh')
    c[3].metric('Days with no sheet',f"{int(Gp[Gp.meter=='LV12'].hours.sum()/24)} days",help='Calendar days with no meter sheet. The energy for them is recovered from the register difference.')
    st.markdown("<div class='card'><b>How the numbers were rebuilt.</b> On 2021-01-05 five meter registers dropped to 0 and came back (9.10 and 3.40 million kWh on the register scale). Readings of 0 are treated as dropouts, not as real values, and each gap is recovered from the register difference. The solar meter is generation and is never added to consumption.</div>",unsafe_allow_html=True)
    f=go.Figure()
    for m,col in zip(CONS,['#27408b','#ff9100']):
        f.add_bar(x=Dp.index,y=Dp[m],name=m,marker_color=col)
    f.add_scatter(x=Dp.index,y=Dp['SOLAR'],name='Solar (generation)',line=dict(color='#2e9e6b'))
    for _,g in Gp[(Gp.meter=='LV12')&(Gp.hours>=48)].iterrows():
        f.add_vrect(x0=g.gap_start,x1=g.gap_end,fillcolor='#d9534f',opacity=.12,line_width=0)
    f.update_layout(barmode='stack',template='plotly_white',height=380,yaxis_title='kWh per production day (06:00 to 06:00)',legend=dict(orientation='h',y=1.1),margin=dict(t=30))
    st.plotly_chart(f,use_container_width=True)
    st.caption('Red bands: days with no sheet. The register still proves how much energy passed through them; it is counted in the "bridged" KPI, not drawn as fake daily bars.')
    idle=(daily<0.3*daily.median()).sum()
    night=cons[cons.slot=='22:00'].kwh.sum()/cons.kwh.sum()
    top=cons.groupby('slot').kwh.sum().idxmax()
    st.subheader('Three things the data says')
    st.markdown(f"- The plant drew **{daily.mean():,.0f} kWh on an average full day** and sat near-idle on **{idle} of {len(daily)} days** (under 30% of the median).\n- The 22:00 to 04:00 off-peak window carries **{night:.0%}** of consumption.\n- Solar offsets **{meas['SOLAR']/cons_meas:.1%}** of metered consumption.")
    IN.panel(0)
with tabs[1]:
    IN.begin(1)
    st.markdown("<div class='card'>Intervals are 1 to 6 hours long, so energy per interval is not comparable. Power (kW = kWh / hours) is.</div>",unsafe_allow_html=True)
    m=st.radio('Meter',['LV11','LV12','SOLAR'],horizontal=True)
    d=M[M.meter==m]
    H=d.pivot_table(index='slot',columns='month',values='kw',aggfunc='mean').reindex(SLOTS)
    f=px.imshow(H,aspect='auto',color_continuous_scale='Turbo',labels=dict(color='mean kW',x='month',y='interval start'))
    f.update_layout(height=380,margin=dict(t=20))
    st.plotly_chart(f,use_container_width=True)
    w=d.groupby(['slot','weekend']).kw.mean().reset_index().replace({True:'Weekend',False:'Weekday'})
    w['slot']=pd.Categorical(w.slot,SLOTS,ordered=True); w=w.sort_values('slot')
    f2=px.line(w,x='slot',y='kw',color='weekend',markers=True,template='plotly_white',labels=dict(kw='mean kW',slot='interval start'))
    f2.update_layout(height=320); st.plotly_chart(f2,use_container_width=True)
    IN.panel(1)
with tabs[2]:
    IN.begin(2)
    st.markdown("<div class='card'>Tariffs below are <b>illustrative placeholders</b>: replace them with your contract. The sheets tag no interval as peak, so only normal and off-peak are priced.</div>",unsafe_allow_html=True)
    a,b,c3=st.columns(3)
    rn=a.number_input('Normal VND/kWh',value=1500,step=50); ro=b.number_input('Off-peak VND/kWh',value=900,step=50)
    shift=c3.slider('Shift this % of normal-band load into the 22:00-04:00 window',0,30,10)
    cc=cons.assign(rate=np.where(cons.tariff=='offpeak',ro,rn)); cc['cost']=cc.kwh*cc.rate
    mc=cc.groupby(['month','tariff']).cost.sum().reset_index()
    f=px.bar(mc,x='month',y='cost',color='tariff',template='plotly_white',labels=dict(cost='VND'))
    f.update_layout(height=340); st.plotly_chart(f,use_container_width=True)
    days=cons.pday.nunique(); tot=cc.cost.sum(); nk=cons[cons.tariff!='offpeak'].kwh.sum()
    saved=nk*shift/100*(rn-ro); ann=saved*365/days
    k=st.columns(3)
    k[0].metric('Measured energy cost',f'{tot/1e9:,.2f} bn VND'); k[1].metric(f'Shift {shift}% to off-peak: saving over the data',f'{saved/1e6:,.0f} M VND'); k[2].metric('Annualised',f'{ann/1e6:,.0f} M VND/yr')
    sv=meas['SOLAR']*rn
    st.markdown(f"Solar generation is worth about **{sv/1e6:,.0f} M VND** at the normal rate, if it offsets bought power. Off-peak currently carries {cons[cons.tariff=='offpeak'].kwh.sum()/cons.kwh.sum():.0%} of energy. The saving is only real if the process can run at night: it is a ceiling to test, not a promise.")
    IN.panel(2)
with tabs[3]:
    IN.begin(3)
    thr=st.slider('Robust z threshold',2.5,10.0,3.5,.5)
    m=st.selectbox('Meter',CONS)
    d=M[M.meter==m].copy()
    g=d.groupby(['slot','weekend']).kw
    d['med']=g.transform('median'); d['mad']=g.transform(lambda s:(s-s.median()).abs().median())*1.4826+1
    d['z']=(d.kw-d.med)/d.mad
    A=d[d.z.abs()>=thr].sort_values('z',key=lambda s:-s.abs())
    st.markdown(f"<div class='card'>Each reading is compared with its own meter, time slot and weekday/weekend history (median and MAD), not with other machines. {len(A)} flagged of {len(d):,} intervals.</div>",unsafe_allow_html=True)
    T=A.head(25)[['pday','slot','kw','med','z','o','n']].rename(columns={'pday':'day','kw':'kW','med':'expected kW','o':'register start (M kWh)','n':'register end (M kWh)'}).round(2)
    st.dataframe(T,use_container_width=True,height=300)
    if len(A):
        pick=st.selectbox('Inspect',A.head(25).pday.dt.strftime('%Y-%m-%d').tolist())
        day=d[d.pday==pick].set_index('slot').reindex(SLOTS)
        base=d.groupby('slot').kw.quantile([.1,.9]).unstack().reindex(SLOTS)
        f=go.Figure()
        f.add_scatter(x=SLOTS,y=base[.9],line=dict(width=0),showlegend=False)
        f.add_scatter(x=SLOTS,y=base[.1],fill='tonexty',fillcolor='rgba(39,64,139,.15)',line=dict(width=0),name='normal range (P10-P90)')
        f.add_scatter(x=SLOTS,y=day.kw,mode='lines+markers',name=pick,line=dict(color='#d9534f',width=3))
        f.update_layout(template='plotly_white',height=340,yaxis_title='kW',xaxis_title='interval start',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    IN.panel(3)
with tabs[4]:
    IN.begin(4)
    rows=[]
    for m in ['LV11','LV12','SOLAR']:
        x=I[I.meter==m]; span=(x.end.max()-x.start.min()).total_seconds()/3600
        mh=x[x.quality=='measured'].hours.sum()
        rows.append(dict(meter=m,span_days=round(span/24),measured_pct=round(100*mh/span,1),gap_days=round(Gp[Gp.meter==m].hours.sum()/24),bridged_kWh=round(brid[m])))
    st.dataframe(pd.DataFrame(rows),use_container_width=True)
    gg=Gp[Gp.hours>=24].copy(); gg['gap']=gg.hours/24
    f=px.timeline(gg,x_start='gap_start',x_end='gap_end',y='meter',color='energy_kwh',color_continuous_scale='Reds',template='plotly_white')
    f.update_layout(height=260,margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    st.markdown("**Integrity checks run by the pipeline**")
    if not any('raw sheet totals' in x.get('check','') for x in issues):
        st.info('Raw-sheet reconciliation is unavailable in this processed pack. Run the full data route to compute it.')
    chk=pd.DataFrame(issues)
    st.dataframe(chk,use_container_width=True)
    st.caption('Readings have a 10 kWh resolution (5 decimals of a million kWh), so a single interval carries about +/-10 kWh of rounding. Summing register steps cancels the intermediate rounding, so a daily or monthly total carries only the endpoint resolution (about +/-10 kWh); missing or cleaned readings still matter, so totals are close, not exact.')
    IN.panel(4)
with tabs[5]:
    IN.begin(5)
    h=st.select_slider('Horizon (days)',[7,14,28],value=14)
    s=daily.reindex(pd.date_range(daily.index.min(),daily.index.max())).interpolate(limit=3)
    nn=s.notna().astype(int); seg=(nn.diff().fillna(0)!=0).cumsum(); lastseg=seg[s.notna()].iloc[-1]
    s=s[(seg==lastseg)&s.notna()]
    st.caption(f'Fitted on the most recent continuous segment after filling gaps of up to 3 days: {s.index.min().date()} to {s.index.max().date()} ({len(s)} days). A forecast across missing months would be made up.')
    with st.spinner('Backtesting three models on the same rolling windows...'):
        bt=backtest(s,h)
    if bt['champ'] is None or bt['naive'] is None: st.info('Not enough gap-free history for a backtest.')
    else:
        wape=bt['wape']; wn=bt['naive']; champ=bt['champ']
        C=pd.DataFrame([dict(model=k,WAPE=wape[k]) for k in MODELS if wape[k] is not None]+[dict(model='Repeat last week (baseline)',WAPE=wn)]).sort_values('WAPE')
        k=st.columns(4); k[0].metric('Winning model',champ); k[1].metric('Its error (WAPE)',f"{wape[champ]:.1%}"); k[2].metric('Repeat-last-week error',f'{wn:.1%}'); k[3].metric('Verdict','Beats the baseline' if wape[champ]<wn else 'None beats last week')
        f=go.Figure(); f.add_bar(x=C.model,y=(C.WAPE*100).round(1),marker_color=['#2e9e6b' if m==champ else ('#7c5cbf' if 'baseline' in m else '#27408b') for m in C.model],text=(C.WAPE*100).round(1),textposition='outside')
        f.update_layout(template='plotly_white',height=300,yaxis_title='backtest error, WAPE (%)',margin=dict(t=20),showlegend=False); st.plotly_chart(f,use_container_width=True)
        fidx=pd.date_range(s.index[-1]+pd.Timedelta(days=1),periods=h)
        fc=MODELS[champ](s,h); q=np.quantile(bt['resid'],[.1,.9])
        f=go.Figure(); f.add_scatter(x=s.index[-120:],y=s.values[-120:],name='actual',line=dict(color='#14202b'))
        f.add_scatter(x=fidx,y=fc+q[1],line=dict(width=0),showlegend=False)
        f.add_scatter(x=fidx,y=fc+q[0],fill='tonexty',fillcolor='rgba(255,145,0,.25)',line=dict(width=0),name='80% band from backtest errors')
        f.add_scatter(x=fidx,y=fc,name=champ+' forecast',line=dict(color='#ff9100',width=3))
        f.update_layout(template='plotly_white',height=380,yaxis_title='kWh per day',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
        st.dataframe(C.assign(WAPE=(C.WAPE*100).round(1)).rename(columns={'WAPE':'error (WAPE %)'}),use_container_width=True)
        st.markdown(f"Backtest: {bt['nwin']} rolling windows of {h} days, each predicted using only earlier data. Three models take the same test: Holt-Winters (a smooth weekly curve), Prophet (a flexible trend-and-season model) and gradient boosting (a tree model that learns from calendar and lag patterns). The band is the spread of the winning model's real errors, not a model assumption. If no model beats repeating last week, trust last week - a complex model has to earn its place.")
    IN.panel(5)
with tabs[7]:
    IN.begin(7)
    st.markdown("<div class='card'>Prices below are <b>illustrative placeholders</b>. Enter your own tariff to estimate the bill.</div>",unsafe_allow_html=True)
    a,b,c3,d3=st.columns(4)
    bn=a.number_input('Normal VND/kWh',value=1500,step=50,key='bn'); bo=b.number_input('Off-peak VND/kWh',value=900,step=50,key='bo')
    bf=c3.number_input('Fixed charge per month (VND)',value=0,step=1000000,key='bf'); bv=d3.number_input('VAT %',value=0.0,step=1.0,key='bv')
    bb=cons.assign(rate=np.where(cons.tariff=='offpeak',bo,bn)); bb['cost']=bb.kwh*bb.rate
    mm=bb.groupby('month').agg(kwh=('kwh','sum'),cost=('cost','sum'),days=('pday','nunique')).reset_index()
    mm['bill']=(mm.cost+bf)*(1+bv/100); mm['full']=mm.days>=25
    ok=mm[mm.full]
    k=st.columns(3)
    if len(ok):
        k[0].metric('Typical monthly bill',f'{ok.bill.mean()/1e6:,.0f} M VND'); k[1].metric('Typical monthly energy',f'{ok.kwh.mean()/1e3:,.0f} MWh'); k[2].metric('Average rate paid',f'{ok.cost.sum()/ok.kwh.sum():,.0f} VND/kWh')
    mm['status']=np.where(mm.full,'full month','partial (not in typical)')
    f=px.bar(mm,x='month',y='bill',color='status',template='plotly_white',labels=dict(bill='VND'),color_discrete_map={'full month':'#ff9100','partial (not in typical)':'#c9bfb4'})
    f.update_layout(height=340); st.plotly_chart(f,use_container_width=True)
    st.dataframe(mm[['month','days','kwh','bill','status']].round(0),use_container_width=True,height=260)
    st.caption('Measured consumption only (LV11 + LV12). Bridged gaps and any demand or reactive-power charges are not included.')
    IN.panel(7)
with tabs[8]:
    IN.begin(8)
    offs=sorted(cons[cons.tariff=='offpeak'].slot.unique())
    a,b,c3=st.columns(3)
    pr=a.number_input('Normal VND/kWh',value=1500,step=50,key='pr'); po=b.number_input('Off-peak VND/kWh',value=900,step=50,key='po')
    sh=c3.slider('Share of the evening peak to move',0,50,20,key='psh')
    pk=st.multiselect('Evening peak intervals',['17:00','18:00','20:00'],default=['17:00','18:00','20:00'],key='pk')
    base=cons.groupby('slot').kwh.mean().reindex(SLOTS)
    moved=base[pk].sum()*sh/100 if pk else 0.0
    aft=base.copy()
    for s_ in pk: aft[s_]=base[s_]*(1-sh/100)
    for s_ in offs: aft[s_]=base[s_]+moved/len(offs)
    kwb=base/pd.Series(SH).reindex(SLOTS); kwa=aft/pd.Series(SH).reindex(SLOTS)
    perday=moved*(pr-po)*2; ann=perday*365
    k=st.columns(3); k[0].metric('Energy moved per day (both meters)',f'{moved*2:,.0f} kWh'); k[1].metric('Saving per year (illustrative)',f'{ann/1e6:,.0f} M VND'); k[2].metric('Peak-hour average draw',f'{kwb[pk].mean():,.0f} to {kwa[pk].mean():,.0f} kW' if pk else 'n/a')
    f=go.Figure(); f.add_bar(x=SLOTS,y=base.values,name='today',marker_color='#27408b'); f.add_bar(x=SLOTS,y=aft.values,name='after shifting',marker_color='#ff9100')
    f.update_layout(template='plotly_white',barmode='group',height=360,yaxis_title='average kWh per interval (one meter)',xaxis_title='interval start',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    f=go.Figure(); f.add_scatter(x=SLOTS,y=kwb.values,name='today',line=dict(color='#27408b',width=3)); f.add_scatter(x=SLOTS,y=kwa.values,name='after shifting',line=dict(color='#ff9100',width=3))
    f.update_layout(template='plotly_white',height=300,yaxis_title='average kW per meter',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    st.caption(f'Off-peak window intervals used: {", ".join(offs)}. Assumes the moved load can run at night and ignores capacity limits and process constraints. Prices are illustrative.')
    IN.panel(8)
with tabs[9]:
    IN.begin(9)
    sc=st.slider('Solar array size, times today',1.0,6.0,2.0,.5,key='sc')
    Pv=M.pivot_table(index='start',columns='meter',values='kwh').dropna(subset=['LV11','LV12','SOLAR'])
    cn=Pv.LV11+Pv.LV12; sl=Pv.SOLAR
    def offs_(x): return np.minimum(sl*x,cn).sum()
    o1=offs_(1.0); ox=offs_(sc)
    k=st.columns(3); k[0].metric('Consumption offset by solar',f'{ox/cn.sum():.1%}',delta=f'{(ox-o1)/cn.sum():+.1%} vs today'); k[1].metric('Energy offset',f'{ox/1e3:,.0f} MWh'); k[2].metric('Solar output that goes unused',f'{(sl*sc).sum()-ox:,.0f} kWh'.replace(',000',',000'))
    xs=np.arange(.5,6.01,.5); ys=[offs_(x)/cn.sum()*100 for x in xs]
    f=go.Figure(); f.add_scatter(x=xs,y=ys,mode='lines+markers',line=dict(color='#ff9100',width=3),name='offset share'); f.add_vline(x=sc,line_dash='dot',line_color='#27408b')
    f.update_layout(template='plotly_white',height=320,xaxis_title='array size (times today)',yaxis_title='% of consumption offset',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    av=pd.DataFrame({'cons':cn,'sol':sl*sc}); av['slot']=av.index.strftime('%H:%M'); g=av.groupby('slot').mean().reindex(SLOTS)
    f=go.Figure(); f.add_bar(x=SLOTS,y=g.cons,name='consumption (both meters)',marker_color='#27408b'); f.add_bar(x=SLOTS,y=g.sol,name=f'solar x{sc:g}',marker_color='#ff9100')
    f.update_layout(template='plotly_white',barmode='group',height=300,yaxis_title='average kWh per interval',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
    st.caption(f'Based on {len(Pv):,} intervals where all three meters were measured. Matching is interval by interval with no storage and no export. Scaling is linear, so shading, inverter limits and weather are not modelled.')
    IN.panel(9)
with tabs[10]:
    IN.begin(10)
    thr2=st.slider('Robust z threshold',2.5,10.0,3.5,.5,key='thr2')
    rows=[]
    for m_ in CONS:
        d_=M[M.meter==m_].copy(); g_=d_.groupby(['slot','weekend']).kw
        d_['med']=g_.transform('median'); d_['mad']=g_.transform(lambda s:(s-s.median()).abs().median())*1.4826+1
        d_['flag']=((d_.kw-d_.med)/d_.mad).abs()>=thr2
        r_=d_.groupby('month').agg(n=('flag','size'),rate=('flag','mean')).reset_index(); r_['meter']=m_; rows.append(r_)
    R=pd.concat(rows); R=R[R.n>=100].copy(); R['rate']=R.rate*100
    f=px.line(R,x='month',y='rate',color='meter',markers=True,template='plotly_white',labels=dict(rate='% of readings flagged'),color_discrete_map={'LV11':'#27408b','LV12':'#ff9100'})
    f.update_layout(height=340); st.plotly_chart(f,use_container_width=True)
    out=[]
    for m_ in CONS:
        x_=R[R.meter==m_].sort_values('month')
        if len(x_)>=6:
            rec=x_.rate.iloc[-3:].mean(); bas=x_.rate.iloc[:-3].median(); rising=(rec>=1.5*bas) and (rec-bas>=1)
        else: rec=bas=np.nan; rising=False
        out.append(dict(meter=m_,baseline_pct=round(bas,2),last_3_months_pct=round(rec,2),status='Rising: investigate' if rising else 'Stable'))
    O=pd.DataFrame(out); st.dataframe(O,use_container_width=True)
    for r in out:
        if r['status']!='Stable': st.markdown(f"<div class='card bad'><b>Early warning, {r['meter']}.</b> Unusual readings rose from a baseline of {r['baseline_pct']}% to {r['last_3_months_pct']}% over the last 3 months.</div>",unsafe_allow_html=True)
    if all(r['status']=='Stable' for r in out): st.markdown("<div class='card good'>No meter shows a rising rate of unusual readings at this threshold.</div>",unsafe_allow_html=True)
    st.caption('Rule: the last 3 months average at least 1.5 times the earlier median and at least 1 percentage point higher. Months with fewer than 100 measured readings are skipped. Whole-plant meters only: no per-machine sensors, so this shows that behaviour is shifting, not which machine causes it.')
    IN.panel(10)
with tabs[11]:
    IN.begin(11)
    s2=daily.reindex(pd.date_range(daily.index.min(),daily.index.max())).interpolate(limit=3)
    nn2=s2.notna().astype(int); sg2=(nn2.diff().fillna(0)!=0).cumsum(); ls2=sg2[s2.notna()].iloc[-1]
    s2=s2[(sg2==ls2)&s2.notna()]
    H=7; nw=st.select_slider('Weeks to track',[4,6,8,10],value=8,key='nw')
    with st.spinner('Tracking the winning model week by week...'):
        bt=backtest(s2,H); champ=bt['champ']
        recs,fcs=(track(s2,H,nw,champ) if champ else ([],[]))
    if len(recs)>=4:
        T=pd.DataFrame(recs); F=pd.concat(fcs)
        last=T.wape.iloc[-2:].mean(); ref=T.wape.iloc[:-2].median(); sgn=np.sign(T.bias.iloc[-3:]); biased=(sgn.nunique()==1) and (T.bias.iloc[-3:].abs().min()>3)
        drift=(last>=1.5*ref) or biased
        k=st.columns(4); k[0].metric('Tracked model',champ); k[1].metric('Typical weekly error',f'{ref:.1f}%'); k[2].metric('Last 2 weeks error',f'{last:.1f}%'); k[3].metric('Drift status','Drift: review model' if drift else 'On track')
        f=go.Figure(); f.add_scatter(x=F.index,y=F.actual,name='actual',line=dict(color='#14202b')); f.add_scatter(x=F.index,y=F.forecast,name='forecast made a week earlier',line=dict(color='#ff9100',width=3))
        f.update_layout(template='plotly_white',height=340,yaxis_title='kWh per day',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
        f=go.Figure(); f.add_bar(x=T.week,y=T.wape,name='weekly error %',marker_color=['#c2410c' if i>=len(T)-2 and drift else '#27408b' for i in range(len(T))])
        f.update_layout(template='plotly_white',height=260,yaxis_title='error (%)',xaxis_title='week starting',margin=dict(t=20)); st.plotly_chart(f,use_container_width=True)
        st.dataframe(T.round(1).rename(columns={'wape':'error %','bias':'bias % (+ = over-predicted)'}),use_container_width=True)
        st.caption(f'Tracked model: {champ}, the current backtest winner, re-checked as the data grows. Each week is predicted using only data before it. Drift rule: the last 2 weeks have at least 1.5 times the earlier median error, or the last 3 weeks all miss in the same direction by more than 3%. Gap-free stretch used: {s2.index.min().date()} to {s2.index.max().date()}.')
    else: st.info('Not enough gap-free history to track the forecast.')
    IN.panel(11)
with tabs[6]:
    import sys; sys.path.insert(0,_HERE)
    import importlib, chat; importlib.reload(chat); chat.render(I,Gp,daily)
