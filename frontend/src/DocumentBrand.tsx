/** Identidad compartida de todos los documentos imprimibles de SalesIA. */
export function DocumentBrand({label,id}:{label:string;id:number}){
  return <header className="report-document-brand"><div><strong>SALES<span>IA</span></strong><small>ENTERPRISE / INTELIGENCIA COMERCIAL</small></div><div className="report-document-number">{label}<b>#{String(id).padStart(5,"0")}</b></div></header>;
}

export function DocumentFooter({reference}:{reference:string}){
  return <footer className="report-document-footer"><b>SALESIA ENTERPRISE</b><span>Documento de gestión interna · {reference}</span></footer>;
}
