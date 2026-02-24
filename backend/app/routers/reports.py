from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import StringIO, BytesIO
import csv
from datetime import datetime

from app.routers.analytics import (
    get_summary,
    get_follower_growth,
    get_content_types,
    get_trend_prediction,
)
from app.routers.competitors import (
    compare_competitors,
    competitor_growth,
    get_gaps,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _draw_panel(pdf, x, y, width, height, title):
    from reportlab.lib import colors

    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.setFillColor(colors.HexColor("#F9FAFB"))
    pdf.roundRect(x, y, width, height, 8, stroke=1, fill=1)
    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x + 10, y + height - 16, title)


def _draw_line_chart(pdf, x, y, width, height, values, line_color="#4F46E5"):
    from reportlab.lib import colors

    chart_x = x + 12
    chart_y = y + 24
    chart_w = width - 24
    chart_h = height - 46

    pdf.setStrokeColor(colors.HexColor("#6B7280"))
    pdf.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    pdf.line(chart_x, chart_y, chart_x + chart_w, chart_y)

    if not values:
        pdf.setFillColor(colors.HexColor("#6B7280"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(chart_x + 8, chart_y + chart_h / 2, "No data available")
        return

    low = min(values)
    high = max(values)
    if high == low:
        high = low + 1

    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.setFont("Helvetica", 7)
    pdf.drawString(chart_x - 4, chart_y - 10, str(round(low)))
    pdf.drawString(chart_x - 4, chart_y + chart_h - 2, str(round(high)))

    mid = (low + high) / 2
    mid_y = chart_y + ((mid - low) / (high - low)) * chart_h
    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.line(chart_x, mid_y, chart_x + chart_w, mid_y)
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.drawString(chart_x - 4, mid_y - 3, str(round(mid)))

    step_count = max(len(values) - 1, 1)
    x_step = chart_w / step_count

    pdf.setStrokeColor(colors.HexColor(line_color))
    pdf.setFillColor(colors.HexColor(line_color))

    prev_x = prev_y = None
    for idx, value in enumerate(values):
        px = chart_x + idx * x_step
        py = chart_y + ((_safe_float(value) - low) / (high - low)) * chart_h
        if prev_x is not None:
            pdf.line(prev_x, prev_y, px, py)
        pdf.circle(px, py, 1.8, stroke=0, fill=1)
        prev_x, prev_y = px, py


def _draw_bar_chart(pdf, x, y, width, height, labels, values, bar_color="#22C55E"):
    from reportlab.lib import colors

    chart_x = x + 12
    chart_y = y + 26
    chart_w = width - 24
    chart_h = height - 52

    pdf.setStrokeColor(colors.HexColor("#6B7280"))
    pdf.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    pdf.line(chart_x, chart_y, chart_x + chart_w, chart_y)

    if not labels or not values:
        pdf.setFillColor(colors.HexColor("#6B7280"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(chart_x + 8, chart_y + chart_h / 2, "No data available")
        return

    max_value = max([_safe_float(v) for v in values]) or 1
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.setFont("Helvetica", 7)
    pdf.drawString(chart_x - 4, chart_y - 10, "0")
    pdf.drawString(chart_x - 4, chart_y + chart_h - 2, str(round(max_value)))

    mid_value = max_value / 2
    mid_y = chart_y + (mid_value / max_value) * chart_h
    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.line(chart_x, mid_y, chart_x + chart_w, mid_y)
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.drawString(chart_x - 4, mid_y - 3, str(round(mid_value)))

    count = len(values)
    bar_w = chart_w / max(count * 1.8, 1)
    gap = bar_w * 0.8

    pdf.setFillColor(colors.HexColor(bar_color))
    for idx, value in enumerate(values):
        left = chart_x + idx * (bar_w + gap)
        h = (_safe_float(value) / max_value) * chart_h
        pdf.rect(left, chart_y, bar_w, h, stroke=0, fill=1)

        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.setFont("Helvetica", 7)
        label = str(labels[idx])
        if len(label) > 10:
            label = label[:9] + "…"
        pdf.drawCentredString(left + bar_w / 2, chart_y - 10, label)
        pdf.setFillColor(colors.HexColor(bar_color))


def _draw_multi_line_chart(pdf, x, y, width, height, series):
    from reportlab.lib import colors

    chart_x = x + 12
    chart_y = y + 24
    chart_w = width - 24
    chart_h = height - 46

    pdf.setStrokeColor(colors.HexColor("#6B7280"))
    pdf.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    pdf.line(chart_x, chart_y, chart_x + chart_w, chart_y)

    all_values = []
    max_len = 0
    for item in series:
        values = [_safe_float(p.get("followers", 0)) for p in item.get("data", [])]
        all_values.extend(values)
        max_len = max(max_len, len(values))

    if not all_values or max_len == 0:
        pdf.setFillColor(colors.HexColor("#6B7280"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(chart_x + 8, chart_y + chart_h / 2, "No data available")
        return

    low = min(all_values)
    high = max(all_values)
    if high == low:
        high = low + 1

    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.setFont("Helvetica", 7)
    pdf.drawString(chart_x - 4, chart_y - 10, str(round(low)))
    pdf.drawString(chart_x - 4, chart_y + chart_h - 2, str(round(high)))

    mid = (low + high) / 2
    mid_y = chart_y + ((mid - low) / (high - low)) * chart_h
    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.line(chart_x, mid_y, chart_x + chart_w, mid_y)
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.drawString(chart_x - 4, mid_y - 3, str(round(mid)))

    colors_cycle = ["#4F46E5", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4"]
    step_count = max(max_len - 1, 1)
    x_step = chart_w / step_count

    for idx, item in enumerate(series):
        color_hex = colors_cycle[idx % len(colors_cycle)]
        pdf.setStrokeColor(colors.HexColor(color_hex))
        pdf.setFillColor(colors.HexColor(color_hex))

        values = [_safe_float(p.get("followers", 0)) for p in item.get("data", [])]
        prev_x = prev_y = None
        for point_idx, value in enumerate(values):
            px = chart_x + point_idx * x_step
            py = chart_y + ((value - low) / (high - low)) * chart_h
            if prev_x is not None:
                pdf.line(prev_x, prev_y, px, py)
            prev_x, prev_y = px, py

        legend_x = x + width - 150
        legend_y = y + height - 16 - (idx * 12)
        pdf.rect(legend_x, legend_y, 8, 8, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.setFont("Helvetica", 8)
        name = str(item.get("name", "series"))
        if len(name) > 18:
            name = name[:17] + "…"
        pdf.drawString(legend_x + 12, legend_y + 1, name)


@router.get("/dashboard.csv")
def export_dashboard_csv() -> StreamingResponse:
    """Export key dashboard analytics as a CSV file.

    This reuses the existing analytics functions so the numbers
    match what you see in the UI.
    """
    summary = get_summary()
    followers = get_follower_growth()
    content_types = get_content_types()

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Dashboard Summary"])
    writer.writerow(["Metric", "Value"])
    for key, value in summary.items():
        writer.writerow([key, value])

    writer.writerow("")
    writer.writerow(["Follower Growth"])
    writer.writerow(["Date", "Followers"])
    for row in followers:
        writer.writerow([row["date"], row["followers"]])

    writer.writerow("")
    writer.writerow(["Content Types"])
    writer.writerow(["Content Type", "Post Count", "Avg Engagement"])
    for ct in content_types:
        writer.writerow([
            ct["content_type"],
            ct["count"],
            ct["avg_engagement"],
        ])

    buffer.seek(0)
    filename = f"dashboard-report-{datetime.now().date()}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/competitors.csv")
def export_competitors_csv() -> StreamingResponse:
    """Export competitor comparison, growth, and gaps as CSV.

    Uses the same underlying functions as the Competitors page,
    so the report matches what you see in the charts/table.
    """
    comps = compare_competitors()
    growth_series = competitor_growth()
    gaps = get_gaps()

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Competitor Snapshot"])
    writer.writerow(["Name", "Follower Count", "Avg Engagement"])
    for row in comps:
        writer.writerow([
            row["username"],
            row["follower_count"],
            row["avg_engagement"],
        ])

    writer.writerow("")
    writer.writerow(["Follower Growth Over Time"])
    writer.writerow(["Name", "Date", "Followers"])
    for series in growth_series:
        name = series["name"]
        for point in series["data"]:
            writer.writerow([name, point["date"], point["followers"]])

    writer.writerow("")
    writer.writerow(["Content Gaps"])
    writer.writerow([
        "Competitor",
        "Their Top Content",
        "Your Usage",
        "Suggested Extra Posts",
    ])
    for gap in gaps:
        writer.writerow([
            gap["competitor"],
            gap["their_top_content"],
            gap["your_usage"],
            gap["gap"],
        ])

    buffer.seek(0)
    filename = f"competitors-report-{datetime.now().date()}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dashboard.pdf")
def export_dashboard_pdf() -> StreamingResponse:
    """Generate a chart-focused dashboard PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF generation library is not installed on the server.",
        ) from exc

    summary = get_summary()
    followers = get_follower_growth()
    content_types = get_content_types()
    trend = get_trend_prediction()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - margin, "GapSight Dashboard Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - margin, height - margin, datetime.now().strftime("%Y-%m-%d %H:%M"))

    card_y = height - 120
    card_h = 50
    gap = 8
    card_w = (width - 2 * margin - (gap * 3)) / 4
    cards = [
        ("Followers", str(summary.get("follower_count", "—"))),
        ("Growth %", str(summary.get("follower_growth_pct", "—"))),
        ("Avg Engagement", str(summary.get("avg_engagement", "—"))),
        ("Top Content", str(summary.get("top_content_type", "—"))),
    ]
    for idx, (title, value) in enumerate(cards):
        x = margin + idx * (card_w + gap)
        _draw_panel(pdf, x, card_y, card_w, card_h, title)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(x + 10, card_y + 15, value)

    _draw_panel(pdf, margin, 390, width - (2 * margin), 190, "Follower Growth")
    _draw_line_chart(
        pdf,
        margin,
        390,
        width - (2 * margin),
        190,
        [row.get("followers", 0) for row in followers],
        "#4F46E5",
    )

    _draw_panel(pdf, margin, 170, width - (2 * margin), 190, "Content Mix")
    _draw_bar_chart(
        pdf,
        margin,
        170,
        width - (2 * margin),
        190,
        [row.get("content_type", "N/A") for row in content_types],
        [row.get("count", 0) for row in content_types],
        "#22C55E",
    )

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(margin, height - margin, "Trend Prediction")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - margin - 18, "Historical points plus next 4-week follower forecast")

    _draw_panel(pdf, margin, 220, width - (2 * margin), 460, "Follower Trend Forecast")
    _draw_line_chart(
        pdf,
        margin,
        220,
        width - (2 * margin),
        460,
        [row.get("followers", 0) for row in trend],
        "#F59E0B",
    )

    pdf.save()
    buffer.seek(0)
    filename = f"dashboard-report-{datetime.now().date()}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/competitors.pdf")
def export_competitors_pdf() -> StreamingResponse:
    """Generate a chart-focused competitors PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF generation library is not installed on the server.",
        ) from exc

    comps = compare_competitors()
    growth = competitor_growth()
    gaps = get_gaps()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - margin, "GapSight Competitor Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - margin, height - margin, datetime.now().strftime("%Y-%m-%d %H:%M"))

    labels = [row.get("username", "N/A") for row in comps]
    follower_values = [row.get("follower_count", 0) for row in comps]
    engagement_values = [row.get("avg_engagement", 0) for row in comps]

    _draw_panel(pdf, margin, 390, width - (2 * margin), 190, "Follower Comparison")
    _draw_bar_chart(pdf, margin, 390, width - (2 * margin), 190, labels, follower_values, "#4F46E5")

    _draw_panel(pdf, margin, 170, width - (2 * margin), 190, "Engagement Comparison")
    _draw_bar_chart(pdf, margin, 170, width - (2 * margin), 190, labels, engagement_values, "#F59E0B")

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(margin, height - margin, "Competitor Growth + Gap Snapshot")

    _draw_panel(pdf, margin, 290, width - (2 * margin), 390, "Follower Growth Over Time")
    _draw_multi_line_chart(pdf, margin, 290, width - (2 * margin), 390, growth)

    _draw_panel(pdf, margin, 80, width - (2 * margin), 180, "Top Content Gaps")
    pdf.setFont("Helvetica", 9)
    row_y = 230
    for gap in gaps[:6]:
        line = (
            f"• {gap.get('competitor', 'N/A')} | top: {gap.get('their_top_content', 'N/A')} "
            f"| your usage: {gap.get('your_usage', 0)} | gap: {gap.get('gap', 0)}"
        )
        pdf.drawString(margin + 12, row_y, line)
        row_y -= 22

    pdf.save()
    buffer.seek(0)
    filename = f"competitors-report-{datetime.now().date()}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/summary.pdf")
def export_summary_pdf() -> StreamingResponse:
    """Backward-compatible alias for the dashboard PDF."""
    return export_dashboard_pdf()
