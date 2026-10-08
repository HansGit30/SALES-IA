import { Activity, Boxes, FileBarChart2, ShieldCheck, ShoppingBag, Users } from "lucide-react";

const sections:Record<string,{label:string;title:string;description:string;steps:string[];icon:typeof Activity}>={
  branches:{label:"PRESENCIA TERRITORIAL",title:"Tu red, en una sola vista.",description:"Consulta ubicaciones y contactos de las sucursales de tu empresa.",steps:["Cobertura en Perú","Ubicaciones","Responsables"],icon:Boxes},
  sales:{label:"OPERACIONES",title:"Cada venta, con su detalle.",description:"Consulta transacciones, revisa pagos y accede a los recibos de tu empresa.",steps:["Detalle de artículos","Pagos registrados","Recibo imprimible"],icon:ShoppingBag},
  orders:{label:"OPERACIONES",title:"Del pedido a la venta.",description:"Organiza solicitudes y conserva los precios hasta completar la operación.",steps:["Preparación","Seguimiento","Conversión a venta"],icon:ShoppingBag},
  customers:{label:"RELACIONES COMERCIALES",title:"Tu cartera, organizada.",description:"Mantén los datos de tus clientes disponibles para las operaciones diarias.",steps:["Datos de contacto","Búsqueda","Estado del registro"],icon:Users},
  products:{label:"CATÁLOGO",title:"El detalle hace la diferencia.",description:"Organiza artículos, precios y categorías en un catálogo compartido.",steps:["Código SKU","Precio de venta","Existencias"],icon:Boxes},
  categories:{label:"CATÁLOGO",title:"Una estructura para crecer.",description:"Agrupa tus productos y facilita la búsqueda y el análisis por categoría.",steps:["Organización","Clasificación","Estado del registro"],icon:Boxes},
  employees:{label:"EQUIPO COMERCIAL",title:"Personas detrás de cada operación.",description:"Administra los perfiles del equipo vinculados a la actividad comercial.",steps:["Perfiles","Contacto","Disponibilidad"],icon:Users},
  inventory:{label:"CONTROL OPERATIVO",title:"Visibilidad de tus existencias.",description:"Consulta el stock y sigue las entradas y salidas de cada producto.",steps:["Stock actual","Movimientos","Ajustes"],icon:Boxes},
  analytics:{label:"INTELIGENCIA COMERCIAL",title:"Datos que explican tu negocio.",description:"Explora resultados estadísticos con variables definidas y cálculos reproducibles.",steps:["Estadística descriptiva","Probabilidad","Historial"],icon:Activity},
  insights:{label:"INTELIGENCIA COMERCIAL",title:"Señales para decidir.",description:"Revisa hallazgos y su evidencia para comprender cambios en ventas e inventario.",steps:["Periodo de análisis","Reglas comerciales","Evidencia"],icon:Activity},
  reports:{label:"INFORMACIÓN EJECUTIVA",title:"Resultados listos para compartir.",description:"Genera copias de tus resultados con filtros y una presentación corporativa.",steps:["Filtros del reporte","Copia archivada","CSV y PDF"],icon:FileBarChart2},
  settings:{label:"ADMINISTRACIÓN",title:"Control del espacio de trabajo.",description:"Administra accesos y consulta la trazabilidad de las acciones de tu empresa.",steps:["Usuarios","Recuperación de acceso","Auditoría"],icon:ShieldCheck},
  security:{label:"TU CUENTA",title:"El control de tu acceso.",description:"Actualiza tu contraseña y gestiona las sesiones abiertas de tu cuenta.",steps:["Contraseña personal","Cierre de sesiones","Acceso seguro"],icon:ShieldCheck}
};
export default function ModuleOverview({page}:{page:string}){
  const data=sections[page];if(!data)return null;
  return <section className={"module-overview module-overview-"+page}><div className="module-overview-icon" aria-hidden="true"><data.icon size={29} strokeWidth={1.5}/></div><div className="module-overview-copy"><span>{data.label}</span><h2>{data.title}</h2><p>{data.description}</p></div><div className="module-overview-steps">{data.steps.map((step,index)=><span key={step}><b>{String(index+1).padStart(2,"0")}</b>{step}</span>)}</div></section>;
}
