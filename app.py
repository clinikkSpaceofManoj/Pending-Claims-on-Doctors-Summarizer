import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

st.set_page_config(page_title="Pending on Doctors – Enhanced", layout="centered")

st.title("📄 Pending on Doctors – Enhanced PDF Generator")

# ----------------------------
# Upload file
# ----------------------------
uploaded_file = st.file_uploader("Upload OPD Claims Excel (.xlsx)", type=["xlsx"])

pending_threshold = st.number_input(
    "Highlight claims pending more than X days",
    min_value=1, max_value=365,
    value=30, step=1
)

if uploaded_file:
    # ----------------------------
    # Load Excel
    # ----------------------------
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # ----------------------------
    # Filter only in-progress claims
    # ----------------------------
    df = df[df["claimStatus"].str.lower() == "in progress"]

    # ----------------------------
    # Compute days since updated
    # ----------------------------
    df["last_updated_at"] = pd.to_datetime(df["last_updated_at"])
    today = pd.Timestamp(datetime.today().date())
    df["days_since_updated"] = (today - df["last_updated_at"]).dt.days

    df = df[["assigned_to_doctor", "claim_id", "days_since_updated"]]

    df = df.sort_values(by=["assigned_to_doctor", "days_since_updated"], ascending=[True, False])

    st.success("File processed successfully!")

    # ----------------------------
    # Summary Table (count per doctor)
    # ----------------------------
    summary_df = df.groupby("assigned_to_doctor").agg(
        total_claims=("claim_id", "count"),
        overdue_claims=("days_since_updated", lambda x: (x > pending_threshold).sum())
    ).reset_index()

    st.subheader("📊 Summary (Doctor-wise)")
    st.dataframe(summary_df, use_container_width=True)

    # ----------------------------
    # PDF Generator
    # ----------------------------
    def generate_pdf(dataframe, summarydata):
        buffer = BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=A4)

        styles = getSampleStyleSheet()
        story = []

        # PDF Title
        title = Paragraph("<b>Pending on Doctors – Report</b>", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 12))

        # Summary Section
        story.append(Paragraph("<b>Summary Overview</b>", styles["Heading2"]))
        summary_table_data = [
            ["Doctor", "Total Claims", f"Pending > {pending_threshold} days"]
        ]

        for _, row in summarydata.iterrows():
            summary_table_data.append([
                row["assigned_to_doctor"],
                row["total_claims"],
                row["overdue_claims"]
            ])

        summary_table = Table(summary_table_data, colWidths=[150, 100, 150])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Doctor-wise Details
        for doctor, group in dataframe.groupby("assigned_to_doctor"):
            story.append(Paragraph(f"<b>{doctor}</b>", styles["Heading3"]))
            story.append(Spacer(1, 8))

            table_data = [["Claim ID", "Days since updated"]]

            for _, row in group.iterrows():
                days = row["days_since_updated"]
                if days > pending_threshold:
                    table_data.append(
                        [row["claim_id"], f"{days} ⚠️"]  # Highlight
                    )
                else:
                    table_data.append([row["claim_id"], days])

            table = Table(table_data, colWidths=[120, 130])

            table_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ])

            # Highlight overdue rows
            for i, row in enumerate(table_data[1:], start=1):
                if "⚠️" in str(row[1]):
                    table_style.add("BACKGROUND", (0, i), (-1, i), colors.lightpink)

            table.setStyle(table_style)
            story.append(table)
            story.append(Spacer(1, 20))

        pdf.build(story)
        buffer.seek(0)
        return buffer

    pdf_output = generate_pdf(df, summary_df)

    # ----------------------------
    # Download Button
    # ----------------------------
    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_output,
        file_name="pending_on_doctors.pdf",
        mime="application/pdf"
    )

    with st.expander("🔍 Preview Processed Data"):
        st.dataframe(df, use_container_width=True)
