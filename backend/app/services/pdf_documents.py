"""Shared corporate A4 layout for reports and internal sales receipts."""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, CondPageBreak

NAVY = colors.HexColor('#16364a')
TEAL = colors.HexColor('#207f87')
MUTED = colors.HexColor('#617887')
PALE = colors.HexColor('#eef5f7')
STYLES = {
    'body': ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=13,textColor=NAVY,spaceAfter=4,splitLongWords=True),
    'title': ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=NAVY,spaceAfter=12),
    'section': ParagraphStyle('section',fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=TEAL,spaceBefore=17,spaceAfter=9),
    'small': ParagraphStyle('small',fontName='Helvetica',fontSize=8,leading=11,textColor=MUTED,spaceAfter=7),
    'head': ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=colors.white),
    'amount': ParagraphStyle('amount',fontName='Helvetica',fontSize=9,leading=13,textColor=NAVY,alignment=TA_RIGHT),
}


def paragraph(value, style='body'):
    return Paragraph(escape(str(value if value is not None else '—')).replace('\n','<br/>'),STYLES[style])


def money(value, currency='PEN'):
    return f"{'S/' if currency == 'PEN' else currency} {Decimal(str(value or 0)):,.2f}"


def local_date(value):
    if not value: return '—'
    parsed = datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    return parsed.astimezone(ZoneInfo('America/Lima')).strftime('%d/%m/%Y %H:%M')


def data_table(headers, rows, widths):
    content=[[paragraph(value,'head') for value in headers]]
    content.extend([[paragraph(value) for value in row] for row in rows])
    if len(content)==1:
        content.append([paragraph('Sin registros para los filtros seleccionados.')]+['']*(len(headers)-1))
    table=Table(content,colWidths=[width*mm for width in widths],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
        ('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#dce7ec')),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    return table


def build_document(title, reference, story):
    stream=BytesIO()
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=17*mm,rightMargin=17*mm,topMargin=32*mm,bottomMargin=22*mm,
                          title=title,author='SalesIA Enterprise')
    def frame(canvas, document):
        canvas.saveState()
        width,height=A4
        canvas.setStrokeColor(TEAL);canvas.setLineWidth(2)
        canvas.line(17*mm,height-14*mm,width-17*mm,height-14*mm)
        canvas.setFillColor(NAVY);canvas.setFont('Helvetica-Bold',15)
        canvas.drawString(17*mm,height-23*mm,'SALESIA')
        canvas.setFont('Helvetica',7);canvas.setFillColor(MUTED)
        canvas.drawString(46*mm,height-23*mm,'ENTERPRISE / INTELIGENCIA COMERCIAL')
        canvas.drawRightString(width-17*mm,height-23*mm,reference)
        canvas.setStrokeColor(colors.HexColor('#dce7ec'));canvas.setLineWidth(0.5)
        canvas.line(17*mm,17*mm,width-17*mm,17*mm)
        canvas.drawString(17*mm,12*mm,'Documento de gestion interna | America/Lima')
        canvas.drawRightString(width-17*mm,12*mm,f'Pagina {document.page}')
        canvas.restoreState()
    flow=[paragraph(title,'title')]
    for item in story:
        if isinstance(item,Paragraph) and item.style.name=='section': flow.append(CondPageBreak(35*mm))
        flow.append(item)
    doc.build(flow,onFirstPage=frame,onLaterPages=frame)
    return stream.getvalue()


def report_pdf(report):
    titles={'sales':'Reporte de ventas','statistical':'Resumen estadístico','products':'Rendimiento de productos','customers':'Actividad por cliente','sellers':'Rendimiento de vendedores'}
    params=report['parameters']; summary=report['summary']; kind=report['report_type']
    story=[paragraph(f"Periodo: {params.get('start') or 'Desde el inicio'} / {params.get('end') or 'Sin fecha final'}"),
           paragraph(f"Generado: {local_date(report['generated_at'])}",'small')]
    names={'customer_id':'Cliente','employee_id':'Vendedor','product_id':'Producto','branch_id':'Sucursal'}
    filters=params.get('filters') or {}
    story.append(paragraph(' | '.join(f"{label}: {(filters.get(key) or {}).get('name','Todos')}" for key,label in names.items()),'small'))
    story += [paragraph('01 / Indicadores del periodo','section'),paragraph(f"{summary['sales_count']} ventas confirmadas; {summary['voided_count']} anuladas excluidas.")]
    for group in summary['by_currency']:
        currency=group['currency']
        story.append(data_table(['Moneda','Ingresos','Ticket promedio','Mediana'],[[currency,money(group['revenue'],currency),money(group['average_ticket'],currency),money(group['median_ticket'],currency)]],[24,56,48,48]))
        story.append(paragraph(f"Mínimo: {money(group['minimum'],currency)} | Máximo: {money(group['maximum'],currency)}",'small'))
    if not summary['by_currency']: story.append(paragraph('No hay ventas confirmadas para calcular indicadores.'))
    if kind=='sales':
        story.append(paragraph('02 / Detalle de transacciones','section'))
        rows=[[f"#{r['id']}\n{local_date(r['sold_at'])}",f"{r.get('customer') or 'Cliente general'}\n{r['seller']}",'Confirmada' if r['status']=='confirmed' else 'Anulada',money(r['total'],r['currency'])] for r in report['rows']]
        story.append(data_table(['Venta / fecha','Cliente / vendedor','Estado','Total'],rows,[39,70,25,42]))
    elif kind in {'products','customers','sellers'}:
        story.append(paragraph('02 / Resultados agrupados','section'))
        rows=[[g['name'],g['sales_count'],*([g.get('units','—')] if kind=='products' else []),money(g['revenue'],g['currency']),money(g['average'],g['currency'])] for g in report.get('groups',[])]
        story.append(data_table(['Entidad','Ventas',*(['Unidades'] if kind=='products' else []),'Ingresos','Promedio'],rows,[56,20,22,39,39] if kind=='products' else [60,24,46,46]))
    story += [Spacer(1,8*mm),paragraph('Criterios del reporte','section'),paragraph('Esta copia conserva los datos y estados registrados al generarse. Los importes se separan por moneda. Las ventas anuladas no contribuyen a los indicadores.','small')]
    return build_document(titles.get(kind,'Reporte'),f"REPORTE #{report['id']:05d}",story)


def sale_pdf(sale):
    currency=sale['currency']
    story=[paragraph(sale['company_name']),paragraph(f"Fecha: {local_date(sale['sold_at'])} | Cliente: {sale.get('customer_name') or 'Cliente general'}"),
           paragraph(f"Vendedor: {sale['seller_name']} | Estado: {'ANULADA' if sale['status']=='voided' else 'CONFIRMADA'}"),paragraph('01 / Detalle de artículos','section')]
    rows=[[f"{r['name']}\n{r['sku']}",r['quantity'],money(r['unit_price'],currency),money(r['discount'],currency),money(r['tax'],currency),money(r['line_total'],currency)] for r in sale['items']]
    story.append(data_table(['Artículo','Cant.','Precio','Desc.','Impuesto','Total'],rows,[56,15,26,25,26,28]))
    story.append(KeepTogether([paragraph('Resumen de la operación','section'),data_table(['Subtotal','Descuentos','Impuestos','Total'],[[money(sale['subtotal'],currency),money(sale['discount_total'],currency),money(sale['tax_total'],currency),money(sale['total'],currency)]],[44,44,44,44])]))
    methods={'cash':'Efectivo','card':'Tarjeta','transfer':'Transferencia','other':'Otro'}
    states={'completed':'Recibido','refunded':'Devolución registrada','pending':'Pendiente'}
    story += [paragraph('02 / Pagos registrados','section'),data_table(['Método','Importe','Estado','Fecha'],[[methods.get(p['method'],p['method']),money(p['amount'],currency),states.get(p['status'],p['status']),local_date(p.get('paid_at'))] for p in sale['payments']],[35,42,54,45])]
    if sale['status']=='voided': story += [paragraph('Anulación','section'),paragraph(sale.get('void_reason') or '—')]
    story.append(paragraph('Este recibo es un registro interno de la venta y sus pagos.','small'))
    return build_document('Recibo de venta',f"VENTA #{sale['id']:05d}",story)
