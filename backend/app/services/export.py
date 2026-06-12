"""Formulation export to CSV and PDF (Export Formulation Report use case).

The "formulation detail & export" frontend page/screen calls these to let a farmer
keep or share a ration sheet.
"""

from __future__ import annotations

import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.formulation import FormulationDetail


def formulation_to_csv(detail: FormulationDetail) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Formulation report"])
    writer.writerow(["Formulation ID", detail.formulation_id])
    writer.writerow(["Flock ID", detail.flock_id])
    writer.writerow(["Method", detail.generated_by.value])
    writer.writerow(["Total cost (RWF/kg)", round(detail.total_cost_per_kg_rwf, 2)])
    writer.writerow(["DTSI score", round(detail.dtsi_score, 6)])
    if detail.cosine_distance is not None:
        writer.writerow(["Cosine distance", round(detail.cosine_distance, 6)])
    writer.writerow([])
    writer.writerow(["Ingredient", "Proportion (%)"])
    for item in detail.ingredients:
        writer.writerow([item.ingredient_name, round(item.proportion_percent, 4)])
    return buf.getvalue().encode("utf-8")


def formulation_to_pdf(detail: FormulationDetail) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Formulation {detail.formulation_id}",
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Poultry Feed Formulation Report", styles["Title"]),
        Spacer(1, 6 * mm),
    ]

    summary = [
        ["Formulation ID", str(detail.formulation_id)],
        ["Flock ID", str(detail.flock_id)],
        ["Method", detail.generated_by.value],
        ["Total cost (RWF/kg)", f"{detail.total_cost_per_kg_rwf:.2f}"],
        ["DTSI score", f"{detail.dtsi_score:.6f}"],
    ]
    if detail.cosine_distance is not None:
        summary.append(["Cosine distance", f"{detail.cosine_distance:.6f}"])
    summary.append(["Selected (active ration)", "Yes" if detail.is_selected else "No"])

    summary_table = Table(summary, colWidths=[60 * mm, 90 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.extend([summary_table, Spacer(1, 8 * mm)])
    elements.append(Paragraph("Ration composition", styles["Heading2"]))

    rows = [["Ingredient", "Proportion (%)"]]
    rows.extend(
        [item.ingredient_name, f"{item.proportion_percent:.3f}"]
        for item in detail.ingredients
    )
    comp_table = Table(rows, colWidths=[100 * mm, 50 * mm])
    comp_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(comp_table)

    doc.build(elements)
    return buf.getvalue()
