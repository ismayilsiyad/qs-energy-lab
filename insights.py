import os, json, base64, html
import streamlit as st
import streamlit.delta_generator as dg

MODEL = os.environ.get('AZURE_OPENAI_VISION_DEPLOYMENT', 'gpt-5.4')
CUR = {'key': None, 'facts': [], 'figs': []}

if not getattr(dg.DeltaGenerator, '_qs_patched', False):
    _om, _op, _od = dg.DeltaGenerator.metric, dg.DeltaGenerator.plotly_chart, dg.DeltaGenerator.dataframe
    def _metric(self, label, value, *a, **k):
        CUR['facts'].append('KPI ' + str(label) + ': ' + str(value)); return _om(self, label, value, *a, **k)
    def _plot(self, fig, *a, **k):
        CUR['figs'].append(fig); return _op(self, fig, *a, **k)
    def _df(self, data=None, *a, **k):
        try: CUR['facts'].append('TABLE (first rows):\n' + data.head(12).to_string()[:1800])
        except Exception: pass
        return _od(self, data, *a, **k)
    dg.DeltaGenerator.metric, dg.DeltaGenerator.plotly_chart, dg.DeltaGenerator.dataframe = _metric, _plot, _df
    dg.DeltaGenerator._qs_patched = True

if not getattr(st, '_qs_patched', False):
    st.plotly_chart = lambda fig, *a, **k: _plot(st._main, fig, *a, **k)
    st.dataframe = lambda data=None, *a, **k: _df(st._main, data, *a, **k)
    st.metric = lambda label, value, *a, **k: _metric(st._main, label, value, *a, **k)
    st._qs_patched = True
ABOUT = {
 0: ("What you are looking at", "Each bar is one production day (06:00 to 06:00) of electricity use, stacked by the two consumption meters: LV12 (orange) and LV11 (blue). The green line is solar <b>generation</b>, which is never added to consumption. Pink bands are stretches with no meter sheet: the register still proves how much energy passed through, so that energy is counted in <b>Bridged gaps</b>, not drawn as bars. <b>Measured consumption</b> comes from real sheet readings; <b>Days with no sheet</b> counts the missing calendar days."),
 1: ("What you are looking at", "How the plant's power draw (kW) behaves through the production day. The heatmap has one row per interval start time and one column per month; colour is the average kW, so hot cells are the heavy periods. Use the meter selector to switch meters. The line chart compares the average kW in each interval on weekdays and weekends. Intervals last between 1 and 6 hours, so this page compares kW (power), not kWh (energy)."),
 2: ("What you are looking at", "Each bar is one month of electricity cost for the two consumption meters, split by tariff band. The prices are editable and are <b>illustrative placeholders</b>, so replace them with your contract. The slider moves a share of normal-band load into the 22:00 to 04:00 off-peak window and shows the saving that would give. Treat it as a ceiling to test: it is only real if the process can run at night."),
 3: ("What you are looking at", "Each reading is compared with the same meter, the same time slot and the same weekday/weekend history, using the median and a robust spread (MAD). The table lists the most unusual readings, with the expected kW next to the actual kW and a z score. The threshold slider sets how strict the test is. Pick a day under Inspect to see it as a red line against the usual range (shaded, 10th to 90th percentile)."),
 4: ("What you are looking at", "How much of the record is real measurement. The table shows, per meter, the days spanned, the share of time covered by real readings, the number of gap days and the energy recovered for them from the register difference. The timeline shows every gap of a day or longer; darker red means more energy was recovered for it. The checks table lists what the pipeline tested and how many rows each check flagged."),
 5: ("What you are looking at", "A forecast of daily energy (kWh) for the chosen horizon. Three models - Holt-Winters, Prophet and gradient boosting - take the same backtest on rolling windows of the most recent continuous segment (gaps up to 3 days filled), and the lowest error wins and builds the forecast. <b>Model error (WAPE)</b> is compared with a simple 'repeat last week' guess: a complex model has to beat that to earn its place. The orange band is the 80% range taken from the winner's real backtest errors."),
}

SYS = ("You analyse ONE page of an energy dashboard for a wood-processing plant (meters LV11 and LV12 are consumption, SOLAR is generation and must never be added to consumption). "
       "You receive images of the page's charts and the numbers shown on the page. Use ONLY what is visible in the images and the numbers given. Every statement must cite a visible number, range or feature. "
       "Do not state causes as facts: say what could explain it and what to check. Do not invent figures, dates, prices or machines. Tariffs on the cost page are illustrative placeholders. "
       "Write for a beginner in plain English, short sentences. Respond with a single JSON object only.")
def _png(fig):
    try:
        return fig.to_image(format='png', width=1000, height=int(fig.layout.height or 380) , scale=1)
    except Exception as e:
        CUR['err'] = repr(e)[:300]; return None

def _client():
    from openai import AzureOpenAI
    return AzureOpenAI(azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'], api_key=os.environ['AZURE_OPENAI_API_KEY'], api_version='2025-03-01-preview')

def _call(content):
    r = _client().chat.completions.create(model=MODEL, messages=[{'role': 'system', 'content': SYS}, {'role': 'user', 'content': content}],
                                          max_completion_tokens=4000, response_format={'type': 'json_object'})
    return json.loads(r.choices[0].message.content)

def begin(i):
    CUR['key'], CUR['facts'], CUR['figs'] = i, [], []
    t, txt = ABOUT[i]
    st.markdown("<div class='card'><b>" + t + ".</b> " + txt + "</div>", unsafe_allow_html=True)

def _esc(x): return html.escape(str(x))
def _insights(i):
    imgs = [p for p in (_png(f) for f in CUR['figs'][:3]) if p]
    facts = '\n'.join(CUR['facts'])[:6000]
    content = [{'type': 'text', 'text': 'Page: ' + ABOUT[i][1].replace('<b>', '').replace('</b>', '') + '\n\nNumbers shown on this page:\n' + facts +
                '\n\nReturn JSON: {"headline": one sentence, "insights": [3 to 5 items {"title": short, "metric": the key number or range as shown, "evidence": 1-2 sentences citing what is visible, "signal": "high"|"watch"|"info"}], "caveat": one sentence on what this page cannot tell}.'}]
    for p in imgs: content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(p).decode()}})
    if not imgs:
        raise RuntimeError('Chart image export is unavailable. Check the Plotly/Kaleido setup before requesting visual insights.')
    out = _call(content); out['_images'] = len(imgs); return out

def _actions(i, ins):
    facts = '\n'.join(CUR['facts'])[:4000]
    txt = ('Numbers shown on this page:\n' + facts + '\n\nInsights already extracted (numbered from 1):\n' +
           '\n'.join(str(n + 1) + '. ' + x.get('title', '') + ' | ' + x.get('metric', '') + ' | ' + x.get('evidence', '') for n, x in enumerate(ins.get('insights', []))) +
           '\n\nReturn JSON: {"actions": [3 or 4 items {"action": one clear step the plant team can take, "based_on": the insight number it follows from, "why": 1 sentence tied to that insight, "check": how to confirm it using only controls on this page (its sliders, selectors, inputs, tables and charts) or with the plant; never mention views, drill-downs or tabs that are not described on the page, "priority": "now"|"next"|"later"}], "note": one sentence}. '
           'Each action must follow from a listed insight. Do not promise savings or numbers that are not in the data above.')
    return _call(txt)

_SIG = {'high': ('#d9534f', 'Important'), 'watch': ('#ff9100', 'Watch'), 'info': ('#27408b', 'Context')}
_PRI = {'now': ('#d9534f', 'Do now'), 'next': ('#ff9100', 'Next'), 'later': ('#27408b', 'Later')}

def _cards(items, kind):
    for a in range(0, len(items), 2):
        cols = st.columns(2)
        for col, x in zip(cols, items[a:a + 2]):
            if kind == 'ins':
                c, lab = _SIG.get(x.get('signal'), _SIG['info'])
                col.markdown("<div style='border-left:5px solid " + c + ";background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)'>"
                             "<span style='font-size:.72rem;font-weight:700;color:" + c + ";text-transform:uppercase;letter-spacing:.06em'>" + lab + "</span>"
                             "<div style='font-weight:700;margin:2px 0'>" + _esc(x.get('title', '')) + "</div>"
                             "<div style='font-size:1.5rem;font-weight:700;color:#0d0908'>" + _esc(x.get('metric', '')) + "</div>"
                             "<div style='font-size:.9rem;color:#444'>" + _esc(x.get('evidence', '')) + "</div></div>", unsafe_allow_html=True)
            else:
                c, lab = _PRI.get(x.get('priority'), _PRI['next'])
                col.markdown("<div style='border-left:5px solid " + c + ";background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)'>"
                             "<span style='font-size:.72rem;font-weight:700;color:" + c + ";text-transform:uppercase;letter-spacing:.06em'>" + lab + " &middot; from insight " + _esc(x.get('based_on', '')) + "</span>"
                             "<div style='font-weight:700;margin:2px 0'>" + _esc(x.get('action', '')) + "</div>"
                             "<div style='font-size:.9rem;color:#444'>" + _esc(x.get('why', '')) + "</div>"
                             "<div style='font-size:.85rem;color:#666;margin-top:6px'><b>How to check:</b> " + _esc(x.get('check', '')) + "</div></div>", unsafe_allow_html=True)
def panel(i):
    ss = st.session_state; k1, k2 = 'ins_%d' % i, 'act_%d' % i
    st.markdown("<hr style='margin:1.2rem 0 .6rem'><b>AI analysis of this page</b> <span style='color:#666'>(" + MODEL + " reads the charts and numbers above)</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button('Extract insights with AI', key='b1_%d' % i, use_container_width=True, type='primary'):
        with st.spinner('Reading the charts on this page...'):
            try: ss[k1] = _insights(i); ss.pop(k2, None)
            except Exception as e: st.error('Could not extract insights: ' + str(e)[:200])
    if c2.button('Recommended actions', key='b2_%d' % i, use_container_width=True, disabled=k1 not in ss):
        with st.spinner('Turning the insights into actions...'):
            try: ss[k2] = _actions(i, ss[k1])
            except Exception as e: st.error('Could not build actions: ' + str(e)[:200])
    if k1 in ss:
        r = ss[k1]
        st.markdown("<div class='card'><b>" + _esc(r.get('headline', '')) + "</b></div>", unsafe_allow_html=True)
        _cards(r.get('insights', []), 'ins')
        st.caption(_esc(r.get('caveat', '')) + ' Based on %d chart image(s) plus the numbers on this page.' % r.get('_images', 0) + (' [' + CUR.get('err','') + ']' if not r.get('_images') else ''))
    if k2 in ss:
        st.markdown('**Recommended actions**')
        _cards(ss[k2].get('actions', []), 'act')
        if ss[k2].get('note'): st.caption(_esc(ss[k2]['note']))
