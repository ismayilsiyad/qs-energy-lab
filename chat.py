import os, json
import pandas as pd, numpy as np
import streamlit as st


# ---- Vetted queries: the model may only choose one of these functions and one of these arguments.
# No model-written code is ever executed. Every function is fixed pandas code on read-only copies.
METERS = ['LV11', 'LV12', 'SOLAR']
CONS = ['LV11', 'LV12']
NIGHT_SLOTS = ['20:00', '22:00', '04:00']

def _slot(s): return str(s)[:5]
def _fmt(df): return df.to_string(index=False)

def q_meter_share(env, meter=None):
    iv = env['iv']; m = iv[(iv.quality == 'measured') & iv.meter.isin(CONS)]
    t = m.groupby('meter', as_index=False)['kwh'].sum()
    t['share_pct'] = (t.kwh / t.kwh.sum() * 100).round(2)
    return 'Measured consumption by meter (LV11+LV12 only, SOLAR is generation and excluded, measured intervals only):\n' + _fmt(t.sort_values('kwh', ascending=False).assign(kwh=lambda d: d.kwh.round(0)))

def q_slot_profile(env, meter='LV12'):
    iv = env['iv']; m = iv[(iv.quality == 'measured') & (iv.meter == meter)].copy()
    m['slot_s'] = m.slot.map(_slot); m['day_type'] = m.weekend.map(lambda w: 'weekend' if w else 'weekday')
    t = m.groupby(['slot_s', 'day_type']).kw.mean().unstack().round(1)
    best = {c: t[c].idxmax() for c in t.columns}
    return 'Average kW by interval start (' + meter + ', measured intervals):\n' + t.to_string() + '\nHighest slot by day type: ' + json.dumps(best)

def q_gap_summary(env, meter=None):
    g = env['gaps']; c = g[g.meter.isin(CONS)]
    by = c.groupby(['gap_start', 'gap_end'], as_index=False)['energy_kwh'].sum().sort_values('energy_kwh', ascending=False)
    s = g[g.meter == 'SOLAR'].energy_kwh.sum()
    top = by.head(5).copy(); top['gap_start'] = top.gap_start.astype(str); top['gap_end'] = top.gap_end.astype(str)
    return ('Bridged (no sheet) consumption LV11+LV12: %.0f kWh across %d gap periods. Bridged SOLAR generation, reported separately: %.0f kWh.\nBiggest gaps by consumption energy:\n' % (c.energy_kwh.sum(), len(by), s)) + _fmt(top.round(0))

def q_best_solar_month(env, meter=None):
    iv = env['iv']; m = iv[(iv.quality == 'measured') & (iv.meter == 'SOLAR')]
    m = m.assign(mon=m.month.astype(str)); t = m.groupby('mon', as_index=False)['kwh'].sum().sort_values('kwh', ascending=False).rename(columns={'mon': 'month'})
    return 'Measured SOLAR generation by month, highest first:\n' + _fmt(t.head(5).assign(kwh=lambda d: d.kwh.round(0)))

def q_shift_compare(env, meter=None):
    iv = env['iv']; m = iv[(iv.quality == 'measured') & iv.meter.isin(CONS)].copy()
    m['shift'] = m.slot.map(lambda s: 'night (20:00-06:00)' if _slot(s) in NIGHT_SLOTS else 'day (06:00-20:00)')
    t = m.groupby('shift').agg(kwh=('kwh', 'sum'), hours=('hours', 'sum')).reset_index()
    t['avg_kw'] = (t.kwh / t.hours).round(1)
    return 'Consumption intensity: average kW PER METER (LV11 and LV12 pooled, measured intervals, energy divided by hours). The plant total is the sum of both meters, about double these figures:\n' + _fmt(t.round(1))

def q_month_totals(env, meter=None):
    iv = env['iv']; m = iv[(iv.quality == 'measured') & iv.meter.isin(CONS)]
    m = m.assign(mon=m.month.astype(str), day=m.pday)
    t = m.groupby('mon').agg(kwh=('kwh', 'sum'), measured_days=('day', 'nunique')).reset_index().rename(columns={'mon': 'month'}).sort_values('kwh', ascending=False)
    return 'Measured consumption by month (LV11+LV12), highest first. Months with few measured days are partial:\n' + _fmt(t.head(6).assign(kwh=lambda d: d.kwh.round(0)))

QUERIES = {
    'meter_share': (q_meter_share, 'Energy per consumption meter and its share of consumption'),
    'slot_profile': (q_slot_profile, 'Average kW per interval start, weekday vs weekend, for one meter'),
    'gap_summary': (q_gap_summary, 'Energy bridged for periods with no sheet, and the biggest gaps'),
    'best_solar_month': (q_best_solar_month, 'Months ranked by measured solar generation'),
    'shift_compare': (q_shift_compare, 'Night shift vs day shift average kW for consumption'),
    'month_totals': (q_month_totals, 'Months ranked by measured consumption'),
}

def run_query(name, args, env):
    if name not in QUERIES: return 'REJECTED: unknown query. Allowed: ' + ', '.join(QUERIES)
    kw = {}
    if isinstance(args, dict) and args.get('meter') in METERS: kw['meter'] = args['meter']
    try: return QUERIES[name][0](env, **kw)[:3500]
    except Exception as e: return f'ERROR: {type(e).__name__}: {e}'

FACTS = """You are the data analyst inside the Quanskill Energy Lab, a teaching dashboard for a wood-particle processing plant (Vietnam). You answer ONLY from the data and facts below.
DATA SEMANTICS (verified):
- 3 electricity meters: LV11 (chipper cabinet) and LV12 (chip-processing area) are CONSUMPTION. SOLAR is a PV cabinet = GENERATION (never add it to consumption).
- Source sheets are cumulative meter registers (millions of kWh). Energy of an interval = register end - register start. Registers have 10 kWh resolution.
- Interval duration is stored in hours; compare kW, not kWh, across different durations. A production day starts at 06:00 ('pday').
- Tariff bands are read from the loaded table; do not assume every band is present. No tariff prices are in the data; any VND cost is an illustrative assumption and must be labelled so.
- 'quality': 'measured' rows are real sheet readings; rows in the gaps table cover all three meters: LV11 and LV12 are consumption, SOLAR is generation. When you give a gap or bridged total, ALWAYS state its scope: report consumption (LV11+LV12) and SOLAR separately and never add solar generation to consumption. Rows in the gaps table are energy bridged over missing days (no sheet exists, energy is proven by register difference but its time profile is unknown).
TOOL: call query(name, meter) to look up a number. Allowed names: meter_share, slot_profile (meter LV11, LV12 or SOLAR), gap_summary, best_solar_month, shift_compare, month_totals. You cannot run code, and you cannot compute anything that these queries do not return. If no query fits the question (for example a forecast or the future bill, causes, prices, machines), say plainly that this chat cannot answer it and point to the Forecasting, Bill estimator or Cost analysis tab instead of guessing. Always answer in English.
RULES: Every number in your answer must come from a tool result in this conversation. Never invent figures. If the data cannot answer (e.g. causes, machine names, prices, other plants, future values beyond the forecast tab), say plainly that the data cannot tell, and say what extra data would. Mention caveats that change the meaning (gaps, bridged energy, resolution). Use kWh/MWh/GWh with units. Be concise: answer first, then one line of 'why/so what'. Answer in English."""

PROXY_URL = 'https://qs-energy-proxy.circawell.workers.dev'  # course AI endpoint (class proxy)
CLASS_PASSCODE = 'QSEnergy-CQyw8kf8'

def client():
    from openai import AzureOpenAI
    ep = os.environ.get('AZURE_OPENAI_ENDPOINT') or PROXY_URL
    k = os.environ.get('AZURE_OPENAI_API_KEY') or CLASS_PASSCODE
    return AzureOpenAI(api_key=k, api_version='2025-03-01-preview', azure_endpoint=ep)

TOOLS = [{'type': 'function', 'function': {'name': 'query', 'description': 'Run one vetted query. meter_share: which consumption meter uses most and its share. slot_profile: average kW by interval start (hour slot), weekday vs weekend, for the chosen meter. gap_summary: energy with no sheet and the biggest gap. best_solar_month: best months of solar generation. shift_compare: night vs day shift. month_totals: highest consumption month.',
          'parameters': {'type': 'object', 'properties': {'name': {'type': 'string', 'enum': list(QUERIES)}, 'meter': {'type': 'string', 'enum': METERS}}, 'required': ['name']}}}]

EXAMPLES = ['Which meter uses the most energy, and what share is that of consumption?',
            'Which hour slot has the highest average kW on weekdays vs weekends for LV12?',
            'How much consumption energy (LV11 + LV12) do we not have a sheet for, and which was the biggest gap?',
            'How much did solar generate in its best month?',
            'Is the night shift (20:00-06:00) more or less intensive than the day shift?',
            'Which month had the highest total consumption, and how much was it?',
            'What will the electricity bill be next month?']

def dataset_context(env):
    iv = env['iv']
    return ('Loaded table context: meters=' + ', '.join(sorted(iv.meter.dropna().unique()))
            + '; tariff labels=' + ', '.join(sorted(iv.tariff.dropna().unique()))
            + '; date range=' + str(iv.start.min()) + ' to ' + str(iv.end.max())
            + '. Numerical answers still require a checked query result.')

def ask(question, env, history):
    c = client()
    if c is None: return 'The chat is not configured (no Azure OpenAI credentials in the environment).', []
    dep = os.environ.get('QS_CHAT_MODEL', 'gpt-5.4')
    msgs = [{'role': 'system', 'content': FACTS + '\n' + dataset_context(env)}] + history[-6:] + [{'role': 'user', 'content': question}]
    steps = []
    for _ in range(5):
        r = c.chat.completions.create(model=dep, messages=msgs, tools=TOOLS, max_completion_tokens=4000)
        m = r.choices[0].message
        if not m.tool_calls:
            return m.content, steps
        msgs.append({'role': 'assistant', 'content': m.content, 'tool_calls': [t.model_dump() for t in m.tool_calls]})
        for t in m.tool_calls:
            try: a = json.loads(t.function.arguments)
            except Exception: a = {}
            name = a.get('name', '') if isinstance(a, dict) else ''
            out = run_query(name, a, env)
            steps.append((name + '(' + json.dumps({k: v for k, v in a.items() if k != 'name'}) + ')', out))
            msgs.append({'role': 'tool', 'tool_call_id': t.id, 'content': out})
    return 'I could not settle this within the allowed steps. Try a narrower question.', steps

def render(I, Gp, daily):
    st.markdown("<div class='card'><b>Ask the data.</b> Questions are answered by an LLM that chooses from a fixed set of checked queries on the corrected gold tables and answers only from the result. It cannot run code. Open <i>Show the working</i> under any answer to see which query ran and its output. It says so when the data cannot answer.</div>", unsafe_allow_html=True)
    env = dict(iv=I.copy(), gaps=Gp.copy(), daily=daily.copy())
    if 'chat' not in st.session_state: st.session_state.chat = []
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES):
        if cols[i % 2].button(q, key=f'ex{i}', use_container_width=True):
            st.session_state.pending = q
    q = st.chat_input('Ask about consumption, load, gaps, solar, anomalies...') or st.session_state.pop('pending', None)
    hist = [{'role': m['role'], 'content': m['content']} for m in st.session_state.chat]
    if q:
        with st.spinner('Analysing the data...'):
            try: a, steps = ask(q, env, hist)
            except Exception as e: a, steps = f'The language model call failed ({type(e).__name__}). Try again.', []
        st.session_state.chat += [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': a, 'steps': steps}]
    for m in st.session_state.chat:
        with st.chat_message(m['role']):
            st.markdown(m['content'])
            if m.get('steps'):
                with st.expander('Show the working'):
                    for code, out in m['steps']:
                        st.code(code, language='text'); st.text(out)
