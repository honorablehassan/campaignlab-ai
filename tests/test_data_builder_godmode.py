import numpy as np
import pandas as pd
import pytest

from analytics.data_builder import (
    detect_source, suggest_mapping, normalize_ad_export,
    build_event_funnel, build_mmm_dataset, _periodize,
)


def _base(n=20):
    return pd.date_range('2025-01-01', periods=n, freq='D')

# 60 mapping tests
MAPPING_CASES = [
    ('date','date'),('day','date'),('week','date'),('event_date','date'),('date_start','date'),('segments_date','date'),('period','date'),
    ('campaign','campaign'),('campaign_name','campaign'),('campaign_id','campaign'),
    ('spend','spend'),('amount_spent','spend'),('cost','spend'),('media_cost','spend'),('ad_spend','spend'),
    ('impressions','impressions'),('impression','impressions'),
    ('clicks','clicks'),('link_clicks','clicks'),('outbound_clicks','clicks'),
    ('conversions','conversions'),('purchases','conversions'),('orders','conversions'),('transactions','conversions'),('leads','conversions'),
    ('revenue','revenue'),('sales','revenue'),('net_sales','revenue'),('gmv','revenue'),('purchase_value','revenue'),('conversion_value','revenue'),('all_conversions_value','revenue'),
    ('event_name','event'),('event','event'),
    ('user_pseudo_id','user'),('user_id','user'),('customer_id','user'),('client_id','user'),
    ('session_id','session'),('ga_session_id','session'),('session_key','session'),
    ('event_timestamp','timestamp'),('timestamp','timestamp'),('event_time','timestamp'),('datetime','timestamp'),
    ('daily_spend','spend'),('meta_spend','spend'),('weekly_revenue','revenue'),('total_clicks','clicks'),('paid_impressions','impressions'),
    ('campaign_name_export','campaign'),('export_event_name','event'),('customer_id_export','user'),('event_timestamp_utc','timestamp'),
    ('google_cost','spend'),('shop_sales','revenue'),('purchase_orders','conversions'),('web_clicks','clicks'),('served_impressions','impressions'),
]

@pytest.mark.parametrize('col,role', MAPPING_CASES)
def test_builder_mapping_aliases(col, role):
    df = pd.DataFrame({col: [1,2,3]})
    m = suggest_mapping(df)['mapping']
    assert m.get(role) == col

# source detection variants (24)
SOURCE_CASES = []
for i in range(6):
    SOURCE_CASES.append(('ga4_events', pd.DataFrame({'event_name':['page_view']*5,'user_pseudo_id':[f'u{x}' for x in range(5)],'event_timestamp':np.arange(5)}), f'ga4_export_{i}'))
    SOURCE_CASES.append(('meta_ads', pd.DataFrame({'date':_base(5),'spend':np.arange(5)+1,'impressions':100,'campaign_name':['c']*5,'placement':['feed']*5}), f'meta_ads_{i}'))
    SOURCE_CASES.append(('google_ads', pd.DataFrame({'segments_date':_base(5),'cost':np.arange(5)+1,'impressions':100,'clicks':10,'conversions':1,'search_impression_share':.5}), f'google_ads_{i}'))
    SOURCE_CASES.append(('sales', pd.DataFrame({'date':_base(5),'net_sales':np.arange(5)+100,'orders':np.arange(5)+1,'customer_id':[f'u{x}' for x in range(5)]}), f'sales_{i}'))

@pytest.mark.parametrize('expected,df,name', SOURCE_CASES)
def test_source_detection(expected, df, name):
    assert detect_source(df, name)['kind'] == expected

# ad normalization variants (30)
@pytest.mark.parametrize('spend_name', ['spend','amount_spent','cost','media_cost','ad_spend'])
@pytest.mark.parametrize('date_name', ['date','day','event_date','segments_date','date_start','period'])
def test_normalize_ad_export_alias_combinations(spend_name, date_name):
    n=14
    df=pd.DataFrame({date_name:_base(n),spend_name:np.arange(n)+1,'impressions':1000,'clicks':20,'purchases':2,'purchase_value':200})
    out, rep=normalize_ad_export(df, platform='meta')
    assert rep.status in {'ready','caution'}
    assert len(out)==n
    assert out['spend'].sum()==pytest.approx(sum(range(1,n+1)))
    assert out['date'].notna().all()

@pytest.mark.parametrize('bad_case', ['missing_date','missing_spend','negative_spend','nan_spend','inf_spend','bad_dates'])
def test_normalize_ad_export_blocks_core_evidence_problems(bad_case):
    n=20
    df=pd.DataFrame({'date':_base(n),'spend':np.arange(n)+1.0,'impressions':100})
    if bad_case=='missing_date': df=df.drop(columns='date')
    elif bad_case=='missing_spend': df=df.drop(columns='spend')
    elif bad_case=='negative_spend': df.loc[0,'spend']=-10
    elif bad_case=='nan_spend': df.loc[0,'spend']=np.nan
    elif bad_case=='inf_spend': df.loc[0,'spend']=np.inf
    elif bad_case=='bad_dates': df['date']='not-a-date'
    out, rep=normalize_ad_export(df, platform='meta')
    assert rep.status=='blocked'
    assert rep.blockers

# event funnels across different entity definitions, ordering, duplicates, noise (36)
def _event_df(n_sessions=50, break_stage=None, out_of_order=False, duplicate_events=False):
    rows=[]
    stages=['page_view','view_item','add_to_cart','begin_checkout','purchase']
    for s in range(n_sessions):
        user=f'u{s//2}'; sid=f's{s}'
        seq=stages.copy()
        if break_stage and s%2==0 and break_stage in seq: seq=seq[:seq.index(break_stage)]
        if out_of_order and s%3==0: seq=['page_view','add_to_cart','view_item','begin_checkout','purchase']
        for j,e in enumerate(seq):
            rows.append((user,sid,e,pd.Timestamp('2026-01-01')+pd.Timedelta(minutes=s*10+j)))
            if duplicate_events and j==0: rows.append((user,sid,e,pd.Timestamp('2026-01-01')+pd.Timedelta(minutes=s*10+j, seconds=1)))
        rows.append((user,sid,'scroll',pd.Timestamp('2026-01-01')+pd.Timedelta(minutes=s*10+8)))
    return pd.DataFrame(rows,columns=['user_pseudo_id','session_id','event_name','event_time'])

@pytest.mark.parametrize('n_sessions', [2,5,10,25,50,100])
def test_event_funnel_clean_is_monotone(n_sessions):
    df=_event_df(n_sessions)
    out=build_event_funnel(df,['page_view','view_item','add_to_cart','begin_checkout','purchase'],timestamp_col='event_time')
    counts=[x['count'] for x in out['stages']]
    assert counts==[n_sessions]*5
    assert counts==sorted(counts, reverse=True)

@pytest.mark.parametrize('break_stage', ['view_item','add_to_cart','begin_checkout','purchase'])
@pytest.mark.parametrize('n_sessions', [10,40,100])
def test_event_funnel_dropoff_is_monotone(break_stage,n_sessions):
    df=_event_df(n_sessions,break_stage=break_stage)
    out=build_event_funnel(df,['page_view','view_item','add_to_cart','begin_checkout','purchase'],timestamp_col='event_time')
    counts=[x['count'] for x in out['stages']]
    assert all(counts[i]>=counts[i+1] for i in range(len(counts)-1))
    assert counts[-1] <= counts[0]

@pytest.mark.parametrize('ordered', [True,False])
@pytest.mark.parametrize('dupes', [True,False])
@pytest.mark.parametrize('sessions', [12,37,88])
def test_event_funnel_duplicate_noise_does_not_overcount(ordered,dupes,sessions):
    df=_event_df(sessions,duplicate_events=dupes)
    out=build_event_funnel(df,['page_view','view_item','add_to_cart','purchase'],timestamp_col='event_time',require_order=ordered)
    assert all(x['count']<=sessions for x in out['stages'])

@pytest.mark.parametrize('sessions', [10,30,90])
def test_event_funnel_order_guard_rejects_out_of_order_progression(sessions):
    df=_event_df(sessions,out_of_order=True)
    ordered=build_event_funnel(df,['page_view','view_item','add_to_cart','begin_checkout','purchase'],timestamp_col='event_time',require_order=True)
    loose=build_event_funnel(df,['page_view','view_item','add_to_cart','begin_checkout','purchase'],timestamp_col='event_time',require_order=False)
    assert ordered['stages'][-1]['count'] <= loose['stages'][-1]['count']

@pytest.mark.parametrize('bad', ['one_stage','missing_event','missing_identity'])
def test_event_funnel_blocks_invalid_requests(bad):
    df=_event_df(5)
    if bad=='one_stage':
        with pytest.raises(ValueError): build_event_funnel(df,['purchase'])
    elif bad=='missing_event':
        with pytest.raises(ValueError): build_event_funnel(df.drop(columns='event_name'),['page_view','purchase'])
    else:
        with pytest.raises(ValueError): build_event_funnel(df.drop(columns=['user_pseudo_id','session_id']),['page_view','purchase'])

# periodization 18
@pytest.mark.parametrize('grain', ['day','week','month'])
@pytest.mark.parametrize('offset', [0,1,6,13,29,60])
def test_periodize_is_deterministic(grain,offset):
    s=pd.Series([pd.Timestamp('2026-01-01')+pd.Timedelta(days=offset)])
    p=_periodize(s,grain)
    assert pd.notna(p.iloc[0])
    if grain=='week': assert p.iloc[0].weekday()==0
    if grain=='month': assert p.iloc[0].day==1

# MMM multi-source data builder variants (40+)
def _media(name='meta', start='2024-01-01', periods=730, freq='D', missing_days=None):
    d=pd.date_range(start,periods=periods,freq=freq)
    x=pd.DataFrame({'date':d,'spend':100+20*np.sin(np.arange(len(d))/13),'impressions':10000,'clicks':500,'campaign_name':[name]*len(d)})
    if missing_days: x=x.drop(index=list(range(min(missing_days,len(x)))))
    return x

def _sales(start='2024-01-01', periods=104, freq='W-MON'):
    d=pd.date_range(start,periods=periods,freq=freq)
    return pd.DataFrame({'date':d,'revenue':10000+np.arange(len(d))*10,'orders':100})

@pytest.mark.parametrize('grain', ['week','month'])
@pytest.mark.parametrize('n_media', [1,2,3,4])
@pytest.mark.parametrize('explicit_outcome', [True,False])
def test_mmm_builder_combines_separate_sources(grain,n_media,explicit_outcome):
    sources=[]
    for i in range(n_media): sources.append({'name':f'channel_{i}','kind':'meta_ads' if i%2==0 else 'google_ads','df':_media(f'c{i}')})
    sources.append({'name':'commerce','kind':'sales','df':_sales()})
    out, rep=build_mmm_dataset(sources,grain=grain,outcome_source='commerce' if explicit_outcome else None)
    assert rep['status'] in {'ready','caution'}
    assert len(rep['media_columns'])==n_media
    assert 'revenue' in out
    assert out['period'].is_monotonic_increasing

@pytest.mark.parametrize('missing_days', [1,7,14,30,60,120])
def test_mmm_builder_preserves_unknown_missing_media(missing_days):
    sources=[{'name':'meta','kind':'meta_ads','df':_media(missing_days=missing_days)},{'name':'sales','kind':'sales','df':_sales()}]
    out, rep=build_mmm_dataset(sources,grain='week',outcome_source='sales',fill_missing_media_zero=False)
    assert rep['status'] in {'caution','ready'}
    col=rep['media_columns'][0]
    if rep['missing_media_periods'][col]>0:
        assert out[col].isna().sum()==rep['missing_media_periods'][col]
        assert any('unknown' in w for w in rep['warnings'])

@pytest.mark.parametrize('missing_days', [7,30,90])
def test_mmm_builder_zero_fill_is_explicit_and_disclosed(missing_days):
    sources=[{'name':'meta','kind':'meta_ads','df':_media(missing_days=missing_days)},{'name':'sales','kind':'sales','df':_sales()}]
    out, rep=build_mmm_dataset(sources,grain='week',outcome_source='sales',fill_missing_media_zero=True)
    col=rep['media_columns'][0]
    assert out[col].isna().sum()==0
    if rep['missing_media_periods'][col]>0: assert any('zero-filled by request' in w for w in rep['warnings'])

@pytest.mark.parametrize('bad', ['no_media','two_outcomes','missing_df','sales_no_revenue','media_no_spend'])
def test_mmm_builder_blocks_ambiguous_or_unusable_builds(bad):
    if bad=='no_media': sources=[{'name':'sales','kind':'sales','df':_sales()}]
    elif bad=='two_outcomes': sources=[{'name':'meta','kind':'meta_ads','df':_media()},{'name':'s1','kind':'sales','df':_sales()},{'name':'s2','kind':'sales','df':_sales()}]
    elif bad=='missing_df': sources=[{'name':'meta','kind':'meta_ads','df':None},{'name':'sales','kind':'sales','df':_sales()}]
    elif bad=='sales_no_revenue': sources=[{'name':'meta','kind':'meta_ads','df':_media()},{'name':'sales','kind':'sales','df':_sales().drop(columns='revenue')}]
    else: sources=[{'name':'meta','kind':'meta_ads','df':_media().drop(columns='spend')},{'name':'sales','kind':'sales','df':_sales()}]
    out, rep=build_mmm_dataset(sources,grain='week')
    assert rep['status']=='blocked'
    assert rep['blockers']
    assert out.empty
