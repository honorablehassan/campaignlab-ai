from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable
import re

import numpy as np
import pandas as pd


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


SOURCE_SIGNATURES = {
    "ga4_events": {
        "required_any": [("event_name",), ("user_pseudo_id", "ga_session_id")],
        "strong": ("event_timestamp", "traffic_source", "event_bundle_sequence_id"),
        "name_hints": ("ga4", "google_analytics", "analytics_events"),
    },
    "meta_ads": {
        "required_any": [("spend", "amount_spent"), ("campaign_name", "campaign_id")],
        "strong": ("adset_name", "ad_set_name", "placement", "amount_spent", "actions", "action_values"),
        "name_hints": ("meta", "facebook", "instagram", "fb_ads"),
    },
    "google_ads": {
        "required_any": [("cost", "cost_micros", "spend"), ("campaign_name", "campaign_id")],
        "strong": ("cost_micros", "search_impression_share", "conversion_value", "all_conversions_value"),
        "name_hints": ("google_ads", "googleads", "paid_search", "search_ads"),
    },
    "sales": {
        "required_any": [("revenue", "sales", "net_sales", "gross_sales", "gmv"), ("orders", "transactions")],
        "strong": ("order_id", "customer_id", "net_sales", "gross_sales", "transactions"),
        "name_hints": ("sales", "commerce", "orders", "revenue", "shopify"),
    },
    "media_export": {
        "required_any": [("spend", "amount_spent", "cost", "media_cost"), ("campaign_name", "campaign_id", "impressions")],
        "strong": ("impressions", "clicks", "conversions"),
        "name_hints": ("youtube", "tv", "tiktok", "linkedin", "snap", "pinterest", "media"),
    },
}



def detect_source(df: pd.DataFrame, name: str = "") -> dict[str, Any]:
    cols = {_norm(c) for c in df.columns}
    name_n = _norm(name)
    scores: dict[str, int] = {}
    for kind, spec in SOURCE_SIGNATURES.items():
        score = 0
        for group in spec["required_any"]:
            if any(_norm(x) in cols for x in group):
                score += 2
        score += sum(2 for x in spec["strong"] if _norm(x) in cols)
        score += sum(5 for x in spec.get("name_hints", ()) if _norm(x) in name_n)
        scores[kind] = score

    # Platform-specific classifications should require platform-specific evidence.
    # Generic spend/campaign columns alone describe an ad export, not Meta or Google.
    meta_specific = any(x in cols for x in {"adset_name","ad_set_name","amount_spent","actions","action_values"}) or any(x in name_n for x in ("meta","facebook","instagram","fb_ads"))
    google_specific = any(x in cols for x in {"cost_micros","search_impression_share","conversion_value","all_conversions_value"}) or any(x in name_n for x in ("google_ads","googleads","paid_search","search_ads"))
    if not meta_specific:
        scores["meta_ads"] = min(scores.get("meta_ads", 0), 3)
    else:
        scores["meta_ads"] = scores.get("meta_ads", 0) + 3
    if not google_specific:
        scores["google_ads"] = min(scores.get("google_ads", 0), 3)
    else:
        scores["google_ads"] = scores.get("google_ads", 0) + 3
    if meta_specific or google_specific:
        scores["media_export"] = max(0, scores.get("media_export", 0) - 2)

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best = ordered[0][0] if ordered else "generic"
    top = ordered[0][1] if ordered else 0
    gap = top - ordered[1][1] if len(ordered) > 1 else top
    confidence = "high" if top >= 8 and gap >= 3 else "medium" if top >= 5 and gap >= 1 else "low"
    return {"kind": best if top >= 3 else "generic", "confidence": confidence, "scores": scores}



ALIASES = {
    "date": ("date", "day", "week", "event_date", "date_start", "segments_date", "period"),
    "campaign": ("campaign", "campaign_name", "campaign_id"),
    "spend": ("spend", "amount_spent", "cost", "media_cost", "ad_spend"),
    "impressions": ("impressions", "impression"),
    "clicks": ("clicks", "link_clicks", "outbound_clicks"),
    "conversions": ("conversions", "purchases", "orders", "transactions", "leads"),
    "revenue": ("revenue", "sales", "net_sales", "gross_sales", "gmv", "purchase_value", "conversion_value", "all_conversions_value"),
    "event": ("event_name", "event"),
    "user": ("user_pseudo_id", "user_id", "customer_id", "client_id"),
    "session": ("session_id", "ga_session_id", "session_key"),
    "timestamp": ("event_timestamp", "timestamp", "event_time", "datetime"),
}


def _candidate_columns(df: pd.DataFrame, role: str) -> list[str]:
    aliases = {_norm(a) for a in ALIASES[role]}
    out = []
    for c in df.columns:
        n = _norm(c)
        if n in aliases or any(n.endswith("_" + a) or n.startswith(a + "_") for a in aliases):
            out.append(c)
    return out


def suggest_mapping(df: pd.DataFrame, source_kind: str | None = None) -> dict[str, Any]:
    mapping: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}
    for role in ALIASES:
        cands = _candidate_columns(df, role)
        if len(cands) == 1:
            mapping[role] = cands[0]
        elif len(cands) > 1:
            exact = [c for c in cands if _norm(c) in {_norm(a) for a in ALIASES[role]}]
            if len(exact) == 1:
                mapping[role] = exact[0]
            else:
                ambiguous[role] = cands
    required = {
        "ga4_events": ["event"],
        "meta_ads": ["date", "spend"],
        "google_ads": ["date", "spend"],
        "sales": ["date", "revenue"],
        "media_export": ["date", "spend"],
    }.get(source_kind or "", [])
    missing_required = [r for r in required if r not in mapping]
    return {"mapping": mapping, "ambiguous": ambiguous, "missing_required": missing_required}


@dataclass
class BuildReport:
    status: str
    source_kind: str
    rows_in: int
    rows_out: int
    mapping: dict[str, str]
    warnings: list[str]
    blockers: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_ad_export(df: pd.DataFrame, platform: str | None = None, mapping: dict[str, str] | None = None) -> tuple[pd.DataFrame, BuildReport]:
    source = detect_source(df, platform or "")
    kind = source["kind"]
    sm = suggest_mapping(df, kind)
    mp = dict(sm["mapping"])
    if mapping:
        mp.update(mapping)
    blockers: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    for role in ("date", "spend"):
        if role not in mp or mp[role] not in df:
            blockers.append(f"A usable {role} field is required before CampaignLab can normalize this ad export.")
    if blockers:
        return pd.DataFrame(), BuildReport("blocked", kind, len(df), 0, mp, warnings, blockers, notes)
    d = pd.DataFrame()
    d["date"] = pd.to_datetime(df[mp["date"]], errors="coerce", format="mixed")
    for role in ("spend", "impressions", "clicks", "conversions", "revenue"):
        if role in mp and mp[role] in df:
            d[role] = pd.to_numeric(df[mp[role]], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if "campaign" in mp and mp["campaign"] in df:
        d["campaign"] = df[mp["campaign"]].astype("string")
    d["platform"] = str(platform or kind.replace("_ads", "")).strip().lower()
    bad_date = float(d["date"].isna().mean()) if len(d) else 0
    bad_spend = float(d["spend"].isna().mean()) if len(d) else 0
    if bad_date > 0:
        (blockers if bad_date > .05 else warnings).append(f"{bad_date:.1%} of rows have unparseable dates.")
    if bad_spend > 0:
        blockers.append(f"{bad_spend:.1%} of rows have missing or non-numeric spend. CampaignLab will not turn unknown spend into zero.")
    if (d["spend"].dropna() < 0).any():
        blockers.append("Negative spend is present. Reconcile credits/refunds before using this data for allocation modeling.")
    for role in ("impressions", "clicks", "conversions", "revenue"):
        if role in d and (d[role].dropna() < 0).any():
            warnings.append(f"{role.title()} contains negative values; confirm refunds/corrections are intentional.")
    if sm["ambiguous"]:
        notes.append("Some fields had multiple plausible mappings; explicit user confirmation may be useful: " + ", ".join(sm["ambiguous"].keys()))
    out = d.loc[d["date"].notna()].copy()
    status = "blocked" if blockers else ("caution" if warnings else "ready")
    return out, BuildReport(status, kind, len(df), len(out), mp, warnings, blockers, notes)


def _session_key(df: pd.DataFrame, user_col: str | None, session_col: str | None) -> pd.Series:
    if session_col and session_col in df:
        if user_col and user_col in df:
            return df[user_col].astype("string") + "::" + df[session_col].astype("string")
        return df[session_col].astype("string")
    if user_col and user_col in df:
        return df[user_col].astype("string")
    raise ValueError("A user or session identifier is required for an event funnel.")


def build_event_funnel(
    df: pd.DataFrame,
    stages: list[str],
    *,
    event_col: str = "event_name",
    user_col: str | None = "user_pseudo_id",
    session_col: str | None = "session_id",
    timestamp_col: str | None = None,
    require_order: bool = True,
) -> dict[str, Any]:
    if len(stages) < 2:
        raise ValueError("Provide at least two ordered funnel stages.")
    if event_col not in df:
        raise ValueError(f"Event field {event_col!r} was not found.")
    d = df.copy()
    d["__entity"] = _session_key(d, user_col, session_col)
    d["__event"] = d[event_col].astype("string")
    if timestamp_col and timestamp_col in d:
        if pd.api.types.is_numeric_dtype(d[timestamp_col]):
            d["__ts"] = pd.to_datetime(d[timestamp_col], unit="us", errors="coerce")
        else:
            d["__ts"] = pd.to_datetime(d[timestamp_col], errors="coerce")
    else:
        d["__ts"] = pd.RangeIndex(len(d))
    entities = d["__entity"].dropna().nunique()
    passed: set[str] | None = None
    rows = []
    for i, stage in enumerate(stages):
        sd = d[d["__event"] == stage]
        if require_order and i > 0 and passed is not None:
            sd = sd[sd["__entity"].isin(passed)]
            # For order, require this stage timestamp to occur after the last required stage.
            prev_events = d[(d["__entity"].isin(passed)) & (d["__event"] == stages[i-1])].groupby("__entity")["__ts"].min()
            cur_events = sd.groupby("__entity")["__ts"].min()
            eligible = cur_events.index.intersection(prev_events.index)
            current = set(eligible[(cur_events.loc[eligible] >= prev_events.loc[eligible]).to_numpy()].astype(str))
        else:
            current = set(sd["__entity"].dropna().astype(str).unique())
        passed = current if passed is None else (passed & current if require_order else current)
        count = len(passed) if require_order else len(current)
        prev_count = rows[-1]["count"] if rows else None
        rows.append({
            "stage": stage,
            "count": count,
            "step_conversion": (count / prev_count if prev_count else None),
            "from_start": (count / rows[0]["count"] if rows and rows[0]["count"] else (1.0 if i == 0 and count else None)),
        })
    return {
        "method": "event_funnel_builder",
        "entity_level": "session" if session_col and session_col in df else "user",
        "entities_seen": int(entities),
        "stages": rows,
        "require_order": bool(require_order),
        "warning": "Event funnels depend on event instrumentation and identity/session definitions. CampaignLab should surface missing or out-of-order instrumentation rather than inventing progression.",
    }


def _periodize(s: pd.Series, grain: str) -> pd.Series:
    dt = pd.to_datetime(s, errors="coerce")
    if grain == "day":
        return dt.dt.floor("D")
    if grain == "week":
        # Monday-start week, deterministic and easy to join across sources.
        return dt.dt.to_period("W-SUN").dt.start_time
    if grain == "month":
        return dt.dt.to_period("M").dt.start_time
    raise ValueError("grain must be day, week, or month")


def _suggest_control_columns(df: pd.DataFrame, excluded: set[str]) -> list[str]:
    tokens=("promo","promotion","holiday","price","discount","distribution","competitor","season","weather","inventory","availability","index")
    out=[]
    for c in df.columns:
        if c in excluded:
            continue
        n=_norm(c)
        if any(t in n for t in tokens):
            numeric=pd.to_numeric(df[c],errors="coerce")
            if numeric.notna().mean() >= .8:
                out.append(c)
    return out


def build_mmm_dataset(
    sources: Iterable[dict[str, Any]],
    *,
    grain: str = "week",
    outcome_source: str | None = None,
    outcome_role: str = "revenue",
    fill_missing_media_zero: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a question-ready MMM table from separate media and outcome sources.

    `sources` items: {name, df, kind?, mapping?}. Media sources are normalized first.
    Missing media periods remain missing by default; zero-fill is opt-in and disclosed.
    """
    built: list[pd.DataFrame] = []
    source_reports: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    media_names: list[str] = []
    outcome_frames: list[tuple[str, pd.DataFrame]] = []
    built_controls: list[str] = []
    for src in sources:
        name = str(src.get("name") or f"source_{len(source_reports)+1}")
        df = src.get("df")
        if not isinstance(df, pd.DataFrame):
            blockers.append(f"{name}: no DataFrame was supplied.")
            continue
        kind = src.get("kind") or detect_source(df, name)["kind"]
        mapping = src.get("mapping") or {}
        sm = suggest_mapping(df, kind)
        mp = dict(sm["mapping"]); mp.update(mapping)
        if kind in {"meta_ads", "google_ads", "media_export"} or ("spend" in mp and kind != "sales"):
            norm, rep = normalize_ad_export(df, platform=name, mapping=mp)
            source_reports.append({"name": name, **rep.to_dict()})
            if rep.blockers:
                blockers.extend([f"{name}: {x}" for x in rep.blockers])
                continue
            norm["period"] = _periodize(norm["date"], grain)
            agg = norm.groupby("period", as_index=False)["spend"].sum(min_count=1)
            col = _norm(name) + "_spend"
            agg = agg.rename(columns={"spend": col})
            built.append(agg); media_names.append(col)
        else:
            date_col = mapping.get("date") or mp.get("date")
            out_col = mapping.get(outcome_role) or mp.get(outcome_role)
            if not date_col or date_col not in df or not out_col or out_col not in df:
                source_reports.append({"name": name, "kind": kind, "status": "blocked", "message": f"Could not map date + {outcome_role}."})
                blockers.append(f"{name}: could not map date + {outcome_role}.")
                continue
            x = pd.DataFrame({"period": _periodize(df[date_col], grain), outcome_role: pd.to_numeric(df[out_col], errors="coerce")})
            if x[outcome_role].isna().any():
                warnings.append(f"{name}: some {outcome_role} values are missing/non-numeric.")
            explicit_controls=list(src.get("controls") or [])
            auto_controls=_suggest_control_columns(df,{date_col,out_col})
            control_cols=[]
            for c in [*explicit_controls,*auto_controls]:
                if c in df and c not in control_cols:
                    control_cols.append(c)
                    x[c]=pd.to_numeric(df[c],errors="coerce")
            agg_spec={outcome_role: lambda z: z.sum(min_count=1)}
            for c in control_cols:
                vals=x[c].dropna()
                is_binary=bool(len(vals) and set(pd.unique(vals)).issubset({0,1}))
                agg_spec[c]="max" if is_binary else "mean"
            x=x.groupby("period",as_index=False).agg(agg_spec)
            outcome_frames.append((name, x))
            built_controls.extend([c for c in control_cols if c not in built_controls])
            control_note={c:("max within period" if str(agg_spec[c])=="max" else "mean within period") for c in control_cols}
            source_reports.append({"name": name, "kind": kind, "status": "ready", "mapping": {"date": date_col, outcome_role: out_col}, "controls": control_cols, "control_aggregation": control_note, "rows_out": len(x)})
    if outcome_source:
        outcome_frames = [x for x in outcome_frames if x[0] == outcome_source]
    if len(outcome_frames) != 1:
        blockers.append("CampaignLab needs exactly one explicitly resolved outcome source for an MMM build.")
    if not media_names:
        blockers.append("No usable media spend sources were built.")
    if blockers:
        return pd.DataFrame(), {"status": "blocked", "blockers": blockers, "warnings": warnings, "sources": source_reports}
    result = outcome_frames[0][1].copy()
    for b in built:
        result = result.merge(b, on="period", how="left")
    media_missing = {c: int(result[c].isna().sum()) for c in media_names}
    for c, nmiss in media_missing.items():
        if nmiss:
            if fill_missing_media_zero:
                result[c] = result[c].fillna(0)
                warnings.append(f"{c}: {nmiss} outcome periods lacked rows in the source and were explicitly zero-filled by request.")
            else:
                warnings.append(f"{c}: {nmiss} outcome periods are missing. CampaignLab preserved them as unknown rather than assuming zero spend.")
    if result["period"].duplicated().any():
        blockers.append("Builder produced duplicate periods, which should never happen after aggregation.")
    status = "blocked" if blockers else ("caution" if warnings else "ready")
    return result.sort_values("period").reset_index(drop=True), {
        "status": status,
        "grain": grain,
        "outcome": outcome_role,
        "outcome_source": outcome_frames[0][0],
        "media_columns": media_names,
        "control_columns": built_controls,
        "missing_media_periods": media_missing,
        "warnings": warnings,
        "blockers": blockers,
        "sources": source_reports,
        "philosophy": "Map what is obvious, preserve what is unknown, ask only when ambiguity changes the analysis.",
    }


def understand_source(df: pd.DataFrame, name: str = "") -> dict[str, Any]:
    """Return a compact, deterministic explanation of what CampaignLab understands.

    This is deliberately not an LLM step. It is a semantic/schema summary used by the
    UI before any analytical method is selected. It should infer the obvious, surface
    consequential ambiguity, and preserve unknowns instead of inventing values.
    """
    detected = detect_source(df, name)
    kind = detected["kind"]
    suggested = suggest_mapping(df, kind)
    mapping = suggested["mapping"]
    ambiguous = suggested["ambiguous"]

    rows = int(len(df))
    cols = int(len(df.columns))
    source_labels = {
        "ga4_events": "GA4-like behavioral events",
        "meta_ads": "Meta Ads-like media export",
        "google_ads": "Google Ads-like media export",
        "sales": "Sales / commerce outcomes",
        "media_export": "Media performance export",
        "generic": "General analytics dataset",
    }

    evidence = []
    for role in ("date", "event", "user", "session", "campaign", "spend", "impressions", "clicks", "conversions", "revenue"):
        if role in mapping:
            evidence.append({"role": role, "column": mapping[role]})

    safe_actions: list[str] = []
    if "date" in mapping:
        safe_actions.append("Parse and validate the time field before time-based analysis.")
    if kind in {"meta_ads", "google_ads"} or "spend" in mapping:
        safe_actions.append("Standardize observed media metrics without treating platform-attributed revenue as incrementality.")
    if kind == "ga4_events" and "event" in mapping:
        safe_actions.append("Build user- or session-level funnels from event sequences when identity fields are available.")
    if kind == "sales" and "revenue" in mapping:
        safe_actions.append("Aggregate outcomes to a defensible business grain before joining to media or experiments.")

    questions: list[str] = []
    for role, candidates in ambiguous.items():
        if role in {"revenue", "spend", "date", "event", "user", "session"}:
            questions.append(f"Confirm which field should represent {role}: {', '.join(map(str, candidates[:5]))}.")
    if suggested["missing_required"]:
        questions.append("CampaignLab is missing a required field for the detected source: " + ", ".join(suggested["missing_required"]) + ".")

    cautions: list[str] = []
    if rows >= 500_000:
        cautions.append("This is large enough that a warehouse/SQL connector with query pushdown is preferable to moving raw rows through the app.")
    if kind == "ga4_events":
        cautions.append("Event exports are evidence streams, not ready-made funnels. Session/user definitions and event order matter.")
    if "spend" in mapping and "revenue" in mapping:
        cautions.append("Observed spend and revenue in the same table do not, by themselves, establish incrementality.")

    return {
        "source_kind": kind,
        "source_label": source_labels.get(kind, source_labels["generic"]),
        "confidence": detected["confidence"],
        "rows": rows,
        "columns": cols,
        "mapping": mapping,
        "evidence": evidence,
        "ambiguous": ambiguous,
        "missing_required": suggested["missing_required"],
        "safe_actions": safe_actions,
        "questions": questions,
        "cautions": cautions,
        "philosophy": "Infer the obvious. Ask only when ambiguity changes the analysis. Preserve unknowns rather than manufacture certainty.",
    }
