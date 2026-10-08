import { useEffect, useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import { api, type Order, type OrderDetail } from "./services/api";
import SaleForm from "./SaleForm";

const labels = { pending: "Pendiente", converted: "Convertido en venta", cancelled: "Cancelado" };
const money = (value: string, currency: string) => new Intl.NumberFormat("es-PE", { style: "currency", currency }).format(Number(value));
export default function OrdersPage({ canManage }: { canManage: boolean }) {
  const [rows, setRows] = useState<Order[]>([]);
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Order | null>(null);
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [action, setAction] = useState<"view" | "confirm" | "cancel">("view");
  const [formError, setFormError] = useState("");
  const [method, setMethod] = useState("cash");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let current = true; setLoading(true); setError("");
    api.orders(page * 25).then(data => { if (current) setRows(data); })
      .catch(e => { if (current) setError(e instanceof Error ? e.message : "No se pudieron cargar los pedidos"); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [page, refresh]);
  useEffect(() => {
    if (!selected) return;
    let current = true;
    setDetail(null); setFormError(""); setAction("view"); setReason(""); setMethod("cash");
    api.order(selected.id).then(data => { if (current) setDetail(data); })
      .catch(e => { if (current) setFormError(e instanceof Error ? e.message : "No se pudo cargar el detalle"); });
    return () => { current = false; };
  }, [selected]);
  function close() { if (!busy) setSelected(null); }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!detail || action === "view") return;
    if (action === "cancel" && reason.trim().length < 3) { setFormError("Indica un motivo de al menos tres caracteres."); return; }
    setBusy(true); setFormError("");
    try {
      if (action === "confirm") {
        const result = await api.confirmOrder(detail.id, method, Number(detail.total));
        setNotice(`Pedido convertido en venta #${result.sale_id}. Pago e inventario registrados.`);
      } else { await api.cancelOrder(detail.id, reason.trim()); setNotice("Pedido cancelado. Se conserva su historial."); }
      setSelected(null); setRefresh(v => v + 1);
    } catch (e) { setFormError(e instanceof Error ? e.message : "No se pudo completar la operación"); }
    finally { setBusy(false); }
  }
  return <>
    <section className="panel data-panel">
      <div className="data-toolbar"><div><strong>Pedidos comerciales</strong><p>Prepara la operación antes de registrar el pago y descontar stock</p></div>{canManage && <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Plus size={15}/> Nuevo pedido</button>}</div>
      {notice && <p className="catalog-notice" role="status">{notice}</p>}
      {error && <div className="inline-error" role="alert">{error} <button className="text-button" onClick={() => setRefresh(v => v + 1)}>Reintentar</button></div>}
      <div className="table-wrap"><table><thead><tr><th>PEDIDO</th><th>FECHA</th><th>CLIENTE</th><th>RESPONSABLE</th><th>TOTAL</th><th>ESTADO</th><th>ACCIONES</th></tr></thead><tbody>{!loading && rows.slice(0,25).map(row => <tr key={row.id}><td><strong>#{row.id}</strong></td><td>{new Date(row.created_at).toLocaleString("es-PE")}</td><td>{row.customer_name || "Cliente general"}</td><td>{row.author_name}</td><td>{money(row.total, row.currency)}</td><td><span className={`status ${row.status === "cancelled" ? "status-inactive" : "status-active"}`}>{labels[row.status]}</span></td><td><button className="text-button" onClick={() => setSelected(row)}>Ver detalle</button></td></tr>)}</tbody></table></div>
      {loading ? <div className="table-empty">Cargando pedidos…</div> : !rows.length && !error && <div className="table-empty">No hay pedidos en esta página.</div>}
      <div className="catalog-pagination"><span>Página {page + 1} · 25 pedidos por página</span><div><button className="btn btn-light" disabled={loading || page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button><button className="btn btn-light" disabled={loading || rows.length <= 25} onClick={() => setPage(p => p + 1)}>Siguiente</button></div></div>
    </section>
    {showCreate && <SaleForm mode="order" onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); setPage(0); setNotice("Pedido creado. El inventario se descontará al convertirlo en venta."); setRefresh(v => v + 1); }}/>}
    {selected && <div className="modal-backdrop" onClick={close}><form className="modal sale-modal" role="dialog" aria-modal="true" aria-labelledby="order-dialog-title" onClick={e => e.stopPropagation()} onSubmit={submit} onKeyDown={e => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled),select:not(:disabled),textarea:not(:disabled)"));
        const first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }}>
      <div className="modal-heading"><div><h2 id="order-dialog-title">Pedido #{selected.id}</h2><p>{labels[detail?.status ?? selected.status]}</p></div><button autoFocus className="icon-button" type="button" disabled={busy} aria-label="Cerrar detalle" onClick={close}><X size={18}/></button></div>
      {formError && <div className="inline-error" role="alert">{formError}</div>}
      {!detail && !formError && <p role="status">Cargando detalle…</p>}
      {detail && <>
        <div className="table-wrap"><table><thead><tr><th>ARTÍCULO</th><th>CANTIDAD</th><th>PRECIO</th><th>IMPORTE</th></tr></thead><tbody>{detail.items.map(item => <tr key={item.product_id}><td>{item.name}<small className="movement-reference">{item.sku}</small></td><td>{item.quantity}</td><td>{money(item.unit_price,detail.currency)}</td><td>{money(item.line_total,detail.currency)}</td></tr>)}</tbody></table></div>
        <div className="sale-total"><span>Total</span><strong>{money(detail.total,detail.currency)}</strong></div>
        {detail.sale_id && <p className="catalog-state-note">Venta generada: #{detail.sale_id}</p>}
        {detail.cancel_reason && <p className="catalog-state-note">Motivo de cancelación: {detail.cancel_reason}</p>}
        {canManage && detail.status === "pending" && <>
          {action === "view" ? <div className="modal-actions"><button type="button" className="btn btn-light" onClick={() => setAction("cancel")}>Cancelar pedido</button><button type="button" className="btn btn-primary" onClick={() => setAction("confirm")}>Convertir en venta</button></div> : <>
            {action === "confirm" ? <><p className="catalog-state-note">Confirma que recibiste el pago completo. Se registrará la venta y se descontará inventario. Los precios y existencias se validan nuevamente.</p><label>Método de pago<select disabled={busy} value={method} onChange={e => setMethod(e.target.value)}><option value="cash">Efectivo</option><option value="card">Tarjeta</option><option value="transfer">Transferencia</option><option value="other">Otro</option></select></label></> : <label>Motivo de cancelación<textarea disabled={busy} required minLength={3} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)}/></label>}
            <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={() => { setAction("view"); setFormError(""); }}>Volver</button><button className="btn btn-primary" disabled={busy}>{busy ? "Procesando…" : action === "confirm" ? "Confirmar pago y venta" : "Confirmar cancelación"}</button></div>
          </>}
        </>}
      </>}
    </form></div>}
  </>;
}
