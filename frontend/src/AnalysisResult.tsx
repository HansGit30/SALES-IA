const labels: Record<string,string> = { count:"Observaciones", mean:"Media / esperanza", median:"Mediana", minimum:"Mínimo", maximum:"Máximo", variance:"Varianza", standard_deviation:"Desviación estándar", outcome_count:"Resultados posibles", probability_sum:"Suma de probabilidades" };
export default function AnalysisResult({ value }: { value: Record<string,unknown> }) {
  const data = (value.result && typeof value.result==="object" ? value.result : value) as Record<string,unknown>;
  const format=(v:unknown)=>new Intl.NumberFormat("es-PE",{maximumFractionDigits:6}).format(Number(v));
  return <div className="analysis-result" aria-live="polite"><strong>Resultado del análisis</strong>
    {"p_a_given_b" in data ? <><div className="probability-answer"><small>Probabilidad posterior · P(A|B)</small><b>{format(Number(data.p_a_given_b)*100)} %</b></div><p>Al observar «{String(data.event_b)}», la probabilidad de «{String(data.event_a)}» es {format(Number(data.p_a_given_b)*100)} % con las entradas proporcionadas.</p><p className="form-note">P(A|B) = P(B|A) × P(A) / P(B)</p></> : <><div className="stat-result-grid">{Object.entries(labels).filter(([key])=>key in data).map(([key,label])=><div key={key}><small>{label}</small><strong>{format(data[key])}</strong></div>)}</div><p className="form-note">La media resume el promedio; la mediana divide las observaciones ordenadas en dos mitades. La desviación estándar expresa la dispersión en la unidad de la variable.</p></>}
    <small>Referencia #{String(value.analysis_id ?? value.id ?? "—")} · Resultado guardado</small>
  </div>;
}
