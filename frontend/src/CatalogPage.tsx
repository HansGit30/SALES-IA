import CustomerHistory from "./CustomerHistory";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Pencil, Search, X } from "lucide-react";
import { api, type Category, type Customer, type Product } from "./services/api";

type Draft = { name: string; email: string; phone: string; sku: string; description: string; price: string; category: string; active: boolean };
const empty: Draft = { name: "", email: "", phone: "", sku: "", description: "", price: "", category: "", active: true };
const pageSize = 25;
const money = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" });

export default function CatalogPage({ kind, canEdit }: { kind: "customers" | "products"; canEdit: boolean }) {
  const [historyId,setHistoryId]=useState<number|null>(null);
  const productMode = kind === "products";
  const label = productMode ? "producto" : "cliente";
  const [rows, setRows] = useState<(Customer | Product)[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [show, setShow] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>(empty);
  const [busy, setBusy] = useState(false);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const timer = window.setTimeout(async () => {
      try {
        const data = productMode ? await api.products(q, page * pageSize, pageSize + 1) : await api.customers(q, page * pageSize, pageSize + 1);
        if (active) setRows(data);
      } catch (e) { if (active) { setRows([]); setError(e instanceof Error ? e.message : "No se pudo cargar el catálogo"); } }
      finally { if (active) setLoading(false); }
    }, 200);
    return () => { active = false; window.clearTimeout(timer); };
  }, [q, page, refresh, productMode]);

  useEffect(() => {
    if (!productMode || !show) return;
    let active = true;
    api.categories().then(data => { if (active) setCategories(data); }).catch(() => { if (active) setFormError("No se pudieron cargar las categorías. Cierra y vuelve a abrir el formulario."); });
    return () => { active = false; };
  }, [productMode, show]);

  useEffect(() => {
    const open = () => {
      if (!canEdit) return;
      returnFocus.current = document.activeElement as HTMLElement;
      setEditing(null); setDraft({ ...empty }); setFormError(""); setShow(true);
    };
    window.addEventListener(`salesia:create-${kind}`, open);
    return () => window.removeEventListener(`salesia:create-${kind}`, open);
  }, [kind, canEdit]);

  function close() { if (!busy) { setShow(false); returnFocus.current?.focus(); } }
  function edit(row: Customer | Product) {
    returnFocus.current = document.activeElement as HTMLElement;
    const p = row as Product, c = row as Customer;
    setEditing(row.id);
    setDraft({ name: row.name, active: row.is_active, email: c.email ?? "", phone: c.phone ?? "", sku: p.sku ?? "", description: p.description ?? "", price: p.unit_price ?? "", category: p.category_id ? String(p.category_id) : "" });
    setFormError(""); setShow(true);
  }
  function field<K extends keyof Draft>(key: K, value: Draft[K]) { setDraft(current => ({ ...current, [key]: value })); }

  async function save(event: FormEvent) {
    event.preventDefault(); setFormError("");
    if (!draft.name.trim() || (productMode && !draft.sku.trim())) { setFormError("Completa los campos obligatorios sin usar solo espacios."); return; }
    setBusy(true);
    try {
      if (productMode) {
        const payload = { name: draft.name.trim(), sku: draft.sku.trim(), description: draft.description.trim() || null, unit_price: Number(draft.price), category_id: draft.category ? Number(draft.category) : null };
        if (editing !== null) await api.updateProduct(editing, { ...payload, is_active: draft.active });
        else await api.createProduct(payload);
      } else {
        const payload = { name: draft.name.trim(), email: draft.email.trim() || null, phone: draft.phone.trim() || null };
        if (editing !== null) await api.updateCustomer(editing, { ...payload, is_active: draft.active });
        else await api.createCustomer({ ...payload, email: payload.email ?? undefined, phone: payload.phone ?? undefined });
      }
      setShow(false); setNotice(editing !== null ? "Cambios guardados." : "Registro creado.");
      setRefresh(value => value + 1); returnFocus.current?.focus();
    } catch (e) { setFormError(e instanceof Error ? e.message : "No se pudo guardar el registro"); }
    finally { setBusy(false); }
  }

  return <>{historyId!==null&&<CustomerHistory id={historyId} onClose={()=>setHistoryId(null)}/>}
    <section className="panel data-panel" aria-busy={loading}>
      <div className="data-toolbar"><div><strong>{productMode ? "Catálogo de productos" : "Directorio de clientes"}</strong><p>{productMode ? "Precios, categorías y disponibilidad" : "Datos de contacto y estado de tu cartera"}</p></div>
        <label className="search-box"><Search size={16}/><input aria-label={`Buscar ${label}`} maxLength={100} placeholder={productMode ? "Buscar nombre o SKU…" : "Buscar nombre o correo…"} value={q} onChange={e => { setQ(e.target.value); setPage(0); }}/></label>
      </div>
      {notice && <p className="catalog-notice" role="status">{notice}</p>}
      {error && <div className="inline-error" role="alert">{error} <button className="text-button" onClick={() => setRefresh(v => v + 1)}>Reintentar</button></div>}
      <div className="table-wrap"><table><thead><tr><th>{productMode ? "PRODUCTO" : "CLIENTE"}</th>
        {productMode ? <><th>SKU</th><th>CATEGORÍA</th><th>PRECIO</th><th>STOCK</th></> : <><th>CORREO</th><th>TELÉFONO</th></>}<th>ESTADO</th>{(canEdit||!productMode) && <th>ACCIONES</th>}
      </tr></thead><tbody>{!loading && rows.slice(0, pageSize).map(row => {
        const p = row as Product, c = row as Customer;
        return <tr key={row.id}><td><div className="table-person"><span className={productMode ? "product-avatar" : "person-avatar"}>{row.name.slice(0, 1).toUpperCase()}</span><strong>{row.name}</strong></div></td>
          {productMode ? <><td><span className="sku">{p.sku}</span></td><td>{p.category_name || "Sin categoría"}</td><td>{money.format(Number(p.unit_price))}</td><td>{p.stock}</td></> : <><td>{c.email || "—"}</td><td>{c.phone || "—"}</td></>}
          <td><span className={`status ${row.is_active ? "status-active" : "status-inactive"}`}><i/>{row.is_active ? "Activo" : "Inactivo"}</span></td>
          {(canEdit||!productMode) && <td>{!productMode&&<button className="text-button" onClick={()=>setHistoryId(row.id)}>Historial</button>}{canEdit&&<button className="btn btn-light catalog-edit" onClick={() => edit(row)} aria-label={`Editar ${row.name}`}><Pencil size={14}/> Editar</button>}</td>}
        </tr>;
      })}</tbody></table></div>
      {loading ? <div className="table-empty" role="status">Cargando registros…</div> : !rows.length && !error && <div className="table-empty">{q ? "No hay coincidencias para esta búsqueda." : "No hay registros en esta página."}</div>}
      <div className="catalog-pagination"><span>Página {page + 1} · Hasta {pageSize} registros por página</span><div><button className="btn btn-light" disabled={loading || page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button><button className="btn btn-light" disabled={loading || rows.length <= pageSize} onClick={() => setPage(p => p + 1)}>Siguiente</button></div></div>
    </section>
    {show && <div className="modal-backdrop" onClick={close}><form className="modal" role="dialog" aria-modal="true" aria-labelledby="catalog-dialog-title" onClick={e => e.stopPropagation()} onKeyDown={e => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)'));
        const first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }} onSubmit={save}>
      <div className="modal-heading"><div><h2 id="catalog-dialog-title">{editing !== null ? "Editar" : "Nuevo"} {label}</h2><p>{editing !== null ? "Actualiza los datos y la disponibilidad." : "Completa los datos del nuevo registro."}</p></div><button type="button" className="icon-button" disabled={busy} aria-label="Cerrar formulario" onClick={close}><X size={18}/></button></div>
      <fieldset disabled={busy} className="catalog-fields">
        <label>Nombre<input autoFocus required maxLength={180} value={draft.name} onChange={e => field("name", e.target.value)}/></label>
        {productMode ? <>
          <label>SKU<input required maxLength={80} value={draft.sku} onChange={e => field("sku", e.target.value)}/></label>
          <label>Descripción<textarea maxLength={2000} value={draft.description} onChange={e => field("description", e.target.value)}/></label>
          <label>Categoría<select value={draft.category} onChange={e => field("category", e.target.value)}><option value="">Sin categoría</option>{categories.filter(c => c.is_active || String(c.id) === draft.category).map(c => <option key={c.id} value={c.id}>{c.name}{!c.is_active && " (inactiva)"}</option>)}</select></label>
          <label>Precio unitario (S/)<input required type="number" min="0" max="999999999999.99" step="0.01" value={draft.price} onChange={e => field("price", e.target.value)}/></label>
        </> : <>
          <label>Correo electrónico<input type="email" value={draft.email} onChange={e => field("email", e.target.value)}/></label>
          <label>Teléfono<input maxLength={40} value={draft.phone} onChange={e => field("phone", e.target.value)}/></label>
        </>}
        {editing !== null && <><label>Estado<select value={String(draft.active)} onChange={e => field("active", e.target.value === "true")}><option value="true">Activo</option><option value="false">Inactivo</option></select></label><p className="catalog-state-note">Los registros inactivos conservan su historial y dejan de estar disponibles para nuevas ventas.</p></>}
      </fieldset>
      {formError && <div className="inline-error" role="alert">{formError}</div>}
      <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={close}>Cancelar</button><button className="btn btn-primary" disabled={busy}>{busy ? "Guardando…" : "Guardar cambios"}</button></div>
    </form></div>}
  </>;
}
