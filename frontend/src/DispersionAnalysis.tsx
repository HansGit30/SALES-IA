
import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./services/api";
import "./DispersionAnalysis.css";

type DispersionResult = {
  observations: number;
  mean: number;
  median: number;
  variance: number;
  standard_deviation: number;
  minimum: number;
  maximum: number;
  interpretation: string;
  values?: number[];
};

type Variable = "total" | "units" | "discount_total";

const VARIABLES: { value: Variable; label: string }[] = [
  { value: "total", label: "Importe de venta" },
  { value: "units", label: "Unidades por venta" },
  { value: "discount_total", label: "Descuento aplicado" },
];

function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

function formatValue(variable: Variable, value: number): string {
  if (variable === "total" || variable === "discount_total") {
    return `S/ ${formatNumber(value)}`;
  }

  return formatNumber(value);
}

function MetricCard({
  title,
  value,
  description,
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <article className="disp-metric-card">
      <p className="disp-metric-title">{title}</p>
      <p className="disp-metric-value">{value}</p>
      <p className="disp-metric-description">{description}</p>
    </article>
  );
}

function ScatterChart({
  values,
  mean,
  variable,
}: {
  values: number[];
  mean: number;
  variable: Variable;
}) {
  const chart = useMemo(() => {
    const width = 720;
    const height = 300;
    const paddingLeft = 62;
    const paddingRight = 24;
    const paddingTop = 24;
    const paddingBottom = 44;

    const validValues = values.filter(Number.isFinite);

    if (validValues.length === 0) {
      return null;
    }

    const rawMin = Math.min(...validValues, mean);
    const rawMax = Math.max(...validValues, mean);
    const range = rawMax - rawMin;
    const extra =
      range === 0 ? Math.max(Math.abs(rawMax) * 0.1, 1) : range * 0.15;

    const min = rawMin - extra;
    const max = rawMax + extra;
    const plotWidth = width - paddingLeft - paddingRight;
    const plotHeight = height - paddingTop - paddingBottom;

    const y = (value: number) =>
      paddingTop + ((max - value) / (max - min)) * plotHeight;

    const points = validValues.map((value, index) => ({
      x:
        validValues.length === 1
          ? paddingLeft + plotWidth / 2
          : paddingLeft + (index / (validValues.length - 1)) * plotWidth,
      y: y(value),
      value,
      index,
    }));

    const ticks: { value: number; y: number }[] = Array.from(
      { length: 5 },
      (_, index) => {
        const value = max - (index / 4) * (max - min);
        return { value, y: y(value) };
      }
    );

    return {
      width,
      height,
      paddingLeft,
      paddingRight,
      paddingTop,
      paddingBottom,
      plotWidth,
      plotHeight,
      points,
      ticks,
      meanY: y(mean),
    };
  }, [values, mean]);

  if (!chart) {
    return (
      <div className="disp-empty-chart">
        No hay observaciones disponibles para construir el gráfico.
      </div>
    );
  }

  return (
    <div className="disp-chart-container">
      {values.length < 5 && (
        <div className="disp-sample-warning" role="status">
          <strong>Muestra pequeña:</strong> solo hay {values.length}{" "}
          {values.length === 1 ? "observación" : "observaciones"}. El gráfico
          muestra los datos disponibles, pero no permite establecer patrones
          sólidos.
        </div>
      )}

      <div className="disp-chart-scroll">
        <svg
          className="disp-scatter-svg"
          viewBox={`0 0 ${chart.width} ${chart.height}`}
          role="img"
          aria-label="Diagrama de dispersión con línea de la media"
        >
          {chart.ticks.map((tick, index) => (
            <g key={index}>
              <line
                x1={chart.paddingLeft}
                y1={tick.y}
                x2={chart.width - chart.paddingRight}
                y2={tick.y}
                className="disp-chart-grid"
              />
              <text
                x={chart.paddingLeft - 10}
                y={tick.y + 4}
                textAnchor="end"
                className="disp-axis-label"
              >
                {formatNumber(tick.value)}
              </text>
            </g>
          ))}

          <line
            x1={chart.paddingLeft}
            y1={chart.paddingTop}
            x2={chart.paddingLeft}
            y2={chart.height - chart.paddingBottom}
            className="disp-chart-axis"
          />

          <line
            x1={chart.paddingLeft}
            y1={chart.height - chart.paddingBottom}
            x2={chart.width - chart.paddingRight}
            y2={chart.height - chart.paddingBottom}
            className="disp-chart-axis"
          />

          <line
            x1={chart.paddingLeft}
            y1={chart.meanY}
            x2={chart.width - chart.paddingRight}
            y2={chart.meanY}
            className="disp-mean-line"
          />

          {chart.points.map((point) => (
            <g key={`${point.index}-${point.value}`}>
              <circle
                cx={point.x}
                cy={point.y}
                r={5}
                className="disp-scatter-point"
              >
                <title>
                  Observación {point.index + 1}:{" "}
                  {formatValue(variable, point.value)}
                </title>
              </circle>
            </g>
          ))}

          <text
            x={chart.width - chart.paddingRight}
            y={Math.max(chart.paddingTop + 12, chart.meanY - 8)}
            textAnchor="end"
            className="disp-mean-label"
          >
            Media: {formatValue(variable, mean)}
          </text>

          <text
            x={chart.paddingLeft + chart.plotWidth / 2}
            y={chart.height - 10}
            textAnchor="middle"
            className="disp-axis-title"
          >
            Número de observación
          </text>
        </svg>
      </div>

      <div className="disp-chart-legend">
        <span className="disp-legend-item">
          <span className="disp-legend-dot" />
          Observaciones
        </span>
        <span className="disp-legend-item">
          <span className="disp-legend-line" />
          Media aritmética
        </span>
      </div>
    </div>
  );
}

function Histogram({
  values,
  variable,
}: {
  values: number[];
  variable: Variable;
}) {
  const validValues = useMemo(
    () => values.filter(Number.isFinite),
    [values]
  );

  const histogram = useMemo(() => {
    if (validValues.length < 5) {
      return [];
    }

    const min = Math.min(...validValues);
    const max = Math.max(...validValues);
    const range = max - min;

    const binCount = Math.max(
      2,
      Math.min(8, Math.ceil(Math.sqrt(validValues.length)))
    );

    if (range === 0) {
      return [
        {
          start: min,
          end: max,
          count: validValues.length,
          label: formatNumber(min),
        },
      ];
    }

    const binWidth = range / binCount;

    const bins = Array.from({ length: binCount }, (_, index) => {
      const start = min + index * binWidth;
      const end =
        index === binCount - 1 ? max : min + (index + 1) * binWidth;

      return {
        start,
        end,
        count: 0,
        label: `${formatNumber(start)} – ${formatNumber(end)}`,
      };
    });

    validValues.forEach((value) => {
      let index = Math.floor((value - min) / binWidth);

      if (index >= binCount) {
        index = binCount - 1;
      }

      if (index < 0) {
        index = 0;
      }

      bins[index].count += 1;
    });

    return bins;
  }, [validValues]);

  if (validValues.length === 0) {
    return (
      <div className="disp-empty-chart">
        No hay datos suficientes para mostrar el histograma.
      </div>
    );
  }

  if (validValues.length < 5) {
    return (
      <div className="disp-small-sample">
        <div className="disp-small-sample-heading">
          <h4>Valores individuales</h4>
          <span className="disp-sample-count">
            {validValues.length}{" "}
            {validValues.length === 1 ? "dato" : "datos"}
          </span>
        </div>

        <p className="disp-small-sample-message">
          Se necesitan al menos 5 observaciones para presentar una distribución
          de frecuencias orientativa. Por ahora, se muestran los valores
          disponibles sin agruparlos en intervalos.
        </p>

        <div className="disp-sample-values">
          {validValues.map((value, index) => (
            <div className="disp-sample-value" key={`${index}-${value}`}>
              <span>Observación {index + 1}</span>
              <strong>{formatValue(variable, value)}</strong>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const maxFrequency = Math.max(...histogram.map((bin) => bin.count), 1);
  const chartHeight = 220;
  const chartWidth = 720;
  const paddingLeft = 42;
  const paddingRight = 12;
  const paddingTop = 20;
  const paddingBottom = 64;
  const plotHeight = chartHeight - paddingTop - paddingBottom;
  const plotWidth = chartWidth - paddingLeft - paddingRight;
  const barGap = 8;
  const barWidth = Math.max(
    8,
    (plotWidth - barGap * (histogram.length - 1)) / histogram.length
  );

  const tickCount = Math.min(maxFrequency + 1, 5);

  const frequencyTicks: { value: number; y: number }[] = Array.from(
    { length: tickCount },
    (_, index) => {
      const value =
        tickCount === 1
          ? maxFrequency
          : Math.round((index / (tickCount - 1)) * maxFrequency);

      return {
        value,
        y: paddingTop + plotHeight - (value / maxFrequency) * plotHeight,
      };
    }
  );

  return (
    <div className="disp-histogram-layout">
      <div className="disp-chart-scroll">
        <svg
          className="disp-histogram-svg"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          role="img"
          aria-label="Histograma de frecuencias"
        >
          {frequencyTicks.map((tick, index) => (
            <g key={`${tick.value}-${index}`}>
              <line
                x1={paddingLeft}
                y1={tick.y}
                x2={chartWidth - paddingRight}
                y2={tick.y}
                className="disp-chart-grid"
              />
              <text
                x={paddingLeft - 10}
                y={tick.y + 4}
                textAnchor="end"
                className="disp-axis-label"
              >
                {tick.value}
              </text>
            </g>
          ))}

          <line
            x1={paddingLeft}
            y1={paddingTop}
            x2={paddingLeft}
            y2={chartHeight - paddingBottom}
            className="disp-chart-axis"
          />

          <line
            x1={paddingLeft}
            y1={chartHeight - paddingBottom}
            x2={chartWidth - paddingRight}
            y2={chartHeight - paddingBottom}
            className="disp-chart-axis"
          />

          {histogram.map((bin, index) => {
            const barHeight = (bin.count / maxFrequency) * plotHeight;
            const x = paddingLeft + index * (barWidth + barGap);
            const y = paddingTop + plotHeight - barHeight;

            return (
              <g key={`${bin.start}-${bin.end}-${index}`}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={Math.max(0, barHeight)}
                  rx={4}
                  className="disp-histogram-bar"
                >
                  <title>
                    Intervalo {bin.label}: {bin.count}{" "}
                    {bin.count === 1 ? "observación" : "observaciones"}
                  </title>
                </rect>

                <text
                  x={x + barWidth / 2}
                  y={Math.max(paddingTop + 12, y - 6)}
                  textAnchor="middle"
                  className="disp-bar-count"
                >
                  {bin.count}
                </text>

                <text
                  x={x + barWidth / 2}
                  y={chartHeight - paddingBottom + 16}
                  textAnchor="middle"
                  className="disp-bin-label"
                >
                  {formatNumber(bin.start)}
                </text>

                {index === histogram.length - 1 && (
                  <text
                    x={x + barWidth / 2}
                    y={chartHeight - paddingBottom + 31}
                    textAnchor="middle"
                    className="disp-bin-label"
                  >
                    {formatNumber(bin.end)}
                  </text>
                )}
              </g>
            );
          })}

          <text
            x={16}
            y={paddingTop + plotHeight / 2}
            textAnchor="middle"
            transform={`rotate(-90 16 ${paddingTop + plotHeight / 2})`}
            className="disp-axis-title"
          >
            Frecuencia
          </text>

          <text
            x={paddingLeft + plotWidth / 2}
            y={chartHeight - 8}
            textAnchor="middle"
            className="disp-axis-title"
          >
            Valores de la variable
          </text>
        </svg>
      </div>

      <p className="disp-histogram-note">
        Cada barra representa la cantidad de observaciones que cae dentro de
        un intervalo. La última barra incluye el valor máximo observado.
      </p>
    </div>
  );
}

export default function DispersionAnalysis() {
  const [variable, setVariable] = useState<Variable>("total");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [result, setResult] = useState<DispersionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const values = useMemo(() => {
    if (result?.values && result.values.length > 0) {
      return result.values.filter(Number.isFinite);
    }

    return [];
  }, [result]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (startDate && endDate && startDate > endDate) {
      setError("La fecha inicial no puede ser posterior a la fecha final.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.dispersion({
        variable,
        start: startDate || undefined,
        end: endDate || undefined,
      });

      setResult(response as DispersionResult);
    } catch (err) {
      console.error("Error al calcular la dispersión:", err);
      setResult(null);
      setError(
        "No se pudo calcular la dispersión. Verifica la conexión con el servidor y vuelve a intentarlo."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="disp-page">


      <section className="disp-panel">
        <div className="disp-section-heading">
          <div>
            <h2>Parámetros del análisis</h2>
            <p>Selecciona la variable y el período que deseas evaluar.</p>
          </div>
        </div>

        <form className="disp-filter-form" onSubmit={handleSubmit}>
          <div className="disp-form-field">
            <label htmlFor="disp-variable">Variable de análisis</label>
            <select
              id="disp-variable"
              value={variable}
              onChange={(event) =>
                setVariable(event.target.value as Variable)
              }
            >
              {VARIABLES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div className="disp-form-field">
            <label htmlFor="disp-start-date">Fecha inicial</label>
            <input
              id="disp-start-date"
              type="date"
              value={startDate}
              max={endDate || undefined}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>

          <div className="disp-form-field">
            <label htmlFor="disp-end-date">Fecha final</label>
            <input
              id="disp-end-date"
              type="date"
              value={endDate}
              min={startDate || undefined}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </div>

          <button
            type="submit"
            className="disp-submit-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="disp-spinner" />
                Calculando...
              </>
            ) : (
              "Calcular dispersión"
            )}
          </button>
        </form>

        {error && (
          <div className="disp-error-message" role="alert">
            {error}
          </div>
        )}
      </section>

      {loading && (
        <section className="disp-loading-panel" aria-live="polite">
          <span className="disp-spinner disp-spinner-large" />
          <p>Procesando los datos de ventas...</p>
        </section>
      )}

      {!loading && result && (
        <>
          <section className="disp-metrics-grid">
            <MetricCard
              title="Observaciones"
              value={formatNumber(result.observations, 0)}
              description="Registros incluidos en el análisis"
            />

            <MetricCard
              title="Media"
              value={formatValue(variable, result.mean)}
              description="Promedio de los valores observados"
            />

            <MetricCard
              title="Mediana"
              value={formatValue(variable, result.median)}
              description="Valor central de los datos ordenados"
            />

            <MetricCard
              title="Varianza"
              value={formatNumber(result.variance)}
              description="Medida de dispersión cuadrática"
            />

            <MetricCard
              title="Desviación estándar"
              value={formatValue(variable, result.standard_deviation)}
              description="Dispersión respecto a la media"
            />

            <MetricCard
              title="Mínimo"
              value={formatValue(variable, result.minimum)}
              description="Menor valor registrado"
            />

            <MetricCard
              title="Máximo"
              value={formatValue(variable, result.maximum)}
              description="Mayor valor registrado"
            />
          </section>

          <section className="disp-panel">
            <div className="disp-section-heading">
              <div>
                <h2>Dispersión de las observaciones</h2>
                <p>
                  Cada punto representa una observación. La línea discontinua
                  indica la media calculada.
                </p>
              </div>
            </div>

            {values.length > 0 ? (
              <ScatterChart
                values={values}
                mean={result.mean}
                variable={variable}
              />
            ) : (
              <div className="disp-info-message">
                El servidor devolvió las métricas estadísticas, pero no una
                lista de valores individuales. Para mostrar los puntos del
                gráfico, la respuesta de la API debe incluir la propiedad{" "}
                <code>values</code>.
              </div>
            )}
          </section>

          <section className="disp-panel">
            <div className="disp-section-heading">
              <div>
                <h2>Distribución de frecuencias</h2>
                <p>
                  Observa cómo se distribuyen los valores en intervalos.
                </p>
              </div>
            </div>

            <Histogram values={values} variable={variable} />
          </section>

          <section className="disp-panel disp-interpretation-panel">
            <div className="disp-interpretation-icon" aria-hidden="true">
              i
            </div>

            <div>
              <h2>Interpretación estadística</h2>
              <p>
                {result.interpretation ||
                  "No se recibió una interpretación para estos resultados."}
              </p>

              {result.observations < 5 && (
                <p className="disp-interpretation-warning">
                  El análisis contiene menos de cinco observaciones. Interpreta
                  los resultados con cautela y evita generalizar a partir de
                  una muestra tan pequeña.
                </p>
              )}
            </div>
          </section>

          <section className="disp-panel">
            <div className="disp-section-heading">
              <div>
                <h2>Rango de los datos</h2>
                <p>Diferencia entre el mayor y el menor valor observado.</p>
              </div>
            </div>

            <div className="disp-range-summary">
              <div className="disp-range-endpoint">
                <span>Valor mínimo</span>
                <strong>{formatValue(variable, result.minimum)}</strong>
              </div>

              <div className="disp-range-track">
                <div className="disp-range-line" />
                <span className="disp-range-marker disp-range-marker-min" />
                <span className="disp-range-marker disp-range-marker-max" />
              </div>

              <div className="disp-range-endpoint disp-range-endpoint-right">
                <span>Valor máximo</span>
                <strong>{formatValue(variable, result.maximum)}</strong>
              </div>
            </div>

            <div className="disp-range-footer">
              <span>Amplitud del rango</span>
              <strong>
                {formatValue(variable, result.maximum - result.minimum)}
              </strong>
            </div>
          </section>
        </>
      )}

      {!loading && !result && !error && (
        <section className="disp-empty-state">
          <div className="disp-empty-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            >
              <path d="M4 19V5M4 19H21" />
              <path d="M7 15l4-5 3 2 5-7" />
              <circle cx="7" cy="15" r="1" />
              <circle cx="11" cy="10" r="1" />
              <circle cx="14" cy="12" r="1" />
              <circle cx="19" cy="5" r="1" />
            </svg>
          </div>

          <h2>Listo para analizar tus ventas</h2>
          <p>
            Selecciona una variable y, si lo deseas, un período. Después,
            presiona <strong>Calcular dispersión</strong> para obtener las
            métricas y los gráficos.
          </p>
        </section>
      )}
    </main>
  );
}
