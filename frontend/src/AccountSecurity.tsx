import { useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";
import { api, clearToken } from "./services/api";

export default function AccountSecurity(){
  const [current,setCurrent]=useState("");
  const [password,setPassword]=useState("");
  const [confirm,setConfirm]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [confirmLogout,setConfirmLogout]=useState(false);
  function endSession(){clearToken();window.dispatchEvent(new Event("salesia:session-expired"));}
  async function change(event:FormEvent){
    event.preventDefault();setError("");
    if(password!==confirm){setError("Las contraseñas nuevas no coinciden.");return;}
    if(password===current){setError("Elige una contraseña diferente de la actual.");return;}
    setBusy(true);
    try{await api.changePassword(current,password);endSession();}
    catch(e){setError(e instanceof Error?e.message:"No se pudo cambiar la contraseña.");}
    finally{setBusy(false);}
  }
  async function revoke(){
    setBusy(true);setError("");
    try{await api.logoutAll();endSession();}
    catch(e){setError(e instanceof Error?e.message:"No se pudieron cerrar las sesiones.");}
    finally{setBusy(false);}
  }
  return <div className="settings-layout">
    <section className="panel settings-form"><div className="panel-heading"><div><h2><ShieldCheck size={19}/> Cambiar contraseña</h2><p>Al guardarla se cerrarán todas tus sesiones, incluida esta.</p></div></div>
      <form onSubmit={change}>
        <label>Contraseña actual<input type="password" autoComplete="current-password" required maxLength={200} disabled={busy} value={current} onChange={e=>setCurrent(e.target.value)}/></label>
        <label>Nueva contraseña<input type="password" autoComplete="new-password" required minLength={12} maxLength={200} disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/><small>Usa al menos 12 caracteres.</small></label>
        <label>Repite la nueva contraseña<input type="password" autoComplete="new-password" required minLength={12} maxLength={200} disabled={busy} value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>
        <button className="btn btn-primary" disabled={busy}>{busy?"Procesando…":"Guardar contraseña y cerrar sesiones"}</button>
      </form>{error&&<div className="inline-error" role="alert">{error}</div>}
    </section>
    <section className="panel settings-form"><div className="panel-heading"><div><h2>Sesiones de tu cuenta</h2><p>Cierra el acceso en todos los navegadores y dispositivos donde hayas iniciado sesión.</p></div></div>
      <p className="form-note">Para volver a entrar necesitarás tu correo, empresa y contraseña. Esta acción también cierra la sesión actual.</p>
      {confirmLogout?<div><p>¿Cerrar todas tus sesiones ahora?</p><div className="modal-actions"><button className="btn btn-light" disabled={busy} onClick={()=>setConfirmLogout(false)}>Volver</button><button className="btn btn-primary" disabled={busy} onClick={revoke}>Confirmar cierre</button></div></div>:<button className="btn btn-light" disabled={busy} onClick={()=>setConfirmLogout(true)}>Cerrar todas las sesiones</button>}
    </section>
  </div>;
}
