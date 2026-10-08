import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Pencil, Plus, Search, X } from "lucide-react";
import { api, type ManagedUser } from "./services/api";

import BranchSelector from "./BranchSelector";

type Entry = { branch_id?:number|null; branch_name?:string|null; id: number; name: string; is_active: boolean; user_id?: number | null; email?: string | null };
export default function DirectoryPage({ kind, canEdit }: { kind: "categories" | "employees"; canEdit: boolean }) {
  const employees = kind === "employees";
  const [items, setItems] = useState<Entry[]>([]);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [show, setShow] = useState(false);
  const [editing, setEditing] = useState<Entry | null>(null);
  const [name, setName] = useState("");
  const [active, setActive] = useState(true);
  const [branchId,setBranchId]=useState("");
  const [userId, setUserId] = useState("");
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const previousFocus = useRef<HTMLElement | null>(null);
  const singular = employees ? "vendedor" : "categoría";

  useEffect(() => {
    let current = true;
    setLoading(true); setError("");
    const request = employees
      ? api.employees().then(rows => rows.map(row => ({ ...row, name: row.full_name })))
      : api.categories();
    request.then(rows => { if (current) setItems(rows); })
      .catch(e => { if (current) setError(e instanceof Error ? e.message : "No se pudo cargar el directorio"); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [employees, refresh]);

  function open(row: Entry | null = null) {
    if (!canEdit) return;
    previousFocus.current = document.activeElement as HTMLElement;
    setEditing(row); setName(row?.name ?? ""); setActive(row?.is_active ?? true);
    setBranchId(row?.branch_id?String(row.branch_id):"");
    setUserId(""); setFormError(""); setShow(true);
  }
  function close() { if (!busy) { setShow(false); previousFocus.current?.focus(); } }

  useEffect(() => {
    const handle = () => open();
    window.addEventListener(`salesia:create-${kind}`, handle);
    return () => window.removeEventListener(`salesia:create-${kind}`, handle);
  }, [kind, canEdit]);

  useEffect(() => {
    if (!show || !employees || editing || !canEdit) return;
    let current = true;
    setUsersLoading(true);
    api.users().then(rows => {
      if (current) setUsers(rows.filter(user => user.is_active && user.role === "seller" && !items.some(item => item.user_id === user.id)));
    }).catch(() => { if (current) { setUsers([]); setFormError("No se pudieron cargar las cuentas. Puedes crear un perfil sin cuenta vinculada."); } })
      .finally(() => { if (current) setUsersLoading(false); });
    return () => { current = false; };
  }, [show, employees, editing, canEdit, items]);

  const filtered = useMemo(() => {
    const text = query.trim().toLocaleLowerCase("es");
    return items.filter(item => (!text || item.name.toLocaleLowerCase("es").includes(text) || item.email?.toLocaleLowerCase("es").includes(text))
      && (status === "all" || item.is_active === (status === "active")));
  }, [items, query, status]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 25));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * 25, currentPage * 25 + 25);

  async function save(event: FormEvent) {
    event.preventDefault(); setFormError("");
    if (name.trim().length < (employees ? 2 : 1)) { setFormError("Escribe un nombre válido."); return; }
    setBusy(true);
    try {
      if (editing) {
        if (employees) await api.updateEmployee(editing.id, name.trim(), active,branchId?Number(branchId):null);
        else await api.updateCategory(editing.id, name.trim(), active);
      } else if (employees) await api.createEmployee(name.trim(), userId ? Number(userId) : null,branchId?Number(branchId):null);
      else await api.createCategory(name.trim());
      setShow(false); setNotice(editing ? "Cambios guardados." : "Registro creado.");
      setRefresh(value => value + 1); previousFocus.current?.focus();
    } catch (e) { setFormError(e instanceof Error ? e.message : "No se pudo guardar el registro"); }
    finally { setBusy(false); }
  }

  return <>
    <section className="panel data-panel" aria-busy={loading}>
      <div className="data-toolbar"><div><strong>{employees ? "Equipo comercial" : "Categorías de productos"}</strong><p>{employees ? "Perfiles, cuentas vinculadas y disponibilidad" : "Organiza el catálogo por familias de productos"}</p></div>
        <div className="directory-filters"><label className="search-box"><Search size={16}/><input aria-label={`Buscar ${singular}`} placeholder="Buscar por nombre…" value={query} onChange={e => { setQuery(e.target.value); setPage(0); }}/></label>
          <select className="directory-status" aria-label="Filtrar por estado" value={status} onChange={e => { setStatus(e.target.value); setPage(0); }}><option value="all">Todos los estados</option><option value="active">Activos</option><option value="inactive">Inactivos</option></select>
          {employees && canEdit && <button className="btn btn-primary" onClick={() => open()}><Plus size={15}/> Nuevo vendedor</button>}
        </div>
      </div>
      {notice && <p className="catalog-notice" role="status">{notice}</p>}
      {error && <div className="inline-error" role="alert">{error} <button className="text-button" onClick={() => setRefresh(value => value + 1)}>Reintentar</button></div>}
      <div className="table-wrap"><table><thead><tr><th>{employees ? "VENDEDOR" : "CATEGORÍA"}</th>{employees && <><th>CUENTA VINCULADA</th><th>SUCURSAL</th></>}<th>ESTADO</th>{canEdit && <th>ACCIONES</th>}</tr></thead>
        <tbody>{!loading && visible.map(item => <tr key={item.id}><td><div className="table-person"><span className="person-avatar">{item.name.slice(0, 1).toUpperCase()}</span><strong>{item.name}</strong></div></td>
          {employees && <><td>{item.email ?? "Sin cuenta vinculada"}</td><td>{item.branch_name??"Sin asignar"}</td></>}
          <td><span className={`status ${item.is_active ? "status-active" : "status-inactive"}`}><i/>{item.is_active ? "Activo" : "Inactivo"}</span></td>
          {canEdit && <td><button className="btn btn-light catalog-edit" aria-label={`Editar ${item.name}`} onClick={() => open(item)}><Pencil size={14}/> Editar</button></td>}
        </tr>)}</tbody>
      </table></div>
      {loading ? <div className="table-empty" role="status">Cargando registros…</div> : !visible.length && !error && <div className="table-empty">{query || status !== "all" ? "No hay coincidencias con estos filtros." : "Todavía no hay registros."}</div>}
      <div className="catalog-pagination"><span>{filtered.length} registros · Página {currentPage + 1} de {pageCount}</span><div><button className="btn btn-light" disabled={loading || currentPage === 0} onClick={() => setPage(currentPage - 1)}>Anterior</button><button className="btn btn-light" disabled={loading || currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Siguiente</button></div></div>
    </section>
    {show && <div className="modal-backdrop" onClick={close}><form className="modal" role="dialog" aria-modal="true" aria-labelledby="directory-dialog-title" onClick={e => e.stopPropagation()} onSubmit={save} onKeyDown={e => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled)'));
        const first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }}>
      <div className="modal-heading"><div><h2 id="directory-dialog-title">{editing ? "Editar" : employees ? "Nuevo" : "Nueva"} {singular}</h2><p>{editing ? "Actualiza el nombre y estado del registro." : "Completa los datos para incorporarlo al directorio."}</p></div><button type="button" className="icon-button" disabled={busy} aria-label="Cerrar formulario" onClick={close}><X size={18}/></button></div>
      <fieldset className="catalog-fields" disabled={busy}>
        {employees && !editing && <label>Cuenta vinculada<select disabled={usersLoading} value={userId} onChange={e => { setUserId(e.target.value); const user = users.find(u => String(u.id) === e.target.value); if (user) setName(user.full_name); }}><option value="">{usersLoading ? "Cargando cuentas…" : "Perfil sin cuenta vinculada"}</option>{users.map(user => <option value={user.id} key={user.id}>{user.full_name} · {user.email}</option>)}</select></label>}
        <label>{employees ? "Nombre completo" : "Nombre"}<input autoFocus required minLength={employees ? 2 : 1} maxLength={employees ? 160 : 120} readOnly={employees && !editing && !!userId} value={name} onChange={e => setName(e.target.value)}/></label>
        {employees && <BranchSelector value={branchId} onChange={setBranchId}/>}
        {editing && <label>Estado<select value={String(active)} onChange={e => setActive(e.target.value === "true")}><option value="true">Activo</option><option value="false">Inactivo</option></select></label>}
        {editing && <p className="catalog-state-note">{employees ? "La cuenta vinculada se conserva. Un vendedor inactivo no puede registrar nuevas ventas; su historial permanece disponible. El cambio de nombre modifica el perfil comercial." : "Una categoría inactiva conserva sus productos y deja de estar disponible para nuevas asignaciones. Los productos existentes mantienen su estado."}</p>}
        {editing && employees && <p className="catalog-state-note">Cuenta vinculada: {editing.email ?? "Sin cuenta"}</p>}
      </fieldset>
      {formError && <div className="inline-error" role="alert">{formError}</div>}
      <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={close}>Cancelar</button><button className="btn btn-primary" disabled={busy || usersLoading}>{busy ? "Guardando…" : "Guardar cambios"}</button></div>
    </form></div>}
  </>;
}
