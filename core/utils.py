from io import BytesIO
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.utils import timezone
from datetime import timedelta

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("PDF generation error", status=500)

def get_business_day():
    """
    Get current business day. If it's before 6 AM, 
    consider it part of the previous business day.
    """
    now = timezone.now()
    if now.hour < 6:
        return (now - timedelta(days=1)).date()
    return now.date()
