import csv
import io
from decimal import Decimal


def summarize(rows):
    confirmed = [row for row in rows if row["status"] == "confirmed"]
    currencies = sorted({row["currency"] for row in confirmed})
    totals = []
    for currency in currencies:
        amounts = sorted(Decimal(str(row["total"])) for row in confirmed if row["currency"] == currency)
        count = len(amounts)
        revenue = sum(amounts, Decimal("0"))
        center = amounts[count // 2] if count % 2 else (amounts[count // 2 - 1] + amounts[count // 2]) / 2
        totals.append({"currency": currency, "sales_count": count, "revenue": str(revenue),
                       "average_ticket": str(revenue / count), "median_ticket": str(center),
                       "minimum": str(amounts[0]), "maximum": str(amounts[-1])})
    return {"sales_count": len(confirmed), "voided_count": sum(row["status"] == "voided" for row in rows),
            "by_currency": totals}


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + value
    return value


def csv_content(snapshot):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if snapshot["report_type"] in {"products","customers","sellers"}:
        writer.writerow(["id","nombre","moneda","ventas","unidades","ingresos","promedio_por_venta"])
        for row in snapshot.get("groups",[]):
            writer.writerow([safe_cell(row[key]) for key in ("entity_id","name","currency","sales_count","units","revenue","average")])
    elif snapshot["report_type"] == "statistical":
        writer.writerow(["moneda","ventas_confirmadas","ingresos","ticket_promedio","mediana","minimo","maximo"])
        for row in snapshot["summary"]["by_currency"]:
            writer.writerow([safe_cell(row[key]) for key in ("currency","sales_count","revenue","average_ticket","median_ticket","minimum","maximum")])
    else:
        writer.writerow(["id","fecha","estado","cliente","vendedor","subtotal","descuento","impuesto","total","moneda"])
        for row in snapshot["rows"]:
            writer.writerow([safe_cell(row.get(key) or ("Cliente general" if key=="customer" else "")) for key in
                             ("id","sold_at","status","customer","seller","subtotal","discount_total","tax_total","total","currency")])
    return "\ufeff" + output.getvalue()
