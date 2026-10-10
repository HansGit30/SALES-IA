const labels: Record<string, string> = {
  count: "Observaciones",
  mean: "Media / esperanza",
  median: "Mediana",
  minimum: "Mínimo",
  maximum: "Máximo",
  variance: "Varianza",
  standard_deviation: "Desviación estándar",
  outcome_count: "Resultados posibles",
  probability_sum: "Suma de probabilidades",
};

const formatNumber = (value: unknown) => {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return new Intl.NumberFormat("es-PE", {
    maximumFractionDigits: 6,
  }).format(number);
};

const formatPercent = (value: unknown) => {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${formatNumber(number * 100)} %`;
};

export default function AnalysisResult({
  value,
}: {
  value: Record<string, unknown>;
}) {
  const data = (
    value.result && typeof value.result === "object"
      ? value.result
      : value
  ) as Record<string, unknown>;

  const isBayes =
    "p_a_given_b" in data &&
    "p_b_given_a" in data &&
    "p_a" in data &&
    "p_b" in data;

  const eventA = String(
    data.event_a_label ?? data.event_a ?? "Evento A"
  );

  const eventB = String(
    data.event_b_label ?? data.event_b ?? "Evento B"
  );

  const analysisId =
    value.analysis_id ?? value.id ?? "—";

  return (
    <div className="analysis-result" aria-live="polite">
      <strong>Resultado del análisis</strong>

      {isBayes ? (
        <>
          <div className="probability-answer">
            <small>Probabilidad posterior · P(A|B)</small>

            <b>{formatPercent(data.p_a_given_b)}</b>

            <p>
              Si se observa «{eventB}», la probabilidad
              de que también ocurra «{eventA}» es{" "}
              <strong>
                {formatPercent(data.p_a_given_b)}
              </strong>
              , según las ventas confirmadas del periodo
              analizado.
            </p>
          </div>

          <div className="stat-result-grid">
            <div>
              <small>P(A) · Probabilidad inicial de A</small>
              <strong>{formatPercent(data.p_a)}</strong>
            </div>

            <div>
              <small>P(B) · Probabilidad de B</small>
              <strong>{formatPercent(data.p_b)}</strong>
            </div>

            <div>
              <small>P(B|A) · B dado A</small>
              <strong>{formatPercent(data.p_b_given_a)}</strong>
            </div>

            <div>
              <small>P(A|B) · A dado B</small>
              <strong>{formatPercent(data.p_a_given_b)}</strong>
            </div>

            <div>
              <small>Ventas analizadas</small>
              <strong>
                {formatNumber(data.total_observations)}
              </strong>
            </div>

            <div>
              <small>Ventas con A y B</small>
              <strong>{formatNumber(data.both_count)}</strong>
            </div>

            <div>
              <small>Ventas que cumplen A</small>
              <strong>{formatNumber(data.event_a_count)}</strong>
            </div>

            <div>
              <small>Ventas que cumplen B</small>
              <strong>{formatNumber(data.event_b_count)}</strong>
            </div>

            <div>
              <small>Ticket promedio del periodo</small>
              <strong>
                {formatNumber(data.average_ticket)}
              </strong>
            </div>

            <div>
              <small>Unidades promedio por venta</small>
              <strong>
                {formatNumber(data.average_units)}
              </strong>
            </div>
          </div>

          <div className="form-note">
            <strong>Interpretación</strong>

            <p>
              {typeof data.interpretation === "string"
                ? data.interpretation
                : `La probabilidad de A dado B es ${formatPercent(
                    data.p_a_given_b
                  )}.`}
            </p>

            <p>
              Fórmula: P(A|B) = P(B|A) × P(A) / P(B).
            </p>

            <small>
              Fuente:{" "}
              {String(data.data_source ?? "datos del análisis")}
              . Las probabilidades se calculan a partir de
              las frecuencias observadas, no de valores
              ingresados manualmente.
            </small>
          </div>
        </>
      ) : (
        <>
          <div className="stat-result-grid">
            {Object.entries(labels)
              .filter(([key]) => key in data)
              .map(([key, label]) => (
                <div key={key}>
                  <small>{label}</small>
                  <strong>{formatNumber(data[key])}</strong>
                </div>
              ))}
          </div>

          <p className="form-note">
            La media resume el promedio; la mediana divide
            las observaciones ordenadas en dos mitades.
            La varianza y la desviación estándar describen
            la dispersión de los resultados.
          </p>
        </>
      )}

      <small>
        Referencia #{String(analysisId)}
        {" · "}
        Resultado del análisis
      </small>
    </div>
  );
}