import { DocumentBrand, DocumentFooter } from "./DocumentBrand";
import { useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Printer, X } from "lucide-react";
import { api, type SaleDetail } from "./services/api";
import { usePdfDownload } from "./hooks/usePdfDownload";

const paymentMethods: Record<string,string> = { cash: "Efectivo", card: "Tarjeta", transfer: "Transferencia", other: "Otro" };
const paymentStates: Record<string,string> = { completed: "Recibido", refunded: "Devolución registrada", pending: "Pendiente" };
export default function SaleReceipt({ id, canVoid, onClose, onVoided }: { id: number; canVoid: boolean; onClose: () => void; onVoided: () => void }) {
  const pdf=usePdfDownload("sales",id);
  const [sale, setSale] = useState<SaleDetail | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [voiding, setVoiding] = useState(false);
  const [reason, setReason] = useState("");
  const [refund, setRefund] = useState(false);
  const [restock, setRestock] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let current = true; setError(""); setSale(null);
    api.sale(id).then(data => { if(current) setSale(data); }).catch(e => { if(current) setError(e instanceof Error ? e.message : "No se pudo cargar la venta"); });
    return () => { current = false; };
  }, [id,revision]);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    return () => { previous?.focus(); };
  }, []);
  const money = (value: string) => new Intl.NumberFormat("es-PE", { style:"currency", currency:sale?.currency ?? "PEN" }).format(Number(value));
  function close() { if (!busy) onClose(); }
  async function cancel(event: FormEvent) {
    event.preventDefault();
    if(!refund || !restock || reason.trim().length < 3) return;
    setBusy(true); setError("");
    try {
      await api.voidSale(id,reason.trim(),refund,restock);
      setVoiding(false); setRevision(v => v + 1); onVoided();
    } catch(e) { setError(e instanceof Error ? e.message : "No se pudo anular la venta"); }
    finally { setBusy(false); }
  }
  return createPortal(<div className="modal-backdrop receipt-overlay" onClick={close}>
    <section className="modal receipt-sheet report-document" role="dialog" aria-modal="true" aria-labelledby="receipt-title" onClick={e => e.stopPropagation()} onKeyDown={e => {
      if(e.key === "Escape") close();
      if(e.key === "Tab") {
        const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled),input:not(:disabled),textarea:not(:disabled)"));
        const first=controls[0],last=controls[controls.length-1];
        if(e.shiftKey && document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first?.focus();}
      }
    }}>
      <div className="report-print-controls no-print"><span>Formato A4 · Recibo de venta</span>{sale&&<div className="document-download-actions"><button className="btn btn-light" onClick={()=>window.print()}><Printer size={16}/> Imprimir</button><button className="btn btn-primary" disabled={pdf.busy} onClick={pdf.download}>{pdf.busy?"Preparando PDF…":"Descargar PDF"}</button></div>}<button autoFocus type="button" className="icon-button" disabled={busy} aria-label="Cerrar recibo" onClick={close}><X size={18}/></button></div>
      <DocumentBrand label="RECIBO INTERNO" id={id}/>
      <div className="report-document-heading"><p>REGISTRO COMERCIAL</p><h1 id="receipt-title">Recibo de venta</h1><p>Detalle de la operación y pagos registrados</p></div>
      {error && <div className="inline-error no-print" role="alert">{error}{!sale && <button className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar</button>}</div>}
      {!sale && !error && <p role="status">Cargando detalle…</p>}
      {pdf.error&&<p className="inline-error no-print" role="alert">{pdf.error}</p>}
      {sale && <>
        <div className="receipt-meta"><div><small>Empresa</small><strong>{sale.company_name}</strong></div><div><small>Fecha de venta</small><strong>{new Date(sale.sold_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</strong></div><div><small>Cliente</small><strong>{sale.customer_name || "Cliente general"}</strong></div><div><small>Vendedor</small><strong>{sale.seller_name}</strong></div></div>
        <p className={sale.status==="voided"?"receipt-voided":"receipt-confirmed"}>{sale.status==="voided"?"VENTA ANULADA":sale.status==="confirmed"?"VENTA CONFIRMADA":"BORRADOR"}</p>
        <h2 className="report-document-section">01 / Detalle de artículos</h2>
        <div className="table-wrap"><table><thead><tr><th>ARTÍCULO</th><th>CANT.</th><th>PRECIO</th><th>DESCUENTO</th><th>IMPUESTO</th><th>TOTAL</th></tr></thead><tbody>{sale.items.map(item=><tr key={item.product_id}><td><strong>{item.name}</strong><small className="movement-reference">{item.sku}</small></td><td>{item.quantity}</td><td>{money(item.unit_price)}</td><td>{money(item.discount)}</td><td>{money(item.tax)}</td><td>{money(item.line_total)}</td></tr>)}</tbody></table></div>
        <dl className="receipt-totals"><div><dt>Subtotal</dt><dd>{money(sale.subtotal)}</dd></div><div><dt>Descuentos</dt><dd>− {money(sale.discount_total)}</dd></div><div><dt>Impuestos</dt><dd>{money(sale.tax_total)}</dd></div><div className="receipt-grand-total"><dt>Total de la operación</dt><dd>{money(sale.total)}</dd></div></dl>
        <h2 className="report-document-section">02 / Pagos registrados</h2>
        <div className="table-wrap"><table><thead><tr><th>MÉTODO</th><th>IMPORTE</th><th>ESTADO</th><th>FECHA DEL PAGO</th></tr></thead><tbody>{sale.payments.map((payment,index)=><tr key={index}><td>{paymentMethods[payment.method]??payment.method}</td><td>{money(payment.amount)}</td><td>{paymentStates[payment.status]??payment.status}</td><td>{payment.paid_at?new Date(payment.paid_at).toLocaleString("es-PE",{timeZone:"America/Lima"}):"—"}</td></tr>)}</tbody></table></div>
        {sale.status==="voided" && <div className="receipt-cancellation"><strong>Anulación: {sale.voided_at?new Date(sale.voided_at).toLocaleString("es-PE",{timeZone:"America/Lima"}):"—"}</strong><p>{sale.void_reason}</p></div>}
        <aside className="report-document-method"><strong>Información de la operación</strong><p>Importes expresados en {sale.currency}. Fechas en America/Lima. Este recibo es un registro interno de la venta y sus pagos.</p></aside>
        <DocumentFooter reference={`Venta #${id}`}/>
        {!voiding ? <div className="modal-actions no-print">{canVoid&&sale.status==="confirmed"&&<button className="btn btn-light" onClick={()=>setVoiding(true)}>Anular venta</button>}</div> : <form className="receipt-void-form no-print" onSubmit={cancel}>
          <h3>Anular la venta completa</h3><p>Esta acción repone todos los artículos y registra la devolución íntegra de los pagos. Confirma las operaciones realizadas antes de continuar.</p>
          <label>Motivo<textarea required minLength={3} maxLength={1000} disabled={busy} value={reason} onChange={e=>setReason(e.target.value)}/></label>
          <label className="receipt-check"><input required type="checkbox" disabled={busy} checked={restock} onChange={e=>setRestock(e.target.checked)}/><span>Los artículos se recibieron y están disponibles para reponer el inventario.</span></label>
          <label className="receipt-check"><input required type="checkbox" disabled={busy} checked={refund} onChange={e=>setRefund(e.target.checked)}/><span>Devolví el importe completo mediante los medios correspondientes.</span></label>
          <p className="catalog-state-note">SalesIA registra la devolución confirmada; el dinero se devuelve por el medio de pago utilizado.</p>
          <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={()=>setVoiding(false)}>Volver</button><button className="btn btn-primary" disabled={busy||!refund||!restock||reason.trim().length<3}>{busy?"Procesando…":"Confirmar anulación"}</button></div>
        </form>}
      </>}
    </section>
  </div>,document.body);
}
