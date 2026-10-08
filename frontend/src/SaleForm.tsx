import BranchSelector from "./BranchSelector";
import { useEffect, useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import { api, type Customer, type Product, type PricingRules } from "./services/api";
import { decimalAmount, saleLineAmounts } from "./services/amounts";

type Line = { product: Product; quantity: string; discount: string; tax: string };
const money = (value: string) => new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(Number(value));
export default function SaleForm({ onClose, onCreated, mode = "sale" }: { onClose: () => void; onCreated: () => void; mode?: "sale" | "order" }) {
  const [rules,setRules]=useState<PricingRules|null>(null);
  const [rulesRevision,setRulesRevision]=useState(0);
  useEffect(()=>{let active=true;api.pricing().then(value=>{if(active)setRules(value)}).catch(()=>{if(active)setError("No se pudieron cargar las reglas comerciales.")});return()=>{active=false}},[rulesRevision]);
  const [branch,setBranch]=useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [productQuery, setProductQuery] = useState("");
  const [customerQuery, setCustomerQuery] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [productId, setProductId] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [method, setMethod] = useState("cash");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lookupError, setLookupError] = useState("");
  const isOrder = mode === "order";
  useEffect(() => {
    let current = true;
    setLoading(true);
    const timer = window.setTimeout(() => {
      Promise.all([api.products(productQuery,0,50,branch), api.customers(customerQuery)])
        .then(([ps, cs]) => { if (current) { setProducts(ps.filter(p => p.is_active)); setCustomers(cs.filter(c => c.is_active)); setLookupError(""); } })
        .catch(e => { if (current) { setProducts([]); setCustomers([]); setProductId(""); setLookupError(e instanceof Error ? e.message : "No se pudo consultar el catálogo. Modifica la búsqueda para reintentar."); } })
        .finally(() => { if (current) setLoading(false); });
    }, 250);
    return () => { current = false; window.clearTimeout(timer); };
  }, [productQuery, customerQuery,branch]);
  let cents = 0n, subtotal=0n, discount=0n, tax=0n;
  let invalid = false;
  for (const line of lines) {
    try {
      if (Number(line.quantity) <= 0 || (!isOrder && Number(line.quantity) > Number(line.product.stock))) invalid = true;
      const amount=saleLineAmounts(line.product.unit_price,line.quantity,line.discount,line.tax);
      cents+=amount.total;subtotal+=amount.subtotal;discount+=amount.discount;tax+=amount.tax;
    } catch { invalid = true; }
  }
  if (cents > 99999999999999n) invalid = true;
  const total = decimalAmount(cents);
  const available = products.filter(p => (isOrder || Number(p.stock) > 0) && !lines.some(line => line.product.id === p.id));
  function add() {
    const product = available.find(p => p.id === Number(productId));
    if (product) { setLines(current => [...current, { product, discount:String(rules?.default_discount_percent??"0"), tax:String(rules?.default_tax_percent??"0"), quantity: isOrder ? "1" : String(Math.min(1, Number(product.stock))) }]); setProductId(""); }
  }
  function close() { if (!busy) onClose(); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (!rules || invalid || !lines.length || cents <= 0n) { setError("Revisa cantidades, existencias y total antes de confirmar."); return; }
    setBusy(true);
    try {
      const payload = { branch_id:branch?Number(branch):null,customer_id: selectedCustomer?.id ?? null, items: lines.map(line => ({ product_id: line.product.id, quantity: Number(line.quantity), discount_percent:Number(line.discount),tax_percent:Number(line.tax) })) };
      if (isOrder) await api.createOrder(payload);
      else await api.createSale({ ...payload, payments: [{ method, amount: Number(total) }] });
      onCreated();
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo guardar la operación"); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop" onClick={close}><form className="modal sale-modal" role="dialog" aria-modal="true" aria-labelledby="sale-form-title" onClick={e => e.stopPropagation()} onSubmit={submit} onKeyDown={e => {
    if (e.key === "Escape") close();
    if (e.key === "Tab") {
      const fields = Array.from(e.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled),input:not(:disabled),select:not(:disabled)"));
      const first = fields[0], last = fields[fields.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }
  }}>
    <div className="modal-heading"><div><h2 id="sale-form-title">{isOrder ? "Nuevo pedido" : "Nueva venta"}</h2><p>{isOrder ? "El pedido conserva precios y no reserva inventario." : "Selecciona artículos, cantidades y forma de pago."}</p></div><button className="icon-button" type="button" disabled={busy} aria-label="Cerrar" onClick={close}><X size={18}/></button></div>
    <fieldset disabled={busy} className="catalog-fields"><BranchSelector value={branch} disabled={lines.length>0} onChange={value=>{setBranch(value);setProductId("");}}/>{lines.length>0&&<p className="form-note">Retira los artículos para cambiar de sucursal.</p>}
      <label>Buscar cliente<input autoFocus value={customerQuery} onChange={e => setCustomerQuery(e.target.value)} placeholder="Nombre o correo" maxLength={100}/></label>
      <label>Cliente<select value={selectedCustomer?.id ?? ""} onChange={e => setSelectedCustomer(customers.find(c => c.id === Number(e.target.value)) ?? null)}><option value="">Cliente general</option>{selectedCustomer && !customers.some(c => c.id === selectedCustomer.id) && <option value={selectedCustomer.id}>{selectedCustomer.name}</option>}{customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      <label>Buscar producto<input value={productQuery} onChange={e => { setProductQuery(e.target.value); setProductId(""); }} placeholder="Nombre o SKU" maxLength={100}/></label>
      <label>Producto<select value={productId} onChange={e => setProductId(e.target.value)} disabled={loading}><option value="">{loading ? "Cargando…" : "Selecciona un producto"}</option>{available.map(p => <option key={p.id} value={p.id}>{p.name} · {p.sku} · {money(p.unit_price)} · stock {p.stock}</option>)}</select></label>
      <button className="btn btn-light" type="button" disabled={!rules || loading || !available.some(p => p.id === Number(productId)) || lines.length >= 100} onClick={add}><Plus size={15}/> Agregar producto</button>
      <p className="catalog-state-note">Se muestran hasta 50 coincidencias. Usa la búsqueda para encontrar otros registros.</p>
      {lines.map(line => <div className="sale-line" key={line.product.id}><div><strong>{line.product.name}</strong><small>{money(line.product.unit_price)} · stock {line.product.stock}</small></div><input required aria-label={`Cantidad de ${line.product.name}`} type="number" step="0.001" min="0.001" max={isOrder ? "99999999999.999" : line.product.stock} value={line.quantity} onChange={e => setLines(current => current.map(item => item.product.id === line.product.id ? { ...item, quantity: e.target.value } : item))}/><button type="button" className="icon-button" aria-label={`Quitar ${line.product.name}`} onClick={() => setLines(current => current.filter(item => item.product.id !== line.product.id))}><X size={15}/></button></div>)}
      {lines.length>0&&<section className="sale-pricing"><h3>Descuentos e impuestos</h3><p className="form-note">Porcentajes por producto. El impuesto se calcula sobre el importe después del descuento. Los precios del catálogo se toman como base; usa 0 si no corresponde agregar un impuesto.</p>{lines.map(line=><div className="sale-pricing-row" key={line.product.id}><strong>{line.product.name}</strong>{(["discount","tax"] as const).map(key=><label key={key}>{key==="discount"?"Descuento %":"Impuesto %"}<input aria-label={`${key==="discount"?"Descuento":"Impuesto"} de ${line.product.name}`} type="number" required disabled={!rules?.allow_pricing_override} min="0" max="100" step="0.01" value={line[key]} onChange={e=>setLines(current=>current.map(item=>item.product.id===line.product.id?{...item,[key]:e.target.value}:item))}/></label>)}</div>)}</section>}
      {!lines.length && <div className="sale-no-lines">Selecciona un producto para comenzar.</div>}
      {!isOrder && <label>Método de pago<select value={method} onChange={e => setMethod(e.target.value)}><option value="cash">Efectivo</option><option value="card">Tarjeta</option><option value="transfer">Transferencia</option><option value="other">Otro</option></select></label>}
    </fieldset>
    {!rules&&<p className="form-note">Cargando reglas comerciales… <button type="button" className="text-button" onClick={()=>setRulesRevision(v=>v+1)}>Reintentar</button></p>}
    {lookupError && <div className="inline-error" role="alert">{lookupError}</div>}
    {error && <div className="inline-error" role="alert">{error}</div>}
    {invalid && <p className="inline-error">Revisa las cantidades y el stock. Los porcentajes deben estar entre 0 y 100, con hasta dos decimales.</p>}
    {lines.length>0&&!invalid&&<div className="sale-cost-breakdown" aria-live="polite"><div><span>Subtotal</span><strong>{money(decimalAmount(subtotal))}</strong></div><div><span>Descuentos</span><strong>− {money(decimalAmount(discount))}</strong></div><div><span>Impuestos</span><strong>{money(decimalAmount(tax))}</strong></div></div>}
    <div className="sale-total"><span>Total {isOrder ? "del pedido" : "a pagar"}</span><strong>{invalid ? "—" : money(total)}</strong></div>
    <div className="modal-actions"><button className="btn btn-light" type="button" disabled={busy} onClick={close}>Cancelar</button><button className="btn btn-primary" disabled={busy || !rules || invalid || !lines.length || cents <= 0n}>{busy ? "Guardando…" : isOrder ? "Crear pedido" : "Confirmar venta"}</button></div>
  </form></div>;
}
