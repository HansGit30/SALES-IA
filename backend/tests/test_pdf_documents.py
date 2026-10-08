import re
import pytest
from app.services.pdf_documents import report_pdf, sale_pdf


def sample_report(kind='sales',count=120):
    return {'id':42,'report_type':kind,'generated_at':'2026-10-04T15:00:00+00:00','parameters':{'start':'2026-09-01','end':'2026-10-04','filters':{}},
            'summary':{'sales_count':count,'voided_count':0,'by_currency':[{'currency':'PEN','revenue':str(count*1250),'average_ticket':'1250','median_ticket':'1250','minimum':'1250','maximum':'1250','sales_count':count}]},
            'rows':[{'id':i+1,'sold_at':'2026-10-03T16:45:00+00:00','customer':'Cliente de aceptación con nombre extenso','seller':'Equipo comercial QA','status':'confirmed','total':'1250','currency':'PEN'} for i in range(count)],
            'groups':[{'name':'Artículo de prueba <QA> & categoría','sales_count':count,'units':str(count),'revenue':str(count*1250),'average':'1250','currency':'PEN'}]}


@pytest.mark.parametrize('kind',['sales','statistical','products','customers','sellers'])
def test_report_types_render(kind):
    content=report_pdf(sample_report(kind))
    assert content.startswith(b'%PDF-')
    assert b'%%EOF' in content
    if kind=='sales': assert len(re.findall(rb'/Type /Page\b',content))>=4


def test_empty_report_renders():
    report=sample_report(count=0)
    report['summary']['by_currency']=[]
    assert report_pdf(report).startswith(b'%PDF-')


def test_receipt_renders_escaped_names_and_cancellation():
    sale={'id':9,'currency':'PEN','company_name':'Empresa & Asociados','customer_name':'Cliente <QA>','seller_name':'Vendedor QA',
          'sold_at':'2026-10-04T15:00:00+00:00','status':'voided','void_reason':'Devolución de prueba',
          'subtotal':'1250','discount_total':'125','tax_total':'202.50','total':'1327.50',
          'items':[{'name':'Portátil <QA>','sku':'QA','quantity':'1','unit_price':'1250','discount':'125','tax':'202.50','line_total':'1327.50'}],
          'payments':[{'method':'cash','amount':'1327.50','status':'refunded','paid_at':'2026-10-04T15:00:00+00:00'}]}
    assert sale_pdf(sale).startswith(b'%PDF-')
