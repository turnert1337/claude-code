#!/usr/bin/env python3
"""Render the Oahu/Lowell decision brief as a phone-readable HTML email.

Reads state.json, emits HTML on stdout. Designed for a 30-second scan:
verdict first, deltas second, sources one tap away.
"""
import json, sys, os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CENTRAL = timezone(timedelta(hours=-5))  # CDT

VERDICT_STYLE = {
    "GO":        ("#0f7b3f", "#e7f5ec", "GO"),
    "REASSESS":  ("#b45309", "#fdf3e3", "REASSESS"),
    "DONT GO":   ("#b91c1c", "#fdeaea", "DON'T GO"),
}
FLAG_DOT = {"ok": "#0f7b3f", "watch": "#b45309", "bad": "#b91c1c"}
TREND = {
    "better": ("&#9650;", "#0f7b3f", "improving"),
    "worse":  ("&#9660;", "#b91c1c", "deteriorating"),
    "flat":   ("&#9654;", "#8a8a85", "steady"),
}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(state):
    r = state["readings"][-1]
    trip = state["trip"]
    color, bg, label = VERDICT_STYLE.get(r["verdict"], VERDICT_STYLE["REASSESS"])

    ts = datetime.fromisoformat(r["ts_utc"].replace("Z", "+00:00")).astimezone(CENTRAL)
    stamp = ts.strftime("%-I:%M%p CT").lower().replace("am", "a").replace("pm", "p")

    prev = r.get("prev_verdict")
    if prev is None:
        change = "First brief. This is your baseline."
        change_color = "#8a8a85"
    elif prev == r["verdict"]:
        change = f"No change. Still {label}."
        change_color = "#8a8a85"
    else:
        change = f"CHANGED: {prev} &rarr; {label}"
        change_color = color

    rows = []
    for d in r["datapoints"]:
        arrow, tcolor, _ = TREND.get(d.get("trend", "flat"), TREND["flat"])
        dot = FLAG_DOT.get(d.get("flag", "ok"), "#8a8a85")
        rows.append(f"""
      <tr><td style="padding:14px 0 0 0;border-top:1px solid #ececea;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="font:600 15px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111;">
            <span style="display:inline-block;width:7px;height:7px;border-radius:7px;background:{dot};margin-right:7px;vertical-align:middle;"></span>{esc(d['label'])}
          </td>
          <td align="right" style="font:600 15px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111;white-space:nowrap;">
            {esc(d['value'])} <span style="color:{tcolor};font-size:13px;">{arrow}</span>
          </td>
        </tr></table>
        <div style="font:400 13px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#5f5f5a;padding:3px 0 12px 14px;">
          {esc(d['detail'])}
        </div>
      </td></tr>""")

    links = "".join(
        f'<a href="{esc(s["url"])}" style="display:inline-block;background:#fff;border:1px solid #d8d8d4;'
        f'border-radius:6px;padding:9px 13px;margin:0 6px 8px 0;font:600 13px -apple-system,BlinkMacSystemFont,sans-serif;'
        f'color:#1a1a17;text-decoration:none;">{esc(s["label"])}</a>'
        for s in r["sources"]
    )

    return f"""<div style="margin:0;padding:0;background:#f5f5f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f4;">
<tr><td align="center" style="padding:16px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:480px;background:#ffffff;border-radius:12px;border:1px solid #e4e4e0;">

  <tr><td style="background:{bg};border-radius:11px 11px 0 0;padding:18px 20px;border-bottom:1px solid {color}22;">
    <div style="font:800 30px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:{color};letter-spacing:-0.5px;">{label}</div>
    <div style="font:400 14px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#3d3d38;padding-top:6px;">{esc(r['verdict_reason'])}</div>
  </td></tr>

  <tr><td style="padding:11px 20px;background:#fafaf9;border-bottom:1px solid #ececea;">
    <span style="font:600 13px -apple-system,BlinkMacSystemFont,sans-serif;color:{change_color};">{change}</span>
    <span style="font:400 12px -apple-system,BlinkMacSystemFont,sans-serif;color:#9a9a95;"> &middot; {stamp} &middot; #{r['n']}</span>
  </td></tr>

  <tr><td style="padding:2px 20px 16px 20px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{''.join(rows)}</table>
  </td></tr>

  <tr><td style="padding:0 20px 18px 20px;">
    <div style="background:#fbf7ed;border-left:3px solid #b45309;border-radius:0 6px 6px 0;padding:12px 14px;">
      <div style="font:700 11px -apple-system,BlinkMacSystemFont,sans-serif;color:#b45309;letter-spacing:0.7px;padding-bottom:5px;">THE $4,800</div>
      <div style="font:400 13px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;color:#3d3d38;">{esc(r['money_note'])}</div>
    </div>
  </td></tr>

  <tr><td style="padding:0 20px 8px 20px;">{links}</td></tr>

  <tr><td style="padding:12px 20px 18px 20px;border-top:1px solid #ececea;">
    <div style="font:400 11px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;color:#9a9a95;">
      {esc(trip['destination'])} &middot; {esc(trip['airline'])} {esc(trip['departure_local'])} &middot; ${trip['nonrefundable']:,} nonrefundable {esc(trip['nonrefundable_item'])}<br>
      Booked {esc(trip['booked'])}
    </div>
  </td></tr>

</table>
</td></tr></table>
</div>"""


if __name__ == "__main__":
    with open(os.path.join(HERE, "state.json")) as f:
        sys.stdout.write(render(json.load(f)))
