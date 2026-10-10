import json
import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles

router = APIRouter(prefix="/probability", tags=["Probabilidad"])


# ============================================================
# BAYES AUTOMÁTICO
# ============================================================

class BayesRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    event_a: str = Field(min_length=1, max_length=80)
    event_b: str = Field(min_length=1, max_length=80)
    start: str | None = None
    end: str | None = None


BAYES_EVENTS = {
    "high_ticket": {
        "label": "Venta de alto valor",
        "description": "Venta cuyo total es igual o superior al ticket promedio del periodo.",
    },
    "multi_unit": {
        "label": "Venta con varias unidades",
        "description": "Venta cuya cantidad total de unidades es igual o superior al promedio de unidades por venta.",
    },
    "discounted": {
        "label": "Venta con descuento",
        "description": "Venta que tiene un descuento mayor que cero.",
    },
    "customer_purchase": {
        "label": "Venta con cliente identificado",
        "description": "Venta asociada a un cliente registrado.",
    },
    "repeat_customer": {
        "label": "Cliente recurrente",
        "description": "Venta realizada por un cliente que registra al menos dos ventas confirmadas en el periodo.",
    },
}


def build_event_sql(event_name: str) -> str:
    """
    Convierte un evento seleccionado en una expresión SQL.

    IMPORTANTE:
    Los valores no vienen del usuario como SQL.
    Solo se aceptan las claves definidas en BAYES_EVENTS.
    """

    events = {
        "high_ticket": "total >= avg_ticket",
        "multi_unit": "units >= avg_units",
        "discounted": "discount_total > 0",
        "customer_purchase": "customer_id IS NOT NULL",
        "repeat_customer": "customer_id IS NOT NULL AND customer_sales >= 2",
    }

    expression = events.get(event_name)

    if expression is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_bayes_event",
                "message": f"Evento no soportado: {event_name}",
            },
        )

    return expression


@router.get("/bayes/events")
def bayes_events(
    user: dict = Depends(
        require_roles("admin", "manager", "analyst")
    ),
):
    """
    Devuelve los eventos que SalesIA puede calcular automáticamente.
    """

    return [
        {
            "value": key,
            "label": value["label"],
            "description": value["description"],
        }
        for key, value in BAYES_EVENTS.items()
    ]


@router.post("/bayes")
def bayes(
    payload: BayesRequest,
    db: DbSession,
    user: dict = Depends(
        require_roles("admin", "manager", "analyst")
    ),
):
    """
    Calcula Bayes usando datos reales de ventas.

    Ya NO recibe:
        P(A)
        P(B|A)
        P(B)

    SalesIA obtiene esas probabilidades directamente
    desde las ventas confirmadas de la empresa.
    """

    if payload.event_a not in BAYES_EVENTS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_bayes_event",
                "message": f"Evento A no soportado: {payload.event_a}",
            },
        )

    if payload.event_b not in BAYES_EVENTS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_bayes_event",
                "message": f"Evento B no soportado: {payload.event_b}",
            },
        )

    event_a_sql = build_event_sql(payload.event_a)
    event_b_sql = build_event_sql(payload.event_b)

    date_filter = ""

    if payload.start:
        date_filter += """
            AND s.sold_at >= CAST(:start AS date)
        """

    if payload.end:
        date_filter += """
            AND s.sold_at < CAST(:end AS date) + INTERVAL '1 day'
        """

    query = text(
        f"""
        WITH sale_units AS (
            SELECT
                s.id,
                s.customer_id,
                s.total,
                s.discount_total,
                s.sold_at,

                COALESCE(
                    SUM(sd.quantity),
                    0
                ) AS units

            FROM sales s

            LEFT JOIN sale_details sd
                ON sd.company_id = s.company_id
                AND sd.sale_id = s.id

            WHERE
                s.company_id = :company_id
                AND s.status = 'confirmed'
                {date_filter}

            GROUP BY
                s.id,
                s.customer_id,
                s.total,
                s.discount_total,
                s.sold_at
        ),

        sales_enriched AS (
            SELECT
                *,
                AVG(total) OVER () AS avg_ticket,
                AVG(units) OVER () AS avg_units,

                COUNT(*) OVER (
                    PARTITION BY customer_id
                ) AS customer_sales

            FROM sale_units
        ),

        classified AS (
            SELECT
                *,
                CASE
                    WHEN {event_a_sql}
                    THEN 1
                    ELSE 0
                END AS event_a,

                CASE
                    WHEN {event_b_sql}
                    THEN 1
                    ELSE 0
                END AS event_b

            FROM sales_enriched
        )

        SELECT
            COUNT(*) AS total_observations,

            COALESCE(
                SUM(event_a),
                0
            ) AS event_a_count,

            COALESCE(
                SUM(event_b),
                0
            ) AS event_b_count,

            COALESCE(
                SUM(
                    CASE
                        WHEN event_a = 1
                        AND event_b = 1
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS both_count,

            COALESCE(
                AVG(total),
                0
            ) AS average_ticket,

            COALESCE(
                AVG(units),
                0
            ) AS average_units

        FROM classified
        """
    )

    params = {
        "company_id": user["company_id"],
        "start": payload.start,
        "end": payload.end,
    }

    row = db.execute(query, params).mappings().one()

    total = int(row["total_observations"])
    event_a_count = int(row["event_a_count"])
    event_b_count = int(row["event_b_count"])
    both_count = int(row["both_count"])

    if total == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "insufficient_sales_data",
                "message": (
                    "No existen ventas confirmadas para calcular "
                    "Bayes con los filtros seleccionados."
                ),
            },
        )

    if event_a_count == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "event_a_without_observations",
                "message": (
                    "El evento A no aparece en las ventas confirmadas "
                    "del periodo seleccionado."
                ),
            },
        )

    if event_b_count == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "event_b_without_observations",
                "message": (
                    "El evento B no aparece en las ventas confirmadas "
                    "del periodo seleccionado."
                ),
            },
        )

    # --------------------------------------------------------
    # Probabilidades obtenidas de los datos reales
    # --------------------------------------------------------

    p_a = event_a_count / total
    p_b = event_b_count / total

    p_b_given_a = both_count / event_a_count

    p_a_given_b = (
        both_count / event_b_count
        if event_b_count > 0
        else 0.0
    )

    # Validación matemática
    calculated = (
        p_b_given_a * p_a / p_b
        if p_b > 0
        else 0.0
    )

    calculated = max(0.0, min(1.0, calculated))

    # --------------------------------------------------------
    # Información del análisis
    # --------------------------------------------------------

    event_a_label = BAYES_EVENTS[payload.event_a]["label"]
    event_b_label = BAYES_EVENTS[payload.event_b]["label"]

    interpretation = (
        f"Según las ventas confirmadas del periodo analizado, "
        f"cuando se observa el evento B ({event_b_label}), "
        f"la probabilidad de que también ocurra el evento A "
        f"({event_a_label}) es "
        f"{p_a_given_b:.4f} ({p_a_given_b * 100:.2f}%)."
    )

    params_output = {
        "event_a": payload.event_a,
        "event_b": payload.event_b,
        "event_a_label": event_a_label,
        "event_b_label": event_b_label,
        "start": payload.start,
        "end": payload.end,
        "data_source": "confirmed_sales",
        "total_observations": total,
    }

    output = {
        **params_output,

        "p_a": p_a,
        "p_b_given_a": p_b_given_a,
        "p_b": p_b,
        "p_a_given_b": p_a_given_b,

        "event_a_count": event_a_count,
        "event_b_count": event_b_count,
        "both_count": both_count,

        "average_ticket": float(
            row["average_ticket"] or 0
        ),

        "average_units": float(
            row["average_units"] or 0
        ),

        "interpretation": interpretation,
    }

    try:
        # ----------------------------------------------------
        # Dataset analítico
        # ----------------------------------------------------

        dataset_id = db.execute(
            text(
                """
                INSERT INTO datasets(
                    company_id,
                    name,
                    source,
                    filters,
                    created_by
                )
                VALUES (
                    :company_id,
                    'Análisis Bayes automático',
                    'sales',
                    CAST(:filters AS jsonb),
                    :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "filters": json.dumps(params_output),
                "user_id": user["id"],
            },
        ).scalar_one()

        # ----------------------------------------------------
        # Análisis estadístico
        # ----------------------------------------------------

        analysis_id = db.execute(
            text(
                """
                INSERT INTO statistical_analyses(
                    company_id,
                    dataset_id,
                    analysis_type,
                    parameters,
                    result,
                    created_by
                )
                VALUES (
                    :company_id,
                    :dataset_id,
                    'bayes',
                    CAST(:parameters AS jsonb),
                    CAST(:result AS jsonb),
                    :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "dataset_id": dataset_id,
                "parameters": json.dumps(params_output),
                "result": json.dumps(output),
                "user_id": user["id"],
            },
        ).scalar_one()

        # ----------------------------------------------------
        # Registro específico de Bayes
        # ----------------------------------------------------

        db.execute(
            text(
                """
                INSERT INTO bayes_analyses(
                    company_id,
                    analysis_id,
                    event_a,
                    event_b,
                    p_a,
                    p_b_given_a,
                    p_b,
                    p_a_given_b
                )
                VALUES (
                    :company_id,
                    :analysis_id,
                    :event_a,
                    :event_b,
                    :p_a,
                    :p_b_given_a,
                    :p_b,
                    :p_a_given_b
                )
                """
            ),
            {
                "company_id": user["company_id"],
                "analysis_id": analysis_id,
                "event_a": event_a_label,
                "event_b": event_b_label,
                "p_a": p_a,
                "p_b_given_a": p_b_given_a,
                "p_b": p_b,
                "p_a_given_b": p_a_given_b,
            },
        )

        # ----------------------------------------------------
        # Auditoría
        # ----------------------------------------------------

        db.execute(
            text(
                """
                INSERT INTO audit_logs(
                    company_id,
                    user_id,
                    action,
                    entity_type,
                    entity_id,
                    details
                )
                VALUES (
                    :company_id,
                    :user_id,
                    'analytics.bayes_created',
                    'statistical_analysis',
                    :analysis_id,
                    CAST(:details AS jsonb)
                )
                """
            ),
            {
                "company_id": user["company_id"],
                "user_id": user["id"],
                "analysis_id": str(analysis_id),
                "details": json.dumps(
                    {
                        "source": "confirmed_sales",
                        "dataset_id": dataset_id,
                        "event_a": payload.event_a,
                        "event_b": payload.event_b,
                        "start": payload.start,
                        "end": payload.end,
                        "observations": total,
                    }
                ),
            },
        )

        db.commit()

        return {
            "analysis_id": analysis_id,
            "dataset_id": dataset_id,
            **output,
        }

    except Exception:
        db.rollback()
        raise


# ============================================================
# VARIABLE ALEATORIA
# ============================================================

class Outcome(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    value: float = Field(
        gt=-1e12,
        lt=1e12,
    )

    probability: float = Field(
        ge=0,
        le=1,
    )


class RandomVariableRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    name: str = Field(
        min_length=1,
        max_length=120,
    )

    outcomes: list[Outcome] = Field(
        min_length=1,
        max_length=1000,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @model_validator(mode="after")
    def probabilities_sum_to_one(self):
        if len({x.value for x in self.outcomes}) != len(
            self.outcomes
        ):
            raise ValueError(
                "Cada valor debe aparecer una sola vez; "
                "combina sus probabilidades"
            )

        if not math.isclose(
            math.fsum(
                x.probability
                for x in self.outcomes
            ),
            1.0,
            rel_tol=0,
            abs_tol=1e-8,
        ):
            raise ValueError(
                "Las probabilidades de todos los resultados "
                "deben sumar 1"
            )

        expectation = math.fsum(
            x.value * x.probability
            for x in self.outcomes
        )

        variance = math.fsum(
            (x.value - expectation) ** 2
            * x.probability
            for x in self.outcomes
        )

        if (
            not math.isfinite(variance)
            or variance >= 1e14
        ):
            raise ValueError(
                "La varianza excede la capacidad de almacenamiento; "
                "utiliza una unidad de menor escala"
            )

        return self


@router.post(
    "/random-variables/analyze",
    status_code=201,
)
def analyze_random_variable(
    payload: RandomVariableRequest,
    db: DbSession,
    user: dict = Depends(
        require_roles("admin", "manager", "analyst")
    ),
):
    mean = math.fsum(
        item.value * item.probability
        for item in payload.outcomes
    )

    variance = math.fsum(
        ((item.value - mean) ** 2)
        * item.probability
        for item in payload.outcomes
    )

    std_dev = math.sqrt(variance)

    params = {
        "distribution": "discrete",
        "outcomes": [
            item.model_dump()
            for item in payload.outcomes
        ],
    }

    output = {
        "mean": mean,
        "variance": variance,
        "standard_deviation": std_dev,
        "outcome_count": len(payload.outcomes),
        "probability_sum": sum(
            item.probability
            for item in payload.outcomes
        ),
    }

    try:
        variable_id = db.execute(
            text(
                """
                INSERT INTO random_variables(
                    company_id,
                    name,
                    distribution,
                    parameters,
                    description,
                    created_by
                )
                VALUES (
                    :company_id,
                    :name,
                    'discrete',
                    CAST(:parameters AS jsonb),
                    :description,
                    :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "name": payload.name,
                "parameters": json.dumps(params),
                "description": payload.description,
                "user_id": user["id"],
            },
        ).scalar_one()

        dataset_id = db.execute(
            text(
                """
                INSERT INTO datasets(
                    company_id,
                    name,
                    source,
                    filters,
                    created_by
                )
                VALUES (
                    :company_id,
                    :name,
                    'manual',
                    CAST(:filters AS jsonb),
                    :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "name": f"Variable aleatoria: {payload.name}",
                "filters": json.dumps(
                    {"random_variable_id": variable_id}
                ),
                "user_id": user["id"],
            },
        ).scalar_one()

        dataset_var_id = db.execute(
            text(
                """
                INSERT INTO dataset_variables(
                    company_id,
                    dataset_id,
                    name,
                    data_type
                )
                VALUES (
                    :company_id,
                    :dataset_id,
                    :name,
                    'quantitative_discrete'
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "dataset_id": dataset_id,
                "name": payload.name,
            },
        ).scalar_one()

        for index, outcome in enumerate(
            payload.outcomes
        ):
            db.execute(
                text(
                    """
                    INSERT INTO observations(
                        company_id,
                        dataset_id,
                        variable_id,
                        numeric_value,
                        source_ref
                    )
                    VALUES (
                        :company_id,
                        :dataset_id,
                        :variable_id,
                        :value,
                        :source_ref
                    )
                    """
                ),
                {
                    "company_id": user["company_id"],
                    "dataset_id": dataset_id,
                    "variable_id": dataset_var_id,
                    "value": Decimal(
                        str(outcome.value)
                    ),
                    "source_ref": str(index),
                },
            )

        analysis_id = db.execute(
            text(
                """
                INSERT INTO statistical_analyses(
                    company_id,
                    dataset_id,
                    analysis_type,
                    parameters,
                    result,
                    created_by
                )
                VALUES (
                    :company_id,
                    :dataset_id,
                    'random_variable',
                    CAST(:parameters AS jsonb),
                    CAST(:result AS jsonb),
                    :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "dataset_id": dataset_id,
                "parameters": json.dumps(params),
                "result": json.dumps(output),
                "user_id": user["id"],
            },
        ).scalar_one()

        for metric, value in [
            ("expectation", mean),
            ("variance", variance),
            ("standard_deviation", std_dev),
        ]:
            db.execute(
                text(
                    """
                    INSERT INTO statistical_results(
                        company_id,
                        analysis_id,
                        variable_id,
                        metric,
                        numeric_value,
                        details
                    )
                    VALUES (
                        :company_id,
                        :analysis_id,
                        :variable_id,
                        :metric,
                        :value,
                        CAST(:details AS jsonb)
                    )
                    """
                ),
                {
                    "company_id": user["company_id"],
                    "analysis_id": analysis_id,
                    "variable_id": dataset_var_id,
                    "metric": metric,
                    "value": Decimal(str(value)),
                    "details": "{}",
                },
            )

        db.execute(
            text(
                """
                INSERT INTO audit_logs(
                    company_id,
                    user_id,
                    action,
                    entity_type,
                    entity_id,
                    details
                )
                VALUES (
                    :company,
                    :user,
                    'analytics.random_variable_created',
                    'statistical_analysis',
                    :id,
                    CAST(:details AS jsonb)
                )
                """
            ),
            {
                "company": user["company_id"],
                "user": user["id"],
                "id": str(analysis_id),
                "details": json.dumps(
                    {
                        "dataset_id": dataset_id,
                        "random_variable_id": variable_id,
                    }
                ),
            },
        )

        db.commit()

        return {
            "random_variable_id": variable_id,
            "analysis_id": analysis_id,
            "name": payload.name,
            **output,
        }

    except Exception:
        db.rollback()
        raise





# ============================================================
# VARIANZA Y DESVIACIÓN ESTÁNDAR CON VENTAS REALES
# ============================================================

from datetime import date
from statistics import median


class DispersionRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    variable: str = Field(
        min_length=1,
        max_length=40,
    )
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError(
                "La fecha inicial no puede ser posterior a la fecha final."
            )
        return self


DISPERSION_VARIABLES = {
    "total": {
        "label": "Importe total por venta",
        "unit": "PEN",
        "sql_column": "total",
        "description": "Importes totales de ventas confirmadas.",
    },
    "units": {
        "label": "Unidades por venta",
        "unit": "unidades",
        "sql_column": "units",
        "description": "Suma de cantidades de los detalles de cada venta.",
    },
    "discount_total": {
        "label": "Descuento por venta",
        "unit": "PEN",
        "sql_column": "discount_total",
        "description": "Descuentos registrados en ventas confirmadas.",
    },
}


@router.post("/dispersion/calculate", status_code=201)
def calculate_dispersion(
    payload: DispersionRequest,
    db: DbSession,
    user: dict = Depends(
        require_roles("admin", "manager", "analyst")
    ),
):
    """
    Calcula medidas de dispersión usando las ventas confirmadas
    de la empresa autenticada y guarda el análisis.
    """

    if payload.variable not in DISPERSION_VARIABLES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_dispersion_variable",
                "message": (
                    "Variable no soportada. Utiliza total, units "
                    "o discount_total."
                ),
            },
        )

    variable_info = DISPERSION_VARIABLES[payload.variable]

    date_filter = ""
    if payload.start:
        date_filter += " AND s.sold_at >= :start "
    if payload.end:
        date_filter += (
            " AND s.sold_at < CAST(:end AS date) + INTERVAL '1 day' "
        )

    query = text(
        f"""
        WITH sale_units AS (
            SELECT
                s.id,
                s.company_id,
                s.total,
                s.discount_total,
                s.sold_at,
                COALESCE(SUM(sd.quantity), 0) AS units
            FROM sales s
            LEFT JOIN sale_details sd
                ON sd.company_id = s.company_id
                AND sd.sale_id = s.id
            WHERE
                s.company_id = :company_id
                AND s.status = 'confirmed'
                {date_filter}
            GROUP BY
                s.id,
                s.company_id,
                s.total,
                s.discount_total,
                s.sold_at
        )
        SELECT
            id,
            total,
            discount_total,
            units,
            sold_at
        FROM sale_units
        ORDER BY sold_at, id
        """
    )

    params = {"company_id": user["company_id"]}
    if payload.start:
        params["start"] = payload.start
    if payload.end:
        params["end"] = payload.end

    rows = db.execute(query, params).mappings().all()

    if not rows:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "insufficient_sales_data",
                "message": (
                    "No hay ventas confirmadas para calcular "
                    "la dispersión con las fechas seleccionadas."
                ),
            },
        )

    # Los datos provienen de la consulta a la base de datos.
    values = [
        float(row[variable_info["sql_column"]])
        for row in rows
    ]

    observations_count = len(values)
    mean = math.fsum(values) / observations_count
    median_value = float(median(values))

    # Varianza poblacional: se divide entre N, no entre N - 1.
    variance = (
        math.fsum((value - mean) ** 2 for value in values)
        / observations_count
    )
    standard_deviation = math.sqrt(variance)
    minimum = min(values)
    maximum = max(values)

    variable_label = variable_info["label"]
    unit = variable_info["unit"]

    interpretation = (
        f"Se analizaron {observations_count} ventas confirmadas. "
        f"El promedio de {variable_label.lower()} es "
        f"{mean:.2f} {unit}. La desviación estándar es "
        f"{standard_deviation:.2f} {unit}; representa la dispersión "
        f"de los valores alrededor del promedio."
    )

    filters = {
        "source": "confirmed_sales",
        "variable": payload.variable,
        "start": payload.start.isoformat() if payload.start else None,
        "end": payload.end.isoformat() if payload.end else None,
        "observations": observations_count,
        "variance_type": "population",
    }

    output = {
        "variable": payload.variable,
        "variable_label": variable_label,
        "start": filters["start"],
        "end": filters["end"],
        "data_source": "confirmed_sales",
        "observations": observations_count,
        "mean": mean,
        "median": median_value,
        "variance": variance,
        "standard_deviation": standard_deviation,
        "minimum": minimum,
        "maximum": maximum,
        "interpretation": interpretation,
    }

    try:
        dataset_id = db.execute(
            text(
                """
                INSERT INTO datasets (
                    company_id, name, source, filters, created_by
                )
                VALUES (
                    :company_id, :name, 'sales',
                    CAST(:filters AS jsonb), :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "name": f"Dispersión: {variable_label}",
                "filters": json.dumps(filters),
                "user_id": user["id"],
            },
        ).scalar_one()

        variable_id = db.execute(
            text(
                """
                INSERT INTO dataset_variables (
                    company_id, dataset_id, name, data_type, unit
                )
                VALUES (
                    :company_id, :dataset_id, :name,
                    'quantitative_continuous', :unit
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "dataset_id": dataset_id,
                "name": variable_label,
                "unit": unit,
            },
        ).scalar_one()

        # Conserva los valores individuales usados en el cálculo.
        for row, value in zip(rows, values):
            db.execute(
                text(
                    """
                    INSERT INTO observations (
                        company_id, dataset_id, variable_id,
                        numeric_value, observed_at, source_ref
                    )
                    VALUES (
                        :company_id, :dataset_id, :variable_id,
                        :value, :observed_at, :source_ref
                    )
                    """
                ),
                {
                    "company_id": user["company_id"],
                    "dataset_id": dataset_id,
                    "variable_id": variable_id,
                    "value": Decimal(str(value)),
                    "observed_at": row["sold_at"],
                    "source_ref": str(row["id"]),
                },
            )

        analysis_id = db.execute(
            text(
                """
                INSERT INTO statistical_analyses (
                    company_id, dataset_id, analysis_type,
                    parameters, result, created_by
                )
                VALUES (
                    :company_id, :dataset_id, 'dispersion',
                    CAST(:parameters AS jsonb),
                    CAST(:result AS jsonb), :user_id
                )
                RETURNING id
                """
            ),
            {
                "company_id": user["company_id"],
                "dataset_id": dataset_id,
                "parameters": json.dumps(filters),
                "result": json.dumps(output, allow_nan=False),
                "user_id": user["id"],
            },
        ).scalar_one()

        for metric, value in [
            ("mean", mean),
            ("median", median_value),
            ("variance", variance),
            ("standard_deviation", standard_deviation),
            ("minimum", minimum),
            ("maximum", maximum),
            ("observations", observations_count),
        ]:
            db.execute(
                text(
                    """
                    INSERT INTO statistical_results (
                        company_id, analysis_id, variable_id,
                        metric, numeric_value, details
                    )
                    VALUES (
                        :company_id, :analysis_id, :variable_id,
                        :metric, :value, CAST(:details AS jsonb)
                    )
                    """
                ),
                {
                    "company_id": user["company_id"],
                    "analysis_id": analysis_id,
                    "variable_id": variable_id,
                    "metric": metric,
                    "value": Decimal(str(value)),
                    "details": json.dumps({"unit": unit}),
                },
            )

        db.execute(
            text(
                """
                INSERT INTO audit_logs (
                    company_id, user_id, action,
                    entity_type, entity_id, details
                )
                VALUES (
                    :company_id, :user_id,
                    'analytics.dispersion_created',
                    'statistical_analysis', :entity_id,
                    CAST(:details AS jsonb)
                )
                """
            ),
            {
                "company_id": user["company_id"],
                "user_id": user["id"],
                "entity_id": str(analysis_id),
                "details": json.dumps({
                    "dataset_id": dataset_id,
                    **filters,
                }),
            },
        )

        db.commit()

        return {
            "analysis_id": analysis_id,
            "dataset_id": dataset_id,
            **output,
        }

    except Exception:
        db.rollback()
        raise
