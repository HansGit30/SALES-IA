import type { Insight } from "./services/api";
export default function InsightEvidence({ item }: { item:Insight }) {
  const evidence=item.evidence;
  const money=(value:unknown)=>new Intl.NumberFormat("es-PE",{style:"currency",currency:String(evidence.currency??"PEN")}).format(Number(value??0));
  if(item.rule_code==="sales_week_over_week_drop") return <div className="insight-evidence">
    <p>Semana evaluada: <strong>{String(evidence.start??"No registrada")} — {String(evidence.end??"No registrada")}</strong></p>
    <p>Comparación: {String(evidence.previous_start??"No registrada")} — {String(evidence.previous_end??"No registrada")} · Lima</p>
    <div className="stat-result-grid"><div><small>Ingresos anteriores</small><strong>{money(evidence.previous_7_days_revenue)}</strong></div><div><small>Ingresos evaluados</small><strong>{money(evidence.current_7_days_revenue)}</strong></div><div><small>Variación</small><strong>{String(evidence.change_percent)} %</strong></div></div>
    <p>Regla: caída de al menos 15 % en ventas confirmadas. El hallazgo describe una variación; no determina su causa.</p>
  </div>;
  if(item.rule_code==="inventory_low_stock"){
    const products=(Array.isArray(evidence.products)?evidence.products:[]) as {id:number;name:string;sku:string;quantity:string}[];
    const count=Number(evidence.total_count??products.length);
    return <div className="insight-evidence"><p>Inventario evaluado el {String(evidence.snapshot_day??"día del registro")}. Umbral: {String(evidence.threshold_units??5)} unidades o menos.</p><div className="table-wrap"><table><thead><tr><th>PRODUCTO</th><th>SKU</th><th>EXISTENCIAS</th></tr></thead><tbody>{products.map(product=><tr key={product.id}><td>{product.name}</td><td>{product.sku}</td><td>{product.quantity}</td></tr>)}</tbody></table></div><p>{products.length} productos mostrados de {count}. Las existencias pueden cambiar después de esta evaluación.</p></div>;
  }
  return <p className="form-note">Este registro pertenece a una regla anterior. Consulta su descripción y fecha de evaluación.</p>;
}
