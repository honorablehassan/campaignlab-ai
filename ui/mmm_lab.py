from __future__ import annotations

from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.mmm import geometric_adstock, media_response, mmm_readiness, fit_mmm, optimize_budget
from analytics.data_builder import understand_source, build_mmm_dataset
from engines.decision_kernel import decision_from_mmm
from ui.brand import brand_mark
from ui.decision_record import render_decision_memory, render_decision_record
from state import prepare_mmm_handoff
from core.uploads import load_tabular_upload


def _money(x, symbol=""): return f"{symbol}{x:,.0f}"

def _dataset_fingerprint(df: pd.DataFrame, source_name: str) -> str:
    row_hash = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    schema = "|".join(f"{c}:{df[c].dtype}" for c in df.columns).encode("utf-8")
    return hashlib.sha256(source_name.encode("utf-8") + schema + row_hash).hexdigest()

def _money_input(label: str, value: float, key: str) -> float:
    raw=st.text_input(label,value=f"{value:,.0f}",key=key)
    cleaned=raw.replace("$","").replace(",","").replace(" ","").strip()
    try:
        out=float(cleaned)
        if out<=0: raise ValueError
        return out
    except ValueError:
        st.caption(f"Enter a positive amount, for example {value:,.0f}.")
        return -1.0



def _infer_period_name(df: pd.DataFrame, date_col: str, builder_report=None) -> str:
    if builder_report and builder_report.get("grain") in {"day", "week", "month"}:
        return {"day": "day", "week": "week", "month": "month"}[builder_report["grain"]]
    try:
        dt = pd.to_datetime(df[date_col], errors="coerce").dropna().sort_values().drop_duplicates()
        if len(dt) >= 3:
            days = float(dt.diff().dropna().dt.total_seconds().median() / 86400)
            if days <= 2.0: return "day"
            if 5.0 <= days <= 10.0: return "week"
            if 24.0 <= days <= 35.0: return "month"
    except Exception:
        pass
    return "period"

def _load(uploaded):
    return load_tabular_upload(uploaded)


def _render_source_understanding(df: pd.DataFrame, name: str):
    u = understand_source(df, name)
    st.markdown(f'<div class="cl-data-understand"><span>CAMPAIGNLAB FOUND YOUR EVIDENCE</span><b>{u["source_label"]}</b><p>{name} · {u["rows"]:,} rows · {u["columns"]:,} columns · {u["confidence"].title()} confidence</p></div>', unsafe_allow_html=True)
    mapped = u.get("evidence") or []
    if mapped:
        chips=[]
        for item in mapped[:8]:
            chips.append(f'<div class="cl-map-chip"><small>{item["role"].replace("_"," ").upper()}</small><b>{item["column"]}</b></div>')
        st.markdown('<div class="cl-map-grid">'+''.join(chips)+'</div>', unsafe_allow_html=True)
    return u


def _load_multi_source(files):
    sources=[]
    understandings=[]
    for uploaded in files:
        df=_load(uploaded)
        u=_render_source_understanding(df, uploaded.name)
        sources.append({"name":uploaded.name.rsplit('.',1)[0],"df":df,"kind":u["source_kind"]})
        understandings.append((uploaded.name,u))
    outcome_candidates=[]
    for src,(filename,u) in zip(sources,understandings):
        mp=u.get("mapping") or {}
        if "revenue" in mp and "spend" not in mp:
            outcome_candidates.append(src["name"])
    outcome_source=None
    if len(outcome_candidates)==1:
        outcome_source=outcome_candidates[0]
        st.caption(f"CampaignLab found one likely business outcome source: {outcome_source}.")
    elif len(outcome_candidates)>1:
        outcome_source=st.selectbox("Which file contains the business result you want CampaignLab to explain?", outcome_candidates, help="This choice changes the target of the model, so CampaignLab asks instead of guessing.")
    grain=st.segmented_control("Time level for the model", ["week","month"], default="week", key="mmm_builder_grain", help="CampaignLab needs all sources on the same time scale. Weekly is usually a strong starting point when enough history exists.")
    built,report=build_mmm_dataset(sources,grain=grain or "week",outcome_source=outcome_source)
    if report.get("blockers"):
        st.markdown('<div class="cl-data-question"><span>CAMPAIGNLAB WILL NOT GUESS</span><b>Resolve these before the model sees the data.</b></div>', unsafe_allow_html=True)
        for blocker in report["blockers"]:
            st.error(blocker)
        return None,report
    if report.get("warnings"):
        for warning in report["warnings"][:6]:
            st.warning(warning)
    st.markdown(f'<div class="cl-mmm-loaded"><span>YOUR EVIDENCE IS READY</span><b>{len(built):,} aligned {report["grain"]} periods</b><p>{len(report.get("media_columns") or []):,} media channel(s) · 1 resolved business outcome · {len(report.get("control_columns") or []):,} demand control(s). Unknown media periods remain unknown unless you explicitly resolve them.</p></div>',unsafe_allow_html=True)
    return built,report


def _load_builder_demo():
    root=Path(__file__).resolve().parents[1]/"examples"/"data_builder_sources"
    files=["meta_daily.csv","google_ads_daily.csv","youtube_daily.csv","tv_daily.csv","commerce_weekly.csv"]
    sources=[]
    for filename in files:
        path=root/filename
        df=pd.read_csv(path)
        u=_render_source_understanding(df, filename)
        sources.append({"name":filename.rsplit('.',1)[0],"df":df,"kind":u["source_kind"]})
    built,report=build_mmm_dataset(sources,grain="week",outcome_source="commerce_weekly")
    if report.get("blockers"):
        for blocker in report["blockers"]: st.error(blocker)
        return None,report
    for warning in report.get("warnings") or []: st.warning(warning)
    st.markdown(f'<div class="cl-mmm-loaded"><span>YOUR EVIDENCE IS READY</span><b>{len(built):,} aligned weekly periods</b><p>{len(report.get("media_columns") or []):,} media channel(s) · 1 resolved business outcome · {len(report.get("control_columns") or []):,} demand control(s) · built from 5 separate exports.</p></div>',unsafe_allow_html=True)
    return built,report


def _step(title: str, number: str, copy: str):
    st.markdown(f'<div class="cl-mmm-step"><span>{number}</span><div><b>{title}</b><p>{copy}</p></div></div>',unsafe_allow_html=True)


def _readiness_card(readiness):
    r=readiness.report
    cls='good' if r.status=='ready' else ('warn' if r.status=='caution' else 'bad')
    headline="Strong starting point" if r.status=='ready' else ("Usable, with caveats" if r.status=='caution' else "Not defensible yet")
    st.markdown(f'<div class="cl-mmm-score {cls}"><div><span>MMM READINESS</span><b>{r.score}/100</b></div><h4>{headline}</h4><p>{"The structure is strong enough for a beta model run. CampaignLab will still keep the causal claim conservative." if r.status=="ready" else "CampaignLab can proceed, but the warnings below should lower confidence in attribution and allocation." if r.status=="caution" else "Fix the blockers below before CampaignLab fits a model. A polished output is not useful if the evidence cannot support it."}</p></div>',unsafe_allow_html=True)
    cols=st.columns(2)
    for i,c in enumerate(r.checks):
        icon={'pass':'✓','warn':'!','fail':'×'}[c.status]
        with cols[i%2]: st.markdown(f'<div class="cl-check {c.status}"><b>{icon} {c.label}</b><span>{c.message}</span></div>',unsafe_allow_html=True)


def _response_curve(channel: str, info: dict, current: float, recommended: float, period_name: str = "period"):
    top=max(current,recommended,1.0)*1.8
    spend=np.linspace(0,top,80)
    alpha=float(info['adstock_alpha']); beta=float(info['coefficient'])
    steady=spend/max(1-alpha,1e-6)
    response=beta*media_response(steady,info)
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=spend,y=response,name='Modeled response',mode='lines',hovertemplate='Spend: $%{x:,.0f}<br>Modeled response: %{y:,.1f}<extra></extra>'))
    for x,name in [(current,'Current'),(recommended,'Scenario')]:
        y=beta*float(media_response(np.asarray([x/max(1-alpha,1e-6)]),info)[0])
        fig.add_trace(go.Scatter(x=[x],y=[y],name=name,mode='markers',marker={'size':10},hovertemplate=f'{name}<br>Spend: $%{{x:,.0f}}<br>Modeled response: %{{y:,.1f}}<extra></extra>'))
    fig.update_layout(title=channel.replace('_',' ').title(),height=310,margin=dict(l=10,r=10,t=48,b=10),legend_title_text='',xaxis_title=f'Spend per {period_name}',yaxis_title='Modeled media response')
    return fig


def render_mmm_lab():
    st.markdown(f'''<section class="cl-mmm-hero">
      <div class="cl-mmm-special">LAB SPECIAL · BETA</div>
      <div class="cl-mmm-hero-row">{brand_mark("lg")}<div><h1>Marketing Mix Model</h1><p>See what appears to be driving performance, where channels may be running out of headroom, and where the next marketing dollar has the strongest modeled upside.</p></div></div>
      <div class="cl-mmm-trustline">Built to make the strongest claim the evidence can support — and no stronger.</div>
    </section>''',unsafe_allow_html=True)

    st.markdown('''<div class="cl-mmm-philosophy">
      <div><span>01 · BRING THE MESS</span><b>You do not need an MMM-ready table.</b><p>Bring the exports you actually have. CampaignLab works out what looks like media spend, business outcomes, and other demand drivers, then tells you what still needs your judgment.</p></div>
      <div><span>02 · EARN THE CLAIM</span><b>Correlation is not incrementality.</b><p>CampaignLab checks whether the history can support the question, accounts for delayed media effects and diminishing returns, tests the model on later unseen periods, and keeps the claim conservative.</p></div>
      <div><span>03 · MAKE IT ACTIONABLE</span><b>Contribution is not the final answer.</b><p>See what the model attributes to each channel, how the response changes with spend, and what a different budget mix could look like. Then get the call, confidence, and best next check.</p></div>
    </div>
    <div class="cl-mmm-principle"><b>Python calculates.</b> CampaignLab challenges the evidence. <b>You get the decision.</b></div>
    <div class="cl-mmm-rail"><span>01 Data</span><span>02 Readiness</span><span>03 Model</span><span>04 Mix</span><span>05 Budget</span><span>06 Decision</span></div>''',unsafe_allow_html=True)

    _step("Bring your marketing evidence", "01", "Start with what you have. CampaignLab handles the routine shaping and alignment; you only confirm choices that can materially change the answer.")
    source_mode=st.segmented_control("What do you have?", ["One analysis-ready table","Separate exports"], default="One analysis-ready table", key="mmm_source_mode")
    df=None; source=''; builder_report=None; source_understanding=None
    if source_mode=="One analysis-ready table":
        c1,c2=st.columns(2)
        with c1:
            st.markdown('''<div class="cl-demo-card mmm">
              <span>KNOWN-ANSWER MMM DEMO</span><h3>Where could the next dollar work harder?</h3>
              <p>Three and a half years of weekly revenue, four media channels, promotions, holidays, pricing, carryover and diminishing returns.</p>
              <small>Explore readiness, validation, contribution, response curves and a constrained allocation scenario.</small>
            </div>''', unsafe_allow_html=True)
            if st.button("🧪 Explore with the MMM demo",width="stretch",key="load_mmm_demo"):
                st.session_state['mmm_demo']=True
                st.session_state.pop('mmm_result',None)
        with c2:
            st.markdown('''<div class="cl-demo-card upload">
              <span>YOUR ANALYSIS-READY TABLE</span><h3>Bring the model-ready history you have.</h3>
              <p>Upload a weekly or monthly table containing an outcome, media investment and the demand controls that matter.</p>
              <small>CampaignLab inspects the structure before it allows the model to make an allocation claim.</small>
            </div>''', unsafe_allow_html=True)
            uploaded=st.file_uploader("Upload CSV / Excel",type=['csv','xlsx'],key='mmm_upload',label_visibility='collapsed')
        if uploaded:
            st.session_state['mmm_demo']=False
            try:
                df=_load(uploaded); source=uploaded.name
                source_understanding=_render_source_understanding(df, source)
            except Exception as exc: st.error(str(exc)); return
        elif st.session_state.get('mmm_demo'):
            p=Path(__file__).resolve().parents[1]/'examples'/'demo_mmm_weekly.csv'; df=pd.read_csv(p); source=p.name
            source_understanding=_render_source_understanding(df, source)
    else:
        d1,d2=st.columns(2)
        with d1:
            st.markdown('''<div class="cl-demo-card mmm">
              <span>DATA BUILDER DEMO</span><h3>See separate exports become one model table.</h3>
              <p>CampaignLab aligns synthetic platform and commerce files, preserves unknown periods and asks only when a mapping changes the answer.</p>
              <small>Use this to inspect the ingestion workflow before bringing your own exports.</small>
            </div>''', unsafe_allow_html=True)
            if st.button("✦ See CampaignLab build the dataset",width="stretch",key="mmm_builder_demo"):
                st.session_state['mmm_builder_demo_on']=True
                st.session_state.pop('mmm_result',None)
        with d2:
            st.markdown('''<div class="cl-demo-card upload">
              <span>YOUR PLATFORM EXPORTS</span><h3>Bring the files you actually receive.</h3>
              <p>Upload media-platform and sales files together. CampaignLab maps, aggregates and aligns them before modeling.</p>
              <small>Raw platform exports remain a guarded workflow; review every material mapping.</small>
            </div>''', unsafe_allow_html=True)
            uploads=st.file_uploader("Bring the exports you actually have",type=['csv','xlsx'],accept_multiple_files=True,key='mmm_multi_upload',label_visibility='collapsed',help="Examples: Meta Ads, Google Ads, YouTube, TV and a sales/commerce file. CampaignLab maps, aggregates and aligns them before MMM.")
        if uploads:
            st.session_state['mmm_builder_demo_on']=False
            try:
                df,builder_report=_load_multi_source(uploads)
                source="CampaignLab-built MMM dataset"
            except Exception as exc:
                st.error(f"CampaignLab could not build these sources safely: {exc}"); return
        elif st.session_state.get('mmm_builder_demo_on'):
            try:
                df,builder_report=_load_builder_demo()
                source="CampaignLab Data Builder demo"
            except Exception as exc:
                st.error(f"CampaignLab could not build the demo sources safely: {exc}"); return

    if df is None:
        demo_path=Path(__file__).resolve().parents[1]/'examples'/'demo_mmm_weekly.csv'
        st.markdown('<div class="cl-mmm-empty"><b>Bring the marketing evidence you actually have.</b><p>Use one analysis-ready table, or give CampaignLab separate platform and sales exports. It will infer the obvious, preserve unknowns, and ask only when a choice can change the answer.</p></div>',unsafe_allow_html=True)
        st.download_button("Download the MMM sample dataset",data=demo_path.read_bytes(),file_name='demo_mmm_weekly.csv',mime='text/csv',width="stretch",key='download_mmm_demo_empty')
        return

    st.markdown(f'<div class="cl-mmm-loaded"><span>DATA LOADED</span><b>{source}</b><p>{len(df):,} rows · {len(df.columns):,} columns</p></div>',unsafe_allow_html=True)
    if source=='demo_mmm_weekly.csv':
        st.download_button("Download this sample dataset",data=df.to_csv(index=False).encode('utf-8'),file_name='demo_mmm_weekly.csv',mime='text/csv',key='download_mmm_demo_loaded')

    numeric=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    mapping=(source_understanding or {}).get('mapping', {})
    likely_dates=[mapping.get('date')] if mapping.get('date') in df.columns else []
    likely_dates += [c for c in df.columns if c not in likely_dates and ('date' in c.lower() or 'week' in c.lower() or 'month' in c.lower() or c.lower()=='period')]
    a,b=st.columns(2)
    with a:
        date_col=st.selectbox("When did it happen?",df.columns,index=df.columns.get_loc(likely_dates[0]) if likely_dates else 0,help="The regular time key CampaignLab will use to align spend and outcomes.")
    mapped_outcome=mapping.get('revenue')
    outcome_default=mapped_outcome if mapped_outcome in numeric else ('revenue' if 'revenue' in df.columns else (numeric[0] if numeric else df.columns[0]))
    with b:
        outcome_col=st.selectbox("What outcome should marketing explain?",numeric,index=numeric.index(outcome_default) if outcome_default in numeric else 0,help="Usually revenue, sales, conversions or another business outcome. CampaignLab preselects a likely field when it can identify one safely.")
    spend_defaults=(builder_report.get('media_columns',[]) if builder_report else [c for c in numeric if any(k in c.lower() for k in ['spend','media','search','meta','youtube','tv','google']) and c!=outcome_col])
    mapped_spend=mapping.get('spend')
    if mapped_spend in numeric and mapped_spend != outcome_col and mapped_spend not in spend_defaults:
        spend_defaults=[mapped_spend,*spend_defaults]
    media_cols=st.multiselect("Which marketing investments should be in the mix?",[c for c in numeric if c!=outcome_col],default=spend_defaults[:6],help="Choose the spend fields CampaignLab should treat as marketing investment. The raw column names stay visible so analysts can verify the mapping.")
    control_candidates=[c for c in numeric if c not in set(media_cols+[outcome_col])]
    control_defaults=[c for c in control_candidates if any(k in c.lower() for k in ['promo','price','holiday','distribution','competitor'])]
    control_cols=st.multiselect("What else could have moved demand?",control_candidates,default=control_defaults,help="Promotions, pricing, holidays, distribution or other drivers help keep media from stealing credit for demand it did not create.")
    experiment_calibrations=[]
    with st.expander("Optional · I have an incrementality result for one channel", expanded=False):
        use_calibration=st.checkbox(
            "Calibrate one channel with experimental evidence",
            key="mmm_use_experiment_calibration",
            help="Use only a credible experiment whose outcome and time unit match this MMM. CampaignLab will preserve the experiment's uncertainty and scope.",
        )
        if use_calibration and media_cols:
            calibrated_channel=st.selectbox("Which channel was tested?",media_cols,key="mmm_calibration_channel")
            typical=float(pd.to_numeric(df[calibrated_channel],errors="coerce").dropna().median())
            cc1,cc2=st.columns(2)
            with cc1:
                baseline_spend=st.number_input("Baseline spend per modeled period",min_value=0.0,value=max(0.0,typical),key="mmm_calibration_baseline")
                incremental_outcome=st.number_input("Estimated incremental outcome per period",value=0.0,key="mmm_calibration_effect")
            with cc2:
                treatment_spend=st.number_input("Treatment spend per modeled period",min_value=0.0,value=max(0.0,typical*1.2),key="mmm_calibration_treatment")
                experiment_se=st.number_input("Standard error of that incremental outcome",min_value=0.000001,value=1.0,key="mmm_calibration_se")
            experiment_calibrations=[{
                "channel":calibrated_channel,"baseline_spend":float(baseline_spend),
                "treatment_spend":float(treatment_spend),"incremental_outcome":float(incremental_outcome),
                "standard_error":float(experiment_se),
            }]
            st.caption("Calibration applies only to this channel and stated spend contrast. It does not make the remaining MMM causal.")
    dataset_fingerprint=_dataset_fingerprint(df, source)
    period_name=_infer_period_name(df, date_col, builder_report)
    calibration_signature=tuple(tuple(sorted(item.items())) for item in experiment_calibrations)
    model_signature=(dataset_fingerprint,date_col,outcome_col,tuple(media_cols),tuple(control_cols),calibration_signature)
    if not media_cols:
        st.warning("Select at least one media spend column so CampaignLab has a marketing mix to evaluate."); return

    _step("Can this data support an MMM?", "02", "Before fitting anything, CampaignLab checks whether the history contains enough information to separate media from the rest of demand.")
    readiness=mmm_readiness(df,date_col,outcome_col,media_cols,control_cols)
    _readiness_card(readiness)
    if readiness.report.status=='blocked': return

    if st.button("Run Marketing Mix Model",type='primary',width="stretch",key='run_mmm'):
        with st.spinner("Modeling carryover and saturation, separating baseline demand, and validating on unseen history…"):
            try:
                st.session_state['mmm_result']=fit_mmm(df,date_col,outcome_col,media_cols,control_cols,experiment_calibrations=experiment_calibrations)
                st.session_state['mmm_result_signature']=model_signature
            except Exception as exc: st.error(str(exc)); return
    result=st.session_state.get('mmm_result')
    if not result:
        st.caption("Nothing is attributed until you run the model. Readiness tells us whether the analysis is worth trusting; it does not manufacture a result.")
        return
    if st.session_state.get('mmm_result_signature') != model_signature:
        st.info("The dataset or model mapping changed after the last run. Run Marketing Mix Model again before CampaignLab shows the old attribution or budget recommendation.")
        return

    _step("Does the model survive contact with reality?", "03", "CampaignLab checks unseen historical periods before asking you to trust contribution or budget recommendations.")
    wape=result['model']['holdout_wape']; r2=result['model']['r2']; strength=result['model']['evidence_strength']
    media_improvement=result['model'].get('media_holdout_improvement',0.0)
    if strength == "Limited":
        interpretation = "The full model may track history, but media does not add enough out-of-sample value over baseline demand and controls to support a confident allocation call."
    elif wape <= .12:
        interpretation = "The model reproduces unseen history and media adds useful signal beyond baseline demand and controls. Attribution remains observational."
    else:
        interpretation = "The model has meaningful holdout error. Treat channel attribution and reallocation as directional rather than precise."
    st.markdown(f'<div class="cl-mmm-interpret"><span>WHAT CAMPAIGNLAB THINKS</span><b>{strength} evidence</b><p>{interpretation}</p></div>',unsafe_allow_html=True)
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Evidence strength",strength,help="A conservative diagnostic label, not a causal probability.")
    m2.metric("Unseen-period error",f"{wape:.1%}",help="WAPE on later periods the model did not fit on. Lower is better.")
    m3.metric("Media signal added",f"{media_improvement:+.1%}",help="How much adding media improves error on unseen periods versus baseline demand and controls. If media adds little or nothing, CampaignLab lowers evidence strength even when overall fit looks good.")
    m4.metric("Historical fit",f"{r2:.2f}",help="R²: how much historical variation the fitted model explains. A high value does not prove that media caused the outcome.")
    st.caption(f"Validated on {result['holdout_periods']:,} unseen period(s). CampaignLab also benchmarks the media model against baseline demand + controls so a good forecast cannot masquerade as evidence that media drove it.")
    st.markdown(f'<div class="cl-causal-note"><b>CAUSAL GUARDRAIL</b><p>{result["warning"]}</p></div>',unsafe_allow_html=True)

    series=pd.DataFrame(result['series']); series[date_col]=pd.to_datetime(series[date_col])
    fig=go.Figure(); fig.add_trace(go.Scatter(x=series[date_col],y=series['actual'],name='Actual')); fig.add_trace(go.Scatter(x=series[date_col],y=series['predicted'],name='Modeled')); fig.add_trace(go.Scatter(x=series[date_col],y=series['baseline'],name='Modeled baseline',line={'dash':'dot'}))
    fig.update_layout(title='Did the model track what actually happened?',hovermode='x unified',legend_title_text='',height=420,margin=dict(l=10,r=10,t=55,b=10))
    st.plotly_chart(fig,width="stretch",config={'displaylogo':False,'responsive':True})
    st.caption("Actual vs modeled shows fit. The dotted baseline is the model's non-media component under this specification — not a directly observed no-marketing counterfactual.")

    _step("What does the model say about the mix?", "04", "Separate historical contribution from future opportunity. The biggest past contributor is not automatically where the next dollar belongs.")
    rows=[]
    for c,v in result['channels'].items(): rows.append({'Channel':c,'Modeled contribution':v['total'],'Lower conditional bound':v.get('total_ci_low'),'Upper conditional bound':v.get('total_ci_high'),'Media share':v['share_of_modeled_media'],'Carryover α':v['adstock_alpha'],'Response family':v.get('saturation_family','exponential')})
    contrib=pd.DataFrame(rows).sort_values('Modeled contribution',ascending=False)
    leader=contrib.iloc[0]
    st.markdown(f'<div class="cl-mmm-insight"><span>WHAT CAMPAIGNLAB SEES</span><b>{str(leader["Channel"]).replace("_"," ").title()} is the largest modeled historical media contributor.</b><p>It represents {leader["Media share"]:.1%} of modeled media contribution in this specification. That is a historical attribution statement, not automatically a recommendation to spend more there.</p></div>',unsafe_allow_html=True)
    fig2=go.Figure(go.Bar(x=contrib['Modeled contribution'],y=contrib['Channel'],orientation='h',customdata=contrib[['Media share']],hovertemplate='%{y}<br>Modeled contribution: %{x:,.0f}<br>Share of modeled media: %{customdata[0]:.1%}<extra></extra>'))
    fig2.update_layout(title='Modeled historical media contribution',height=max(300,70*len(contrib)),margin=dict(l=10,r=10,t=55,b=10),yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig2,width="stretch",config={'displaylogo':False})

    _step("Where should the next dollar go?", "05", "Change the total budget, compare the current mix with a constrained scenario, and inspect the modeled response curve before acting.")
    current_total=sum(float(pd.to_numeric(df[c],errors='coerce').fillna(0).tail(min(8,len(df))).mean()) for c in media_cols)
    budget_col, currency_col = st.columns([2.2, 1])
    with budget_col:
        total_budget=_money_input(f"Media budget to allocate per {period_name}",float(round(current_total,0)),"mmm_period_budget")
    with currency_col:
        money_unit=st.selectbox("Display currency", ["Source units", "USD ($)", "GBP (£)", "EUR (€)", "CAD ($)", "AUD ($)", "PKR (₨)"], key="mmm_currency_display", help="This changes display only; the model uses the units already present in your spend and outcome data.")
    money_symbol={"Source units":"","USD ($)":"$","GBP (£)":"£","EUR (€)":"€","CAD ($)":"$","AUD ($)":"$","PKR (₨)":"₨"}[money_unit]
    if total_budget<=0: return
    try:
        opt=optimize_budget(df,result,media_cols,total_budget)
    except ValueError as exc:
        st.warning(str(exc))
        return
    alloc=[]
    for c in media_cols: alloc.append({'Channel':c,'Current':opt['current'][c],'CampaignLab scenario':opt['recommended'][c],'Change':opt['recommended'][c]-opt['current'][c]})
    allocation=pd.DataFrame(alloc)
    gain=opt['modeled_media_response_recommended']-opt['modeled_media_response_current']
    base=max(abs(opt['modeled_media_response_current']),1e-9); gain_pct=gain/base
    st.markdown(f'<div class="cl-mmm-opportunity"><span>MODELED OPPORTUNITY</span><b>Same {_money(opt["total_weekly_budget"], money_symbol)} budget per {period_name} · {gain_pct:+.1%} modeled media response</b><p>The optimizer reallocates within historically supported ranges. Treat this as a scenario to interrogate, not a causal guarantee.</p></div>',unsafe_allow_html=True)
    st.dataframe(allocation.style.format({'Current': money_symbol + '{:,.0f}', 'CampaignLab scenario': money_symbol + '{:,.0f}', 'Change': money_symbol + '{:+,.0f}'}),width="stretch",hide_index=True)

    with st.expander("Explore channel response curves",expanded=False):
        st.caption("These curves show the response shape implied by the fitted beta MMM. Current and scenario spend are marked so you can see where CampaignLab believes marginal headroom remains.")
        for i,c in enumerate(media_cols):
            st.plotly_chart(_response_curve(c,result['channels'][c],opt['current'][c],opt['recommended'][c], period_name),width="stretch",config={'displaylogo':False},key=f'mmm_curve_{i}_{c}')
    st.caption(opt['guardrail'])

    _step("CampaignLab's decision", "06", "A model is useful only when it changes what you do — and tells you what could make that decision wrong.")
    changes=allocation.sort_values('Change')
    down=changes.iloc[0]; up=changes.iloc[-1]
    if strength == "Limited":
        move="Hold the current mix. CampaignLab does not see enough incremental out-of-sample value from the media variables to defend a budget reallocation from this model."
    elif float(up['Change']) > 0 and float(down['Change']) < 0:
        move=f"Shift about {_money(abs(float(down['Change'])), money_symbol)} per {period_name} away from {str(down['Channel']).replace('_',' ').title()} and toward {str(up['Channel']).replace('_',' ').title()}, while staying inside the modeled support range."
    else:
        move="Keep the current mix close to where it is; this model does not find a strong enough reallocation signal to justify a dramatic move."
    confidence="Moderate" if strength=="Moderate" and readiness.report.status=='ready' else "Cautious"
    caveat="Unmeasured promotions, competitor activity, correlated channel changes, or response outside historical spend support could change the conclusion."
    best_next_evidence="Validate the highest-upside reallocation with a geo-lift or another credible incrementality design before a large irreversible move."
    decision = decision_from_mmm(
        move=move,
        outcome=outcome_col,
        model_result=result,
        readiness_status=readiness.report.status,
        gain_pct=gain_pct,
        next_check=best_next_evidence,
        caveat=caveat,
    )
    render_decision_record(decision, key="mmm_decision")
    render_decision_memory()
    if st.button("🔬 Validate this decision in Evidence Lab →", width="stretch", key="mmm_to_evidence"):
        prepare_mmm_handoff(
            move=move,
            outcome=outcome_col,
            confidence=confidence,
            caveat=caveat,
            best_next_evidence=best_next_evidence,
            budget_period=f"Per-{period_name} allocation scenario",
        )
        st.query_params["page"] = "evidence"
        st.rerun()

    with st.expander("Analyst view · See the machinery"):
        st.write("Each channel receives a geometric adstock transformation for carryover, then competes across exponential and Hill saturation shapes. CampaignLab selects transformations from training history, fits non-negative media effects alongside trend, seasonality and controls, and chooses regularization using rolling validation inside the training window before scoring once on the final chronological holdout.")
        st.write("Contribution intervals use a residual block bootstrap. They are conditional on the selected response shape and do not represent full Bayesian posterior or causal uncertainty.")
        st.write("The budget optimizer searches within historically plausible spend bounds. This beta intentionally reports observational evidence strength rather than claiming causal certainty. When supplied, experiment calibration affects only its stated channel and spend contrast.")
        backtests=result['model'].get('expanding_window_backtests') or []
        if backtests:
            st.markdown("**Expanding-window backtests**")
            st.dataframe(pd.DataFrame(backtests),width="stretch",hide_index=True)
        sensitivity=result['model'].get('control_sensitivity') or []
        if sensitivity:
            st.markdown("**Leave-one-control-out sensitivity**")
            st.dataframe(pd.DataFrame(sensitivity),width="stretch",hide_index=True)
        calibrations=result['model'].get('experiment_calibration') or []
        if calibrations:
            st.markdown("**Experiment calibration provenance**")
            st.dataframe(pd.DataFrame(calibrations),width="stretch",hide_index=True)
