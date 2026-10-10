
import DatasetExplorer from "./DatasetExplorer";
import AnalysisResult from "./AnalysisResult";
import DistributionEditor from "./DistributionEditor";
import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  type Analysis,
  type BayesEvent,
} from "./services/api";

type AnalyticsTab = "sales" | "bayes" | "random";

type RandomVariableOutcome = {
  value: number;
  probability: number;
};

const SALES_EVENT_KEYS = [
  "high_ticket",
  "multi_unit",
  "discounted",
] as const;

const CUSTOMER_EVENT_KEYS = [
  "customer_purchase",
  "repeat_customer",
] as const;

export default function AnalyticsPage({
  canRunProbability = true,
}: {
  canRunProbability?: boolean;
}) {
  const [tab, setTab] = useState<AnalyticsTab>("sales");

  const [metric, setMetric] = useState<
    "sales_total" | "units_per_sale"
  >("sales_total");

  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const [bayesEvents, setBayesEvents] = useState<BayesEvent[]>([]);
  const [eventA, setEventA] = useState("");
  const [eventB, setEventB] = useState("");

  const [variableName, setVariableName] =
    useState("Unidades por compra");

  const [outcomes, setOutcomes] = useState(
    '[{"value":0,"probability":0.2},{"value":1,"probability":0.5},{"value":2,"probability":0.3}]'
  );

  const [result, setResult] =
    useState<Record<string, unknown> | null>(null);

  const [history, setHistory] = useState<Analysis[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // Evento A: características de la venta.
  const salesEvents = bayesEvents.filter((event) =>
    (SALES_EVENT_KEYS as readonly string[]).includes(
      event.value
    )
  );

  // Evento B: características del cliente.
  const customerEvents = bayesEvents.filter((event) =>
    (CUSTOMER_EVENT_KEYS as readonly string[]).includes(
      event.value
    )
  );

  const selectedEventA = salesEvents.find(
    (event) => event.value === eventA
  );

  const selectedEventB = customerEvents.find(
    (event) => event.value === eventB
  );

  async function loadHistory() {
    try {
      setHistory(await api.analysisHistory());
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No se pudo cargar el historial"
      );
    }
  }

  async function loadBayesEvents() {
    if (!canRunProbability) return;

    setLoadingEvents(true);
    setError("");

    try {
      const events = await api.bayesEvents();

      setBayesEvents(events);

      const availableSalesEvents = events.filter((event) =>
        (SALES_EVENT_KEYS as readonly string[]).includes(
          event.value
        )
      );

      const availableCustomerEvents = events.filter((event) =>
        (CUSTOMER_EVENT_KEYS as readonly string[]).includes(
          event.value
        )
      );

      const nextA = availableSalesEvents.some(
        (event) => event.value === eventA
      )
        ? eventA
        : availableSalesEvents[0]?.value ?? "";

      const nextB = availableCustomerEvents.some(
        (event) => event.value === eventB
      )
        ? eventB
        : availableCustomerEvents[0]?.value ?? "";

      setEventA(nextA);
      setEventB(nextB);

      if (
        availableSalesEvents.length === 0 ||
        availableCustomerEvents.length === 0
      ) {
        setError(
          "No se encontraron los eventos necesarios. " +
            "Verifica las claves de eventos definidas en probability.py."
        );
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No se pudieron cargar los eventos de Bayes"
      );
    } finally {
      setLoadingEvents(false);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  useEffect(() => {
    if (tab === "bayes" && canRunProbability) {
      void loadBayesEvents();
    }
  }, [tab, canRunProbability]);

  async function submit(e: FormEvent) {
    e.preventDefault();

    setBusy(true);
    setError("");
    setResult(null);

    try {
      let value: Record<string, unknown>;

      if (tab === "sales") {
        if (start && end && start > end) {
          throw new Error(
            "La fecha inicial no puede ser posterior a la fecha final."
          );
        }

        value = await api.analyzeSales(
          metric,
          start,
          end
        );
      } else if (tab === "bayes") {
        if (!canRunProbability) {
          throw new Error(
            "No tienes permisos para ejecutar análisis de probabilidad."
          );
        }

        if (!eventA || !eventB) {
          throw new Error(
            "Debes seleccionar una característica de venta y una característica del cliente."
          );
        }

        if (
          !salesEvents.some((event) => event.value === eventA)
        ) {
          throw new Error(
            "Evento A debe ser una característica de la venta."
          );
        }

        if (
          !customerEvents.some(
            (event) => event.value === eventB
          )
        ) {
          throw new Error(
            "Evento B debe ser una característica del cliente."
          );
        }

        if (start && end && start > end) {
          throw new Error(
            "La fecha inicial no puede ser posterior a la fecha final."
          );
        }

        value = await api.bayes({
          event_a: eventA,
          event_b: eventB,
          start: start || undefined,
          end: end || undefined,
        });
      } else {
        let parsed: RandomVariableOutcome[];

        try {
          const data: unknown = JSON.parse(outcomes);

          if (
            !Array.isArray(data) ||
            !data.every(
              (item: unknown) =>
                typeof item === "object" &&
                item !== null &&
                "value" in item &&
                "probability" in item &&
                typeof item.value === "number" &&
                Number.isFinite(item.value) &&
                typeof item.probability === "number" &&
                Number.isFinite(item.probability)
            )
          ) {
            throw new Error(
              "Cada resultado debe tener un valor numérico y una probabilidad numérica."
            );
          }

          parsed = data as RandomVariableOutcome[];
        } catch (e) {
          throw new Error(
            e instanceof Error
              ? e.message
              : "Los resultados de la variable aleatoria no contienen JSON válido."
          );
        }

        if (parsed.length === 0) {
          throw new Error(
            "Debes ingresar al menos un resultado para la variable aleatoria."
          );
        }

        if (
          parsed.some(
            (item) =>
              item.probability < 0 ||
              item.probability > 1
          )
        ) {
          throw new Error(
            "Cada probabilidad debe estar entre 0 y 1."
          );
        }

        const probabilitySum = parsed.reduce(
          (sum, item) => sum + item.probability,
          0
        );

        if (Math.abs(probabilitySum - 1) > 0.000001) {
          throw new Error(
            "La suma de las probabilidades debe ser igual a 1."
          );
        }

        value = await api.randomVariable({
          name: variableName,
          outcomes: parsed,
        });
      }

      setResult(value);
      await loadHistory();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "No se pudo ejecutar el análisis"
      );
    } finally {
      setBusy(false);
    }
  }

  function changeTab(newTab: AnalyticsTab) {
    setTab(newTab);
    setResult(null);
    setError("");
  }

  function changeEventA(nextA: string) {
    setEventA(nextA);
    setResult(null);
    setError("");
  }

  function changeEventB(nextB: string) {
    setEventB(nextB);
    setResult(null);
    setError("");
  }

  return (
    <div className="analytics-layout">
      <section className="panel analysis-panel">
        <div className="panel-heading">
          <div>
            <h2>Laboratorio estadístico</h2>
            <p>
              Ejecuta cálculos reproducibles utilizando
              los datos reales registrados en SalesIA.
            </p>
          </div>
        </div>

        <div className="analysis-tabs">
          <button
            type="button"
            className={tab === "sales" ? "selected" : ""}
            disabled={busy}
            onClick={() => changeTab("sales")}
          >
            Ventas
          </button>

          {canRunProbability && (
            <>
              <button
                type="button"
                className={tab === "bayes" ? "selected" : ""}
                disabled={busy}
                onClick={() => changeTab("bayes")}
              >
                Teorema de Bayes
              </button>

              <button
                type="button"
                className={tab === "random" ? "selected" : ""}
                disabled={busy}
                onClick={() => changeTab("random")}
              >
                Variable aleatoria
              </button>
            </>
          )}
        </div>

        <form
          className="analysis-form"
          onSubmit={submit}
        >
          {tab === "sales" && (
            <>
              <label>
                Variable

                <select
                  value={metric}
                  onChange={(e) =>
                    setMetric(
                      e.target.value as typeof metric
                    )
                  }
                >
                  <option value="sales_total">
                    Monto por venta confirmada
                  </option>

                  <option value="units_per_sale">
                    Unidades por venta
                  </option>
                </select>
              </label>

              <div className="date-fields">
                <label>
                  Desde

                  <input
                    type="date"
                    value={start}
                    onChange={(e) =>
                      setStart(e.target.value)
                    }
                  />
                </label>

                <label>
                  Hasta

                  <input
                    type="date"
                    value={end}
                    onChange={(e) =>
                      setEnd(e.target.value)
                    }
                  />
                </label>
              </div>
            </>
          )}

          {tab === "bayes" && (
            <>
              <div className="form-note">
                <strong>
                  Análisis automático de probabilidades
                </strong>

                <p>
                  Selecciona una característica de la venta
                  y una característica del cliente.
                  Las probabilidades se calcularán usando
                  las ventas confirmadas del periodo.
                </p>
              </div>

              <label>
                Evento A: características de la venta

                <select
                  required
                  value={eventA}
                  disabled={
                    loadingEvents ||
                    salesEvents.length === 0
                  }
                  onChange={(e) =>
                    changeEventA(e.target.value)
                  }
                >
                  <option value="">
                    {loadingEvents
                      ? "Cargando eventos..."
                      : "Selecciona una característica de venta"}
                  </option>

                  {salesEvents.map((event) => (
                    <option
                      key={event.value}
                      value={event.value}
                    >
                      {event.label}
                    </option>
                  ))}
                </select>
              </label>

              {selectedEventA?.description && (
                <small className="form-help">
                  {selectedEventA.description}
                </small>
              )}

              <label>
                Evento B: características del cliente

                <select
                  required
                  value={eventB}
                  disabled={
                    loadingEvents ||
                    customerEvents.length === 0
                  }
                  onChange={(e) =>
                    changeEventB(e.target.value)
                  }
                >
                  <option value="">
                    {loadingEvents
                      ? "Cargando eventos..."
                      : "Selecciona una característica del cliente"}
                  </option>

                  {customerEvents.map((event) => (
                    <option
                      key={event.value}
                      value={event.value}
                    >
                      {event.label}
                    </option>
                  ))}
                </select>
              </label>

              {selectedEventB?.description && (
                <small className="form-help">
                  {selectedEventB.description}
                </small>
              )}

              <div className="date-fields">
                <label>
                  Desde

                  <input
                    type="date"
                    value={start}
                    onChange={(e) =>
                      setStart(e.target.value)
                    }
                  />
                </label>

                <label>
                  Hasta

                  <input
                    type="date"
                    value={end}
                    onChange={(e) =>
                      setEnd(e.target.value)
                    }
                  />
                </label>
              </div>

              <div className="form-note">
                El sistema calculará las probabilidades
                a partir de los registros reales. Los
                resultados disponibles dependen de la
                respuesta que entregue el backend.
              </div>
            </>
          )}

          {tab === "random" && (
            <>
              <label>
                Nombre de la variable

                <input
                  required
                  value={variableName}
                  onChange={(e) =>
                    setVariableName(e.target.value)
                  }
                />
              </label>

              <DistributionEditor
                value={outcomes}
                onChange={setOutcomes}
              />
            </>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={
              busy ||
              (tab === "bayes" &&
                (
                  loadingEvents ||
                  !eventA ||
                  !eventB ||
                  salesEvents.length === 0 ||
                  customerEvents.length === 0
                ))
            }
          >
            {busy
              ? "Calculando..."
              : tab === "bayes"
                ? "Calcular probabilidad"
                : "Ejecutar y guardar análisis"}
          </button>
        </form>

        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}

        {result && (
          <AnalysisResult value={result} />
        )}
      </section>

      <section className="panel history-panel">
        <div className="panel-heading">
          <div>
            <h2>Historial de análisis</h2>

            <p>
              Resultados persistidos en el sistema
            </p>
          </div>
        </div>

        {history.length ? (
          history.map((item) => (
            <article
              className="history-item"
              key={item.id}
            >
              <div className="history-icon">
                ∑
              </div>

              <div>
                <strong>
                  {(
                    {
                      random_variable:
                        "Variable aleatoria",

                      bayes:
                        "Teorema de Bayes",

                      descriptive:
                        "Estadística descriptiva",

                      descriptive_manual:
                        "Cálculo manual",
                    } as Record<string, string>
                  )[item.analysis_type] ??
                    item.analysis_type.replaceAll(
                      "_",
                      " "
                    )}
                </strong>

                <span>
                  {new Date(
                    item.created_at
                  ).toLocaleString("es-PE")}
                </span>

                <small>
                  {String(
                    item.result?.metric ??
                      item.parameters?.event_a ??
                      item.parameters?.name ??
                      "Análisis estadístico"
                  )}
                </small>
              </div>

              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() =>
                  setResult({
                    id: item.id,
                    analysis_id: item.id,
                    analysis_type: item.analysis_type,
                    parameters: item.parameters,
                    result: item.result,
                  })
                }
              >
                Ver resultado #{item.id}
              </button>
            </article>
          ))
        ) : (
          <div className="table-empty">
            Los análisis ejecutados aparecerán aquí.
          </div>
        )}
      </section>

      <DatasetExplorer revision={history.length} />
    </div>
  );
}
