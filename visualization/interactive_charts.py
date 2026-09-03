from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

BG='rgba(0,0,0,0)'; TEXT='#f5f2ea'; MUTED='#a9b0b6'; GRID='rgba(255,255,255,.10)'; ACCENT='#ff704d'; COOL='#66c7ff'; GREEN='#b7f34a'; YELLOW='#ffd176'

def _layout(fig,title,subtitle='',legend=False,height=430):
    fig.update_layout(template='plotly_dark',paper_bgcolor=BG,plot_bgcolor=BG,margin=dict(l=42,r=28,t=86,b=48),height=height,
        title=dict(text=f'<b>{title}</b><br><span style="font-size:12px;color:{MUTED}">{subtitle}</span>',x=.01,xanchor='left'),
        font=dict(color=TEXT,size=13),hoverlabel=dict(bgcolor='#151b20',font_color=TEXT,bordercolor='rgba(255,255,255,.15)'),showlegend=legend,
        legend=dict(orientation='h',yanchor='bottom',y=1.02,xanchor='right',x=1))
    fig.update_xaxes(gridcolor=GRID,zeroline=False,title_font=dict(color=MUTED),tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID,zeroline=False,title_font=dict(color=MUTED),tickfont=dict(color=MUTED))
    return fig

def group_outcome_rate(df, group, outcome):
    tmp=df[[group,outcome]].copy(); tmp[outcome]=pd.to_numeric(tmp[outcome],errors='coerce'); tmp=tmp.dropna(); rates=tmp.groupby(group)[outcome].agg(['mean','sum','count']).reset_index()
    fig=go.Figure(go.Bar(x=rates[group].astype(str),y=rates['mean'],marker_color=[COOL if i==0 else ACCENT for i in range(len(rates))],customdata=rates[['sum','count']],text=[f'{x:.1%}' for x in rates['mean']],textposition='outside',hovertemplate='<b>%{x}</b><br>Outcome rate: %{y:.2%}<br>Events: %{customdata[0]:,.0f}<br>Rows: %{customdata[1]:,.0f}<extra></extra>'))
    fig.update_yaxes(tickformat='.0%',title='Outcome rate'); return _layout(fig,'Observed outcome by group','Hover for exact rates and sample sizes. Observed gaps are not causal conclusions by themselves.')

def efficiency_rank(df, group, spend, revenue):
    tmp=df[[group,spend,revenue]].copy(); tmp[spend]=pd.to_numeric(tmp[spend],errors='coerce'); tmp[revenue]=pd.to_numeric(tmp[revenue],errors='coerce'); tmp=tmp.dropna(); agg=tmp.groupby(group)[[spend,revenue]].sum(); agg['roas']=agg[revenue]/agg[spend].replace(0,pd.NA); agg=agg.dropna().sort_values('roas')
    fig=go.Figure(go.Bar(y=agg.index.astype(str),x=agg['roas'],orientation='h',marker_color=ACCENT,customdata=agg[[spend,revenue]],text=[f'{x:.2f}×' for x in agg['roas']],textposition='outside',hovertemplate='<b>%{y}</b><br>ROAS: %{x:.2f}×<br>Spend: %{customdata[0]:$,.0f}<br>Revenue: %{customdata[1]:$,.0f}<extra></extra>'))
    fig.update_xaxes(title='Observed ROAS'); return _layout(fig,f'Efficiency by {group}','Observed attribution efficiency. Hover to compare spend and revenue; do not read this as incrementality.',height=max(420,70+42*len(agg)))

def spend_vs_revenue(df, group, spend, revenue):
    tmp=df[[group,spend,revenue]].copy(); tmp[spend]=pd.to_numeric(tmp[spend],errors='coerce'); tmp[revenue]=pd.to_numeric(tmp[revenue],errors='coerce'); tmp=tmp.dropna(); agg=tmp.groupby(group)[[spend,revenue]].sum().reset_index(); agg['roas']=agg[revenue]/agg[spend].replace(0,pd.NA)
    fig=go.Figure(go.Scatter(x=agg[spend],y=agg[revenue],mode='markers+text',text=agg[group].astype(str),textposition='top center',marker=dict(size=14,color=COOL,line=dict(width=1,color='white')),customdata=agg[[group,'roas']],hovertemplate='<b>%{customdata[0]}</b><br>Spend: %{x:$,.0f}<br>Revenue: %{y:$,.0f}<br>ROAS: %{customdata[1]:.2f}×<extra></extra>'))
    fig.update_xaxes(title='Spend'); fig.update_yaxes(title='Revenue'); return _layout(fig,'Spend vs revenue','Scale and efficiency are different stories. Hover to inspect each channel.')

def performance_over_time(df,date,metric):
    tmp=df[[date,metric]].copy(); tmp[date]=pd.to_datetime(tmp[date],errors='coerce'); tmp[metric]=pd.to_numeric(tmp[metric],errors='coerce'); tmp=tmp.dropna(); agg=tmp.groupby(date)[metric].sum().sort_index()
    fig=go.Figure(go.Scatter(x=agg.index,y=agg.values,mode='lines',line=dict(width=2.4,color=COOL),hovertemplate='%{x|%b %d, %Y}<br>'+metric+': %{y:,.2f}<extra></extra>'))
    fig.update_yaxes(title=metric); return _layout(fig,f'{metric} over time','Hover for exact values. Look for trend shifts, breaks and concentrated performance.')

def group_trends(df,date,group,metric):
    tmp=df[[date,group,metric]].copy(); tmp[date]=pd.to_datetime(tmp[date],errors='coerce'); tmp[metric]=pd.to_numeric(tmp[metric],errors='coerce'); tmp=tmp.dropna(); plot=tmp.groupby([date,group])[metric].mean().reset_index()
    fig=px.line(plot,x=date,y=metric,color=group,markers=True); fig.update_traces(hovertemplate='<b>%{fullData.name}</b><br>%{x|%b %d, %Y}<br>'+metric+': %{y:,.3f}<extra></extra>')
    return _layout(fig,'Treatment and comparison trends',f'Mean {metric} over time. Similar-looking pre-trends are diagnostic, not proof of causality.',legend=True)

def retention_heatmap(df,customer,date):
    tmp=df[[customer,date]].dropna().copy(); tmp[date]=pd.to_datetime(tmp[date],errors='coerce'); tmp=tmp.dropna(); tmp['period']=tmp[date].dt.to_period('M'); tmp['cohort']=tmp.groupby(customer)[date].transform('min').dt.to_period('M'); tmp['age']=(tmp['period'].dt.year-tmp['cohort'].dt.year)*12+(tmp['period'].dt.month-tmp['cohort'].dt.month)
    tab=tmp.groupby(['cohort','age'])[customer].nunique().unstack(fill_value=0).sort_index().tail(12)
    if 0 not in tab.columns: return None
    ret=tab.div(tab[0],axis=0); ret=ret.loc[:, [c for c in ret.columns if c<=11]]
    fig=go.Figure(go.Heatmap(z=ret.values,x=[int(x) for x in ret.columns],y=[str(x) for x in ret.index],colorscale=[[0,'#182028'],[.5,'#66c7ff'],[1,'#b7f34a']],zmin=0,zmax=1,colorbar=dict(title='Retention',tickformat='.0%'),hovertemplate='Cohort: %{y}<br>Month: %{x}<br>Retention: %{z:.1%}<extra></extra>'))
    fig.update_xaxes(title='Months since cohort start'); fig.update_yaxes(title='Cohort'); return _layout(fig,'Cohort retention map','Repeated customer presence by cohort age.',height=max(430,110+30*len(ret)))

def media_funnel(df,impressions,clicks,conversions):
    labels=['Impressions','Clicks','Conversions']; vals=[pd.to_numeric(df[c],errors='coerce').fillna(0).sum() for c in [impressions,clicks,conversions]]
    fig=go.Figure(go.Funnel(y=labels,x=vals,textinfo='value+percent initial',marker=dict(color=[COOL,ACCENT,GREEN]),hovertemplate='<b>%{y}</b><br>Volume: %{x:,.0f}<br>% of start: %{percentInitial:.1%}<extra></extra>'))
    return _layout(fig,'Media funnel','Aggregate stage volume. Verify that all stages share the same scope before interpreting drop-off.')

def missingness(df):
    rates=df.isna().mean().sort_values().loc[lambda s:s>0].tail(15)
    if rates.empty: return None
    fig=go.Figure(go.Bar(y=rates.index.astype(str),x=rates.values,orientation='h',marker_color=YELLOW,text=[f'{x:.1%}' for x in rates.values],textposition='outside',hovertemplate='<b>%{y}</b><br>Missing: %{x:.2%}<extra></extra>'))
    fig.update_xaxes(tickformat='.0%',title='Missing share'); return _layout(fig,'Missingness by field','Only fields with missing values are shown.',height=max(400,100+32*len(rates)))

def numeric_distribution(df):
    numeric=df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric: return None
    col=numeric[0]; vals=pd.to_numeric(df[col],errors='coerce').dropna()
    fig=go.Figure(go.Histogram(x=vals,nbinsx=28,marker_color=COOL,hovertemplate='Range: %{x}<br>Rows: %{y}<extra></extra>'))
    fig.update_xaxes(title=col); fig.update_yaxes(title='Rows'); return _layout(fig,f'Distribution of {col}','A fallback diagnostic when no stronger decision-specific visual is justified.')

def ab_conversion_result(result):
    labels=['Control','Treatment']; rates=[result.control_rate,result.treatment_rate]; ns=[result.control_n,result.treatment_n]; conv=[result.control_conversions,result.treatment_conversions]
    fig=go.Figure(go.Bar(x=labels,y=rates,marker_color=[COOL,ACCENT],text=[f'{x:.2%}' for x in rates],textposition='outside',customdata=list(zip(conv,ns)),hovertemplate='<b>%{x}</b><br>Conversion: %{y:.2%}<br>Conversions: %{customdata[0]:,.0f}<br>Participants: %{customdata[1]:,.0f}<extra></extra>'))
    fig.update_yaxes(tickformat='.0%',title='Conversion rate'); return _layout(fig,'Observed conversion by arm','Hover for exact rates and sample sizes.')

def ab_effect_interval(result):
    x=[result.absolute_lift]; plus=[result.ci_high-result.absolute_lift]; minus=[result.absolute_lift-result.ci_low]
    fig=go.Figure(go.Scatter(x=x,y=['Treatment effect'],mode='markers',marker=dict(size=13,color=ACCENT),error_x=dict(type='data',array=plus,arrayminus=minus,visible=True,color=TEXT,thickness=2),hovertemplate='Lift: %{x:.2%}<extra></extra>'))
    fig.add_vline(x=0,line_dash='dash',line_color=MUTED)
    if getattr(result,'business_threshold',None) is not None: fig.add_vline(x=result.business_threshold,line_dash='dot',line_color=GREEN,annotation_text='Business threshold')
    fig.update_xaxes(tickformat='.1%',title='Absolute lift'); return _layout(fig,'Treatment effect + uncertainty','The dot is the estimated lift; the interval shows the range most compatible with the data.')
