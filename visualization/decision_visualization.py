from __future__ import annotations

from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analytics.dataset_intelligence import DatasetIntelligence
from visualization.style import annotate_bars, clean_axes, finalize, format_compact_axis, format_percent_axis


def recommend_visualizations(intel: DatasetIntelligence, question: str = "") -> list[dict[str, Any]]:
    """Return the smallest decision-oriented visualization set justified by the evidence."""
    roles = intel.role_map
    plans: list[dict[str, Any]] = []
    q = (question or "").lower()

    if roles.get("treatment") and roles.get("binary_outcome"):
        plans.append({
            "id": "group_outcome_rate",
            "title": "Outcome rate by treatment group",
            "why": "Shows the observed treatment/control gap before statistical interpretation.",
            "priority": 100 if any(x in q for x in ["cause", "lift", "impact", "test", "experiment"]) else 96,
        })

    if roles.get("spend") and roles.get("revenue") and (roles.get("channel") or roles.get("campaign")):
        group = (roles.get("channel") or roles.get("campaign"))[0]
        plans.append({"id": "efficiency_rank", "title": f"Efficiency by {group}", "why": "Ranks where spend is producing the strongest return.", "priority": 98 if any(x in q for x in ["budget", "roas", "efficiency", "channel"]) else 94})
        plans.append({"id": "spend_vs_revenue", "title": "Spend vs revenue", "why": "Separates scale from efficiency and exposes expensive underperformers.", "priority": 88})

    if roles.get("date") and (roles.get("revenue") or roles.get("conversions") or roles.get("spend")):
        plans.append({"id": "performance_over_time", "title": "Performance over time", "why": "Shows trend, breaks, seasonality, and whether a result is persistent.", "priority": 90 if any(x in q for x in ["trend", "change", "when", "time", "anomal"]) else 82})

    if roles.get("treatment") and roles.get("date") and (roles.get("continuous_outcome") or roles.get("revenue") or roles.get("conversions")):
        plans.append({"id": "group_trends", "title": "Treatment and comparison trends", "why": "Shows whether groups moved similarly before/through time and whether a visible break aligns with intervention timing.", "priority": 97 if any(x in q for x in ["did", "before", "after", "rollout", "event", "causal"]) else 84})

    if (roles.get("customer") or roles.get("id")) and roles.get("date"):
        plans.append({"id": "retention_heatmap", "title": "Cohort retention map", "why": "Shows how repeated customer activity decays or persists by acquisition cohort and age.", "priority": 96 if any(x in q for x in ["retention", "cohort", "repeat", "lifecycle"]) else 76})

    if roles.get("impressions") and roles.get("clicks") and roles.get("conversions"):
        plans.append({"id": "media_funnel", "title": "Media funnel", "why": "Shows where the largest observed drop occurs from impression to click to conversion.", "priority": 95 if any(x in q for x in ["funnel", "ctr", "cvr", "drop"]) else 75})

    missing = [s for s in intel.column_signals if s["missing_rate"] > 0]
    if missing:
        plans.append({"id": "missingness", "title": "Missingness by field", "why": "Shows where evidence quality may threaten the analysis.", "priority": 68})

    if not plans:
        plans.append({"id": "numeric_distributions", "title": "Key numeric distribution", "why": "A safe first look when no decision-specific chart can yet be justified.", "priority": 50})

    return sorted(plans, key=lambda x: x["priority"], reverse=True)[:4]


def build_visualization(df: pd.DataFrame, intel: DatasetIntelligence, chart_id: str):
    roles = intel.role_map

    if chart_id == "missingness":
        rates = df.isna().mean().sort_values(ascending=True)
        rates = rates[rates > 0].tail(15)
        if rates.empty:
            return None
        values = rates.values * 100
        fig, ax = plt.subplots(figsize=(8, max(3.5, len(rates) * 0.35)))
        ax.barh(rates.index.astype(str), values)
        ax.set_xlabel("Missing values")
        format_percent_axis(ax, axis="x", decimals=0)
        clean_axes(ax, grid_axis="x")
        annotate_bars(ax, values, horizontal=True, suffix="%", decimals=1)
        finalize(fig, ax, title="Missingness by field", subtitle="Only fields with missing values are shown")
        return fig

    if chart_id == "group_outcome_rate":
        g = roles.get("treatment", [None])[0]
        y = roles.get("binary_outcome", [None])[0]
        if not g or not y:
            return None
        tmp = df[[g, y]].dropna().copy()
        if not pd.api.types.is_numeric_dtype(tmp[y]):
            values = list(tmp[y].dropna().unique())
            if len(values) != 2:
                return None
            positive = values[-1]
            tmp["__outcome__"] = (tmp[y] == positive).astype(int)
            y = "__outcome__"
        rates = tmp.groupby(g)[y].mean().sort_values(ascending=False).head(10) * 100
        fig, ax = plt.subplots(figsize=(8, 4.4))
        ax.bar(rates.index.astype(str), rates.values, width=0.62)
        ax.set_ylabel("Outcome rate")
        ax.set_ylim(bottom=0)
        format_percent_axis(ax, axis="y", decimals=1)
        clean_axes(ax, grid_axis="y")
        annotate_bars(ax, rates.values, suffix="%", decimals=1)
        if len(rates) > 5:
            ax.tick_params(axis="x", rotation=25)
        finalize(fig, ax, title="Outcome rate by treatment group", subtitle=f"Outcome: {roles.get('binary_outcome', [''])[0]}")
        return fig

    if chart_id == "efficiency_rank":
        group = (roles.get("channel") or roles.get("campaign") or [None])[0]
        spend = roles.get("spend", [None])[0]
        revenue = roles.get("revenue", [None])[0]
        if not all((group, spend, revenue)):
            return None
        tmp = df[[group, spend, revenue]].copy()
        tmp[spend] = pd.to_numeric(tmp[spend], errors="coerce")
        tmp[revenue] = pd.to_numeric(tmp[revenue], errors="coerce")
        agg = tmp.groupby(group, dropna=False)[[spend, revenue]].sum(min_count=1).dropna()
        agg = agg[agg[spend] > 0]
        if agg.empty:
            return None
        agg["roas"] = agg[revenue] / agg[spend]
        top = agg.sort_values("roas").tail(12)
        values = top["roas"].values
        fig, ax = plt.subplots(figsize=(8, max(4, len(top) * 0.36)))
        ax.barh(top.index.astype(str), values)
        ax.set_xlabel("ROAS (revenue / spend)")
        clean_axes(ax, grid_axis="x")
        annotate_bars(ax, values, horizontal=True, suffix="×", decimals=2)
        finalize(fig, ax, title=f"Efficiency by {group}", subtitle="Higher is better; read alongside scale and incrementality")
        return fig

    if chart_id == "spend_vs_revenue":
        spend = roles.get("spend", [None])[0]
        revenue = roles.get("revenue", [None])[0]
        group = (roles.get("channel") or roles.get("campaign") or [None])[0]
        if not all((spend, revenue)):
            return None
        if group:
            tmp = df[[group, spend, revenue]].copy()
            tmp[spend] = pd.to_numeric(tmp[spend], errors="coerce")
            tmp[revenue] = pd.to_numeric(tmp[revenue], errors="coerce")
            plot = tmp.groupby(group)[[spend, revenue]].sum(min_count=1).dropna()
        else:
            plot = df[[spend, revenue]].apply(pd.to_numeric, errors="coerce").dropna()
        if plot.empty:
            return None
        fig, ax = plt.subplots(figsize=(7.8, 4.7))
        ax.scatter(plot[spend], plot[revenue], alpha=0.72, s=52)
        ax.set_xlabel(spend)
        ax.set_ylabel(revenue)
        format_compact_axis(ax, axis="x")
        format_compact_axis(ax, axis="y")
        clean_axes(ax, grid_axis="both")
        if group and len(plot) <= 12:
            for label, row in plot.iterrows():
                ax.annotate(str(label), (row[spend], row[revenue]), xytext=(5, 5), textcoords="offset points", fontsize=8.5, alpha=0.78)
        finalize(fig, ax, title="Spend vs revenue", subtitle="Look for high-spend points that fail to produce proportional return")
        return fig

    if chart_id == "performance_over_time":
        date = roles.get("date", [None])[0]
        metric = (roles.get("revenue") or roles.get("conversions") or roles.get("spend") or [None])[0]
        if not date or not metric:
            return None
        tmp = df[[date, metric]].copy()
        tmp[date] = pd.to_datetime(tmp[date], errors="coerce")
        tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
        tmp = tmp.dropna().sort_values(date)
        if tmp.empty:
            return None
        agg = tmp.groupby(date)[metric].sum().sort_index()
        fig, ax = plt.subplots(figsize=(8.2, 4.35))
        ax.plot(agg.index, agg.values, linewidth=1.9)
        ax.set_ylabel(metric)
        format_compact_axis(ax, axis="y")
        clean_axes(ax, grid_axis="y")
        locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        finalize(fig, ax, title=f"{metric} over time", subtitle="Use this to spot trend shifts, breaks, and concentrated performance")
        return fig

    if chart_id == "group_trends":
        date = roles.get("date", [None])[0]
        group = roles.get("treatment", [None])[0]
        metric = (roles.get("continuous_outcome") or roles.get("revenue") or roles.get("conversions") or [None])[0]
        if not all((date, group, metric)): return None
        tmp=df[[date,group,metric]].copy(); tmp[date]=pd.to_datetime(tmp[date],errors="coerce"); tmp[metric]=pd.to_numeric(tmp[metric],errors="coerce"); tmp=tmp.dropna()
        if tmp.empty: return None
        plot=tmp.groupby([date,group])[metric].mean().unstack(group).sort_index()
        fig,ax=plt.subplots(figsize=(8.4,4.6))
        for col in plot.columns: ax.plot(plot.index,plot[col],linewidth=1.8,label=str(col))
        ax.set_ylabel(metric); clean_axes(ax,grid_axis="y"); format_compact_axis(ax,axis="y")
        locator=mdates.AutoDateLocator(minticks=4,maxticks=7); ax.xaxis.set_major_locator(locator); ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator)); ax.legend(frameon=False,ncol=min(4,len(plot.columns)))
        finalize(fig,ax,title="Treatment and comparison trends",subtitle=f"Mean {metric} over time; visual trend similarity is diagnostic, not proof of causality")
        return fig

    if chart_id == "retention_heatmap":
        customer=(roles.get("customer") or roles.get("id") or [None])[0]; date=roles.get("date",[None])[0]
        if not customer or not date: return None
        tmp=df[[customer,date]].dropna().copy(); tmp[date]=pd.to_datetime(tmp[date],errors="coerce"); tmp=tmp.dropna()
        if tmp.empty or tmp[customer].duplicated().mean()<0.02: return None
        tmp["period"]=tmp[date].dt.to_period("M"); tmp["cohort"]=tmp.groupby(customer)[date].transform("min").dt.to_period("M"); tmp["age"]=tmp["period"].astype(int)-tmp["cohort"].astype(int)
        tab=tmp.groupby(["cohort","age"])[customer].nunique().unstack(fill_value=0).sort_index().tail(12)
        if 0 not in tab.columns: return None
        ret=tab.div(tab[0],axis=0); ret=ret.loc[:, [c for c in ret.columns if c<=11]]
        fig,ax=plt.subplots(figsize=(8.4,max(4.0,len(ret)*.35)))
        im=ax.imshow(ret.values,aspect="auto",vmin=0,vmax=1)
        ax.set_yticks(range(len(ret))); ax.set_yticklabels([str(x) for x in ret.index]); ax.set_xticks(range(len(ret.columns))); ax.set_xticklabels([str(int(x)) for x in ret.columns]); ax.set_xlabel("Months since cohort start"); ax.set_ylabel("Cohort")
        for i in range(len(ret)):
            for j in range(len(ret.columns)):
                v=ret.iloc[i,j]
                if pd.notna(v): ax.text(j,i,f"{v:.0%}",ha="center",va="center",fontsize=8)
        finalize(fig,ax,title="Cohort retention map",subtitle="Repeated customer presence by monthly cohort age")
        fig.colorbar(im,ax=ax,fraction=.025,pad=.02)
        return fig

    if chart_id == "media_funnel":
        imp=roles.get("impressions",[None])[0]; clk=roles.get("clicks",[None])[0]; conv=roles.get("conversions",[None])[0]
        if not all((imp,clk,conv)): return None
        vals=[pd.to_numeric(df[c],errors="coerce").fillna(0).sum() for c in [imp,clk,conv]]
        labels=["Impressions","Clicks","Conversions"]
        fig,ax=plt.subplots(figsize=(7.8,4.2)); ax.barh(labels[::-1],vals[::-1]); clean_axes(ax,grid_axis="x"); format_compact_axis(ax,axis="x"); annotate_bars(ax,vals[::-1],horizontal=True,decimals=0); finalize(fig,ax,title="Media funnel",subtitle="Aggregate stage volume; verify stages share the same scope before interpreting drop-off")
        return fig

    if chart_id == "numeric_distributions":
        numeric = df.select_dtypes(include=[np.number]).columns.tolist()[:4]
        if not numeric:
            return None
        col = numeric[0]
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if vals.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, 4.3))
        ax.hist(vals, bins=28, alpha=0.8)
        ax.set_xlabel(col)
        ax.set_ylabel("Rows")
        format_compact_axis(ax, axis="x")
        format_compact_axis(ax, axis="y")
        clean_axes(ax, grid_axis="y")
        finalize(fig, ax, title=f"Distribution of {col}", subtitle="Fallback view when no stronger decision-specific visual is justified")
        return fig

    return None
