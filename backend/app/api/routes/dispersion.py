
from math import sqrt, isfinite
from statistics import mean, median
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles

router = APIRouter(
    prefix="/probability/dispersion",
    tags=["Análisis estadístico"],
)


class DispersionRequest(BaseModel):
    variable: Literal["total", "units", "discount_total"]
    start: date | None = None
    end: date | None = None
    branch_id: int | None = Field(default=None, gt=0)


def calculate_dispersion(values: list[float]) -> dict:
    if not values:
        raise HTTPException(
            status_code=422,
            detail="No hay ventas confirmadas para los filtros seleccionados.",
        )

    if not all(isfinite(value) for value in values):
        raise HTTPException(
            status_code=422,
            detail="Los datos contienen valores numéricos no válidos.",
        )

    average = mean(values)
    variance = sum(
        (value - average) ** 2 for value in values
    ) / len(values)
    standard_deviation = sqrt(variance)

    if variance == 0:
        interpretation = (
            "Todos los valores son iguales. "
            "La variable no presenta dispersión."
        )
    elif average != 0 and standard_deviation / abs(average) > 0.5:
        interpretation = (
            "Los valores presentan una dispersión relativamente alta "
            "respecto de su media. Conviene revisar posibles valores atípicos."
        )
    else:
        interpretation = (
            "Los valores presentan dispersión respecto de su media. "
            "Interpreta el resultado considerando la escala comercial."
        )

    return {
        "observations": len(values),
        "mean": average,
        "median": median(values),
        "variance": variance,
        "standard_deviation": standard_deviation,
        "minimum": min(values),
        "maximum": max(values),
        "interpretation": interpretation,
    }


@router.post("/calculate")
def calculate(
    payload: DispersionRequest,
    db: DbSession,
    current_user=Depends(
        require_roles("admin", "manager", "analyst")
    ),
):
    if payload.start and payload.end and payload.end < payload.start:
        raise HTTPException(
            status_code=422,
            detail="La fecha final debe ser igual o posterior a la inicial.",
        )

    company_id = current_user["company_id"]

    if payload.variable == "total":
        expression = "s.total"
        variable_label = "Total de venta"
    elif payload.variable == "discount_total":
        expression = "s.discount_total"
        variable_label = "Descuento total"
    else:
        # Suma de unidades por venta; no se cuenta cada detalle
        # como una observación independiente.
        expression = "COALESCE(units.total_units, 0)"
        variable_label = "Unidades por venta"

    query = text(f"""
        SELECT {expression} AS value
        FROM sales s
        {"LEFT JOIN (SELECT company_id, sale_id, SUM(quantity) AS total_units FROM sale_details GROUP BY company_id, sale_id) units ON units.company_id = s.company_id AND units.sale_id = s.id" if payload.variable == "units" else ""}
        WHERE s.company_id = :company_id
          AND s.status = 'confirmed'
          AND (CAST(:start AS date) IS NULL
               OR s.sold_at >= CAST(:start AS date))
          AND (CAST(:end AS date) IS NULL
               OR s.sold_at < CAST(:end AS date) + INTERVAL '1 day')
          AND (CAST(:branch_id AS bigint) IS NULL
               OR s.branch_id = CAST(:branch_id AS bigint))
        ORDER BY s.sold_at, s.id
    """)

    rows = db.execute(
        query,
        {
            "company_id": company_id,
            "start": payload.start,
            "end": payload.end,
            "branch_id": payload.branch_id,
        },
    ).mappings().all()

    values = [
        float(row["value"])
        for row in rows
        if row["value"] is not None
    ]

    result = calculate_dispersion(values)

    return {
        "variable": payload.variable,
        "variable_label": variable_label,
        "start": payload.start,
        "end": payload.end,
        "branch_id": payload.branch_id,
        "data_source": "sales",
        "values": values,
        **result,
    }
