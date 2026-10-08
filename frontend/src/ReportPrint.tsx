import ReportGroups, { reportTitle } from "./ReportGroups";
import { DocumentBrand, DocumentFooter } from "./DocumentBrand";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { Printer, X } from "lucide-react";
import type { ReportSnapshot } from "./services/api";
import { usePdfDownload } from "./hooks/usePdfDownload";

const money=(value:string,currency:string)=>new Intl.NumberFormat("es-PE",{style:"currency",currency}).format(Number(value));
const date=(value:string)=>new Date(value).toLocaleString("es-PE",{timeZone:"America/Lima"});
export default function ReportPrint({report:r,onClose}:{report:ReportSnapshot;onClose:()=>void}){
  const pdf=usePdfDownload("reports",r.id);
  useEffect(()=>{const previous=document.activeElement as HTMLElement;return()=>previous?.focus();},[]);
  return createPortal(<div className="modal-backdrop receipt-overlay" onClick={onClose}>
    <section className="modal receipt-sheet report-document" role="dialog" aria-modal="true" aria-labelledby="report-document-title" onClick={e=>e.stopPropagation()} onKeyDown={e=>{
      if(e.key==="Escape")onClose();
      if(e.key==="Tab"){const buttons=e.currentTarget.querySelectorAll<HTMLButtonElement>("button");const first=buttons[0],last=buttons[buttons.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
    }}>
      <div className="report-print-controls no-print"><span>Formato A4 · Descarga el documento o abre la vista de impresión.</span><div className="document-download-actions"><button className="btn btn-light" onClick={()=>window.print()}><Printer size={16}/> Imprimir</button><button className="btn btn-primary" disabled={pdf.busy} onClick={pdf.download}>{pdf.busy?"Preparando PDF…":"Descargar PDF"}</button></div><button className="icon-button" autoFocus onClick={onClose} aria-label="Cerrar vista PDF"><X size={18}/></button></div>
      {pdf.error&&<p className="inline-error no-print" role="alert">{pdf.error}</p>}
      
      <DocumentBrand label="REPORTE ARCHIVADO" id={r.id}/>
      <div className="report-document-heading"><p>ANÁLISIS COMERCIAL</p><h1 id="report-document-title">{reportTitle(r.report_type)}</h1><p>{r.parameters.start??"Desde el inicio"} / {r.parameters.end??"Sin fecha final"}</p></div>
      <dl className="report-document-meta"><div><dt>Fecha de generación</dt><dd>{date(r.generated_at)}</dd></div><div><dt>Zona horaria</dt><dd>America/Lima</dd></div>{(["customer_id","employee_id","product_id","branch_id"] as const).map((key,index)=><div key={key}><dt>{["Cliente","Vendedor","Producto","Sucursal"][index]}</dt><dd>{r.parameters.filters?.[key]?.name??"Todos"}</dd></div>)}</dl>
      <h2 className="report-document-section">01 / Indicadores del periodo</h2>
      <p className="report-document-note">{r.summary.sales_count} ventas confirmadas · {r.summary.voided_count} anuladas excluidas de los indicadores.</p>
      {!r.summary.by_currency.length&&<p>No hay ventas confirmadas para calcular indicadores.</p>}
      {r.summary.by_currency.map(group=><div className="report-document-metrics" key={group.currency}><div className="report-document-revenue"><small>INGRESOS · {group.currency}</small><strong>{money(group.revenue,group.currency)}</strong><span>{group.sales_count} ventas confirmadas</span></div><dl>{([["Ticket promedio",group.average_ticket],["Mediana",group.median_ticket],["Ticket mínimo",group.minimum],["Ticket máximo",group.maximum]] as const).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{money(value,group.currency)}</dd></div>)}</dl></div>)}
      {r.groups&&<><h2 className="report-document-section">02 / Resultados agrupados</h2><ReportGroups groups={r.groups} type={r.report_type}/></>}
      {r.report_type==="sales"&&<><h2 className="report-document-section">02 / Detalle de transacciones</h2><p className="report-document-note">{r.rows.length} registros incluidos en la copia archivada.</p><div className="table-wrap"><table><thead><tr><th>Venta / fecha</th><th>Cliente / vendedor</th><th>Estado</th><th>Total</th></tr></thead><tbody>{r.rows.map(row=><tr key={row.id}><td><b>#{row.id}</b><small>{date(row.sold_at)}</small></td><td>{row.customer??"Cliente general"}<small>{row.seller}</small></td><td>{row.status==="confirmed"?"Confirmada":"Anulada"}</td><td className="report-document-amount">{money(row.total,row.currency)}</td></tr>)}</tbody></table></div></>}
      <aside className="report-document-method"><strong>Criterios del reporte</strong><p>Los importes se presentan por moneda. Esta copia conserva los datos y estados registrados al generarse.{r.parameters.filters?.product_id&&" El filtro por producto incluye el importe completo de las ventas que lo contienen."}</p></aside>
      <DocumentFooter reference={`Reporte #${r.id}`}/>
    </section>
  </div>,document.body);
}
