import { useEffect, useState } from "react";
import { api, type InventoryMovement, type InventoryRow } from "./services/api";

const types: Record<string, string> = { adjustment: "Ajuste", sale: "Venta", sale_void: "Anulación", opening: "Apertura" };
export default function InventoryHistory({ products, revision,branch="" }: { products: InventoryRow[]; revision: number;branch?:string }) {
  const [rows, setRows] = useState<InventoryMovement[]>([]);
  const [product, setProduct] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    setLoading(true); setError("");
    api.inventoryMovements(product ? Number(product) : undefined, page * 25,branch)
      .then(data => { if (current) setRows(data); })
      .catch(e => { if (current) { setRows([]); setError(e instanceof Error ? e.message : "No se pudieron cargar los movimientos"); } })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [product, page, revision, retry,branch]);
  return <section className="panel data-panel inventory-history" aria-busy={loading}>
    <div className="data-toolbar"><div><strong>Historial de movimientos</strong><p>Entradas, salidas y ajustes con su responsable y motivo</p></div>
      <select className="directory-status" aria-label="Filtrar movimientos por producto" value={product} onChange={e => { setProduct(e.target.value); setPage(0); }}><option value="">Todos los productos, incluidos inactivos</option>{products.map(row => <option key={row.product_id} value={row.product_id}>{row.name} · {row.sku}</option>)}</select>
    </div>
    {error && <div className="inline-error" role="alert">{error} <button className="text-button" onClick={() => setRetry(v => v + 1)}>Reintentar</button></div>}
    <div className="table-wrap"><table><thead><tr><th>FECHA</th><th>PRODUCTO</th><th>OPERACIÓN</th><th>CANTIDAD</th><th>RESPONSABLE</th><th>MOTIVO / REFERENCIA</th></tr></thead>
      <tbody>{!loading && rows.slice(0, 25).map(row => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString("es-PE")}</td><td><strong>{row.product_name}</strong></td><td>{types[row.movement_type] ?? row.movement_type}</td><td><span className={`status ${Number(row.quantity_delta) > 0 ? "status-active" : "status-inactive"}`}>{Number(row.quantity_delta) > 0 ? "+" : ""}{Number(row.quantity_delta).toLocaleString("es-PE", { maximumFractionDigits: 3 })}</span></td><td>{row.created_by}</td><td>{row.reason || "—"}{row.sale_id && <small className="movement-reference">Venta #{row.sale_id}</small>}</td></tr>)}</tbody>
    </table></div>
    {loading ? <div className="table-empty" role="status">Cargando movimientos…</div> : !rows.length && !error && <div className="table-empty">No hay movimientos en esta página.</div>}
    <div className="catalog-pagination"><span>Página {page + 1} · 25 movimientos por página</span><div><button className="btn btn-light" disabled={loading || page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button><button className="btn btn-light" disabled={loading || rows.length <= 25} onClick={() => setPage(p => p + 1)}>Siguiente</button></div></div>
  </section>;
}
