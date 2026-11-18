import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as file:
        return {row.pop("case"): {key: float(value) for key, value in row.items()}
                for row in csv.DictReader(file)}


def present_value(amount, rate, years):
    return amount / (1 + rate) ** years


def discounted_flows(flows, times, rate):
    return sum(present_value(flow, rate, time) for flow, time in zip(flows, times, strict=True))


def valuation(data, wacc, terminal, method="growth", *, midyear=True, stub=1.0, terminal_nwc=False):
    """Return the separate PV and EV-to-equity bridge, in USD millions."""
    if not 0 < stub <= 1 or wacc <= -1 or data["shares"] <= 0:
        raise ValueError("Invalid timing, discount rate or share count")
    flows = [data[f"forecast_{year}"] for year in range(2025, 2030)]
    flows[0] *= stub
    times = [stub / 2 if midyear else stub]
    times += [stub + i - (0.5 if midyear else 0) for i in range(1, 5)]
    forecast_pv = discounted_flows(flows, times, wacc)
    if method == "growth":
        if not -1 < terminal < wacc:
            raise ValueError("Perpetuity growth must be above -100% and below WACC")
        base_fcf = data["terminal_fcf"]
        if terminal_nwc:
            # The exhibit uses 14% of the change in revenue for terminal working capital.
            midpoint = (data["growth_lo"] + data["growth_hi"]) / 2
            base_fcf += 0.14 * data["terminal_revenue"] * (midpoint - terminal)
        terminal_value = base_fcf * (1 + terminal) / (wacc - terminal)
        terminal_pv = terminal_value / (1 + wacc) ** times[-1]
    elif method == "multiple":
        if terminal < 0:
            raise ValueError("Exit multiple must be nonnegative")
        terminal_value = terminal * data["terminal_ebitda"]
        terminal_pv = terminal_value / (1 + wacc) ** (stub + 4)
    else:
        raise ValueError(f"Unknown terminal method {method}")
    ev = forecast_pv + terminal_pv
    equity = ev + data["cash"] - data["debt"]
    return dict(forecast_pv=forecast_pv, terminal_value=terminal_value,
                terminal_pv=terminal_pv, enterprise=ev, equity=equity,
                price=equity / data["shares"])


def endpoints(data, method, **options):
    axis = "growth" if method == "growth" else "multiple"
    low = valuation(data, data["wacc_hi"], data[f"{axis}_lo"], method, **options)
    high = valuation(data, data["wacc_lo"], data[f"{axis}_hi"], method, **options)
    return [low["price"], high["price"]]


def rounded(value):
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return round(value, 8)


def report(cases, checks):
    result = {}
    for case, data in cases.items():
        midpoint = (data["growth_lo"] + data["growth_hi"]) / 2
        scenarios = {
            "baseline": endpoints(data, "growth"),
            "final_year_fcf": endpoints(dict(data, terminal_fcf=data["forecast_2029"]), "growth"),
            "year_end": endpoints(data, "growth", midyear=False),
            "nine_month_stub": endpoints(data, "growth", stub=0.75),
            "march_net_debt": endpoints(dict(data, cash=197, debt=253), "growth"),
            "alternate_shares": endpoints(dict(data, shares=94.5 if case == "A" else 95), "growth"),
            "exit_multiple": endpoints(data, "multiple"),
            "working_capital_exploratory": endpoints(data, "growth", terminal_nwc=True),
        }
        actual = [checks[case]["adviser_low"], checks[case]["adviser_high"]]
        result[case] = dict(published=actual, ranges=scenarios,
                            gaps=[x-y for x, y in zip(scenarios["baseline"], actual)],
                            midpoint_bridge=valuation(data, 0.115, midpoint))
    return rounded(result)


def cross_deal_report(inputs, checks):
    result = {}
    for check in checks:
        target = check["target"]
        published = [float(check["adviser_low"]), float(check["adviser_high"])]
        row = {"published": published}
        data = inputs.get(target)
        if data is not None and "flows" in data:
            scenarios = {"baseline": [], "alternate_forecast_timing": [], "alternate_terminal_timing": []}
            for wacc, assumption in zip(reversed(data["wacc"]), data["terminal"], strict=True):
                base = data["terminal_base"]
                term = (base * (1 + assumption) / (wacc - assumption)
                        if data["method"] == "growth" else base * assumption)
                timing = (
                    ("baseline", data["times"], data["terminal_time"]),
                    ("alternate_forecast_timing", data["alternate_times"], data["terminal_time"]),
                    ("alternate_terminal_timing", data["times"], data["alternate_terminal_time"]),
                )
                for scenario, times, terminal_time in timing:
                    forecast_pv = discounted_flows(data["flows"], times, wacc)
                    terminal_pv = present_value(term, wacc, terminal_time)
                    equity = forecast_pv + terminal_pv + data["bridge"]
                    scenarios[scenario].append(equity / data["shares"])
            row.update(scenarios)
            row["gaps"] = [model - external for model, external in zip(scenarios["baseline"], published)]
        elif data is not None:
            row["terminal_enterprise_value_usd_m"] = [
                data["terminal_base"] * multiple for multiple in data["terminal"]
            ]
            if "terminal_time" in data:
                row["discounted_terminal_ev_usd_m"] = [
                    present_value(amount, rate, data["terminal_time"])
                    for amount, rate in zip(row["terminal_enterprise_value_usd_m"], reversed(data["wacc"]))
                ]
        result[target] = row
    return rounded(result)


def chart(cases, checks):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="448" viewBox="0 0 920 448" role="img">',
             '<title>TaskUs implied value by WACC and terminal growth</title>',
             '<desc>Two heatmaps share a color scale of 4 to 21 U.S. dollars per share. A line marks the 16.50 dollar offer in Case A.</desc>',
             '<rect width="920" height="448" fill="#fcfbf7"/>',
             '<g font-family="Arial,sans-serif" fill="#172a36">',
             '<text x="38" y="43" font-size="26" font-weight="bold">TaskUs DCF sensitivity</text>',
             '<text x="38" y="68" font-size="14">USD per share · Evercore inputs rounded as disclosed · white line = $16.50 offer</text>']
    n = 36
    cell = 7
    top = 114
    for panel, (case, data) in enumerate(cases.items()):
        left = 103 + panel * 450
        parts.append(f'<text x="{left}" y="101" font-size="16" font-weight="bold">Case {html.escape(case)}</text>')
        offer = checks[case]["offer"]
        for row in range(n):
            wacc = data["wacc_lo"] + (data["wacc_hi"] - data["wacc_lo"]) * (row + .5) / n
            for col in range(n):
                growth = data["growth_lo"] + (data["growth_hi"] - data["growth_lo"]) * (col + .5) / n
                price = valuation(data, wacc, growth)["price"]
                q = max(0, min((price - 4) / 17, 1))
                color = f"rgb({int(224 - 200*q)},{int(240 - 145*q)},{int(239 - 122*q)})"
                parts.append(f'<rect x="{left+cell*col}" y="{top+cell*row}" width="{cell}" height="{cell}" fill="{color}"/>')
        points = []
        for row in range(n * 4 + 1):
            frac = row / (n * 4)
            rate = data["wacc_lo"] + frac * (data["wacc_hi"] - data["wacc_lo"])
            at_zero = valuation(data, rate, 0)
            required = (offer * data["shares"] - at_zero["forecast_pv"] - data["cash"] + data["debt"])
            required *= (1 + rate) ** 4.5
            growth = (required * rate - data["terminal_fcf"]) / (required + data["terminal_fcf"])
            xfrac = (growth - data["growth_lo"]) / (data["growth_hi"] - data["growth_lo"])
            if 0 <= xfrac <= 1:
                points.append(f"{left+cell*n*xfrac:.2f},{top+cell*n*frac:.2f}")
        if points:
            parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#102633" stroke-width="4"/>')
            parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="white" stroke-width="2"/>')
        else:
            parts.append(f'<text x="{left+5}" y="{top+20}" font-size="13">Offer above displayed values</text>')
        for frac in (0, 0.5, 1):
            g = data["growth_lo"] + frac * (data["growth_hi"] - data["growth_lo"])
            w = data["wacc_lo"] + frac * (data["wacc_hi"] - data["wacc_lo"])
            parts.append(f'<text x="{left+cell*n*frac}" y="{top+cell*n+18}" text-anchor="middle" font-size="13">{g:.1%}</text>')
            parts.append(f'<text x="{left-8}" y="{top+cell*n*frac+4}" text-anchor="end" font-size="13">{w:.1%}</text>')
        parts.append(f'<text x="{left+cell*n/2}" y="412" text-anchor="middle" font-size="14">Terminal growth</text>')
        parts.append(f'<text x="{left-60}" y="242" text-anchor="middle" font-size="14">WACC</text>')
    parts.append('<text x="38" y="435" font-size="12">Shared color scale · pale ≈ $4 · dark ≈ $21</text></g></svg>')
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    cases = read("inputs.csv")
    checks = read("checks.csv")
    (ROOT / "heatmap.svg").write_text(chart(cases, checks), encoding="utf-8")
    results = json.dumps(report(cases, checks), indent=2) + "\n"
    (ROOT / "results.json").write_text(results, encoding="utf-8")
    print(results, end="")
    cross_inputs = json.loads((ROOT / "cross_inputs.json").read_text(encoding="utf-8"))
    with (ROOT / "cross_checks.csv").open(newline="", encoding="utf-8") as file:
        cross_results = cross_deal_report(cross_inputs, csv.DictReader(file))
    (ROOT / "cross_deal.json").write_text(json.dumps(cross_results, indent=2) + "\n", encoding="utf-8")
