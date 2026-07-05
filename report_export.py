from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from grader import SheetResult


def build_report_rows(result: SheetResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in result.question_results:
        rows.append(
            {
                "Question ID": item.qid,
                "Status": item.status,
                "Points Earned": item.points_earned,
                "Points Possible": item.points_possible,
                "Feedback": item.feedback,
            }
        )
    return rows


def sheet_result_to_csv_bytes(result: SheetResult) -> bytes:
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "Question ID",
            "Status",
            "Points Earned",
            "Points Possible",
            "Feedback",
        ],
    )
    writer.writeheader()
    for row in build_report_rows(result):
        writer.writerow(row)

    output.write("\n")
    output.write(f"Correct,{result.correct_count}\n")
    output.write(f"Incorrect,{result.incorrect_count}\n")
    output.write(f"Unattempted,{result.unattempted_count}\n")
    output.write(f"Question issue,{result.question_issue_count}\n")
    output.write(f"Strict score,{result.score_correct}/{result.score_possible_strict}\n")
    output.write(
        "Adjusted score,"
        f"{result.score_correct}/{result.score_possible_excluding_issues}\n"
    )

    return output.getvalue().encode("utf-8")


def sheet_result_to_pdf_bytes(result: SheetResult) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Math Worksheet Grading Report")

    y -= 24
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Correct: {result.correct_count}")
    y -= 14
    pdf.drawString(40, y, f"Incorrect: {result.incorrect_count}")
    y -= 14
    pdf.drawString(40, y, f"Unattempted: {result.unattempted_count}")
    y -= 14
    pdf.drawString(40, y, f"Question issue: {result.question_issue_count}")
    y -= 14
    pdf.drawString(
        40,
        y,
        f"Strict score: {result.score_correct}/{result.score_possible_strict}",
    )
    y -= 14
    pdf.drawString(
        40,
        y,
        "Adjusted score: "
        f"{result.score_correct}/{result.score_possible_excluding_issues}",
    )

    y -= 24
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Question Details")
    y -= 16

    pdf.setFont("Helvetica", 9)
    for row in build_report_rows(result):
        text = (
            f"{row['Question ID']} | {row['Status']} | "
            f"{row['Points Earned']}/{row['Points Possible']}"
        )
        feedback = row["Feedback"]

        for line in [text, f"Feedback: {feedback}"]:
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 9)
                y = height - 50
            pdf.drawString(40, y, line[:130])
            y -= 12

        y -= 6

    pdf.save()
    return buffer.getvalue()
