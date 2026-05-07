from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import io
from utils import format_time

class PDFExporter:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle('CustomTitle', parent=self.styles['h1'], fontSize=24, spaceAfter=30, alignment=TA_CENTER, textColor=colors.HexColor('#2E86AB'))
        self.subtitle_style = ParagraphStyle('CustomSubtitle', parent=self.styles['h2'], fontSize=18, spaceAfter=20, textColor=colors.HexColor('#A23B72'))
        self.header_style = ParagraphStyle('CustomHeader', parent=self.styles['h3'], fontSize=14, spaceAfter=12, textColor=colors.HexColor('#F18F01'))
        self.normal_style = ParagraphStyle('CustomNormal', parent=self.styles['Normal'], fontSize=11, spaceAfter=8)
        self.highlight_style = ParagraphStyle('Highlight', parent=self.styles['Normal'], fontSize=11, textColor=colors.HexColor('#C73E1D'), spaceAfter=8)

    def generate_report(self, username, period, study_data, expense_data, task_data):
        """Generate a consolidated PDF report for all user data."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        story = []

        # --- Header ---
        story.append(Paragraph("⏏︎ Elevate - Consolidated Report", self.title_style))
        header_info = f"<b>User:</b> {username}<br/><b>Report Period:</b> {period}<br/><b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}"
        story.append(Paragraph(header_info, self.normal_style))
        story.append(Spacer(1, 30))

        # --- Study Report Section ---
        story.extend(self._create_study_report(study_data))
        
        # --- Expense Report Section ---
        story.append(PageBreak())
        story.extend(self._create_expense_report(expense_data))

        # --- Task Report Section ---
        story.append(PageBreak())
        story.extend(self._create_task_report(task_data))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_study_report(self, study_data):
        """Create the study report section with a table."""
        story = [Paragraph("🎓 Study Report", self.subtitle_style)]
        if study_data.empty:
            story.append(Paragraph("No study data available for this period.", self.normal_style))
            return story

        # Create table data
        table_data = [['Date', 'Subject', 'Chapter/Topic', 'Duration', 'Confidence']]
        for _, row in study_data.iterrows():
            chapter_text = str(row['chapter'])
            table_data.append([
                row['date'].strftime('%Y-%m-%d'),
                row['subject'],
                chapter_text[:25] + '...' if len(chapter_text) > 25 else chapter_text,
                f"{int(row['duration_minutes'])} min",
                f"{int(row['confidence_rating'])}/5"
            ])

        # Create and style the table
        table = Table(table_data, colWidths=[1*inch, 1.2*inch, 1.8*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
        return story
        
    def _create_expense_report(self, expense_data):
        story = [Paragraph("💸 Expense Report", self.subtitle_style)]
        if expense_data.empty:
            story.append(Paragraph("No expense data available for this period.", self.normal_style))
            return story

        total_spent = expense_data['amount'].sum()
        summary_text = f"• <b>Total Spent:</b> ₹{total_spent:,.2f}<br/>• <b>Total Transactions:</b> {len(expense_data)}"
        story.append(Paragraph(summary_text, self.normal_style))
        story.append(Spacer(1, 20))

        story.append(Paragraph("Recent Expenses", self.header_style))
        table_data = [['Date', 'Category', 'Description', 'Amount']]
        for _, row in expense_data.tail(15).iterrows():
            # Ensure 'description' is a string before slicing
            description_text = str(row['description'])
            table_data.append([
                row['date'].strftime('%Y-%m-%d'), 
                row['category'], 
                description_text[:30] + '...' if len(description_text) > 30 else description_text, 
                f"₹{row['amount']:.2f}"
            ])
        
        table = Table(table_data, colWidths=[1*inch, 1.2*inch, 2.2*inch, 1*inch])
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        story.append(table)
        return story

    def _create_task_report(self, task_data):
        story = [Paragraph("✅ Task Report", self.subtitle_style)]
        if task_data.empty:
            story.append(Paragraph("No task data available for this period.", self.normal_style))
            return story
        
        completed = task_data[task_data['status'] == 'Completed'].shape[0]
        total = len(task_data)
        completion_rate = completed / total if total > 0 else 0
        summary_text = f"• <b>Completion Rate:</b> {completion_rate:.1%}<br/>• <b>Pending Tasks:</b> {total - completed} out of {total}"
        story.append(Paragraph(summary_text, self.normal_style))
        story.append(Spacer(1, 20))

        story.append(Paragraph("Pending Tasks", self.header_style))
        table_data = [['Deadline', 'Title', 'Status']]
        for _, row in task_data[task_data['status'] == 'Pending'].tail(15).iterrows():
            # Ensure 'title' is a string before slicing
            title_text = str(row['title'])
            table_data.append([
                row['deadline'].strftime('%Y-%m-%d'), 
                title_text[:40] + '...' if len(title_text) > 40 else title_text, 
                row['status']
            ])
        
        table = Table(table_data, colWidths=[1*inch, 3.5*inch, 1*inch])
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        story.append(table)
        return story

