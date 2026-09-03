from __future__ import annotations

from typing import Iterable
from matplotlib.ticker import FuncFormatter, MaxNLocator

TEXT = "#E8EDF5"
MUTED = "#AAB4C3"
GRID = "#334155"
PANEL = "#111827"
SPINE = "#475569"

def clean_axes(ax, *, grid_axis: str | None = None) -> None:
    ax.set_facecolor(PANEL)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(SPINE); ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(length=0, pad=7, colors=MUTED)
    ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, alpha=.52, linewidth=.7); ax.set_axisbelow(True)

def finalize(fig, ax, *, title: str, subtitle: str | None = None) -> None:
    fig.patch.set_facecolor(PANEL); fig.patch.set_alpha(1)
    ax.set_facecolor(PANEL)
    ax.set_title(title, loc="left", fontsize=13, fontweight="semibold", pad=14, color=TEXT)
    if subtitle:
        ax.text(0,1.015,subtitle,transform=ax.transAxes,fontsize=9.5,color=MUTED,va="bottom")
    ax.tick_params(colors=MUTED)
    ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
    for label in list(ax.get_xticklabels())+list(ax.get_yticklabels()): label.set_color(MUTED)
    legend=ax.get_legend()
    if legend:
        legend.get_frame().set_alpha(0)
        for t in legend.get_texts(): t.set_color(TEXT)
    fig.tight_layout(pad=1.25)

def format_percent_axis(ax, *, axis: str="y", decimals: int=0) -> None:
    fmt=FuncFormatter(lambda value,_: f"{value:.{decimals}f}%")
    (ax.yaxis if axis=="y" else ax.xaxis).set_major_formatter(fmt)

def format_compact_axis(ax, *, axis: str="y") -> None:
    def _fmt(value,_):
        sign="-" if value<0 else ""; n=abs(value)
        if n>=1_000_000_000: return f"{sign}{n/1_000_000_000:.1f}B"
        if n>=1_000_000: return f"{sign}{n/1_000_000:.1f}M"
        if n>=1_000: return f"{sign}{n/1_000:.1f}K"
        return f"{value:.0f}"
    fmt=FuncFormatter(_fmt); (ax.yaxis if axis=="y" else ax.xaxis).set_major_formatter(fmt)

def integer_ticks(ax, *, axis: str="y") -> None:
    (ax.yaxis if axis=="y" else ax.xaxis).set_major_locator(MaxNLocator(integer=True))

def annotate_bars(ax, values: Iterable[float], *, horizontal: bool=False, suffix: str="", decimals: int=1) -> None:
    values=list(values)
    if horizontal:
        span=ax.get_xlim()[1]-ax.get_xlim()[0]; offset=span*.012
        for i,v in enumerate(values): ax.text(v+offset,i,f"{v:.{decimals}f}{suffix}",va="center",fontsize=9,color=TEXT)
    else:
        span=ax.get_ylim()[1]-ax.get_ylim()[0]; offset=span*.018
        for i,v in enumerate(values): ax.text(i,v+offset,f"{v:.{decimals}f}{suffix}",ha="center",va="bottom",fontsize=9,color=TEXT)
