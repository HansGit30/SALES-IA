
import { useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  CircleDollarSign,
  ClipboardList,
  Eye,
  Package,
  Plus,
  Search,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";

import {
  api,
  type Product,
  type Sale,
  type SaleDetail,
} from "./services/api";

import SaleForm from "./SaleForm";
import SaleReceipt from "./SaleReceipt";
import "./SalesHistory.css";

const PAGE_SIZE = 25;

export default function SalesHistory({
  canCreate = false,
}: {
  canCreate?: boolean;
}) {
  const [rows, setRows] = useState<Sale[]>([]);
  const [products, setProducts] = useState<Product[]>([]);

  const [page, setPage] = useState(0);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [status, setStatus] = useState("");

  const [productSearch, setProductSearch] = useState("");
  const [showAllProducts, setShowAllProducts] = useState(false);

  const [selectedProduct, setSelectedProduct] =
    useState<Product | null>(null);

  const [productSales, setProductSales] = useState<SaleDetail[]>([]);
  const [productSalesLoading, setProductSalesLoading] = useState(false);
  const [productSalesError, setProductSalesError] = useState("");

  const [show, setShow] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  const [error, setError] = useState("");
  const [productError, setProductError] = useState("");

  const [loading, setLoading] = useState(true);
  const [productsLoading, setProductsLoading] = useState(true);

  const [revision, setRevision] = useState(0);

  // ==========================================================
  // HISTORIAL PRINCIPAL
  // ==========================================================

  useEffect(() => {
    let current = true;

    if (start && end && end < start) {
      setError("La fecha final debe ser igual o posterior a la inicial.");
      setRows([]);
      setLoading(false);

      return () => {
        current = false;
      };
    }

    setError("");
    setLoading(true);

    api
      .salesPage(page * PAGE_SIZE, start, end, status)
      .then((data) => {
        if (current) setRows(data);
      })
      .catch((e: unknown) => {
        if (!current) return;

        setRows([]);
        setError(
          e instanceof Error
            ? e.message
            : "No se pudieron cargar las ventas.",
        );
      })
      .finally(() => {
        if (current) setLoading(false);
      });

    return () => {
      current = false;
    };
  }, [page, start, end, status, revision]);

  // ==========================================================
  // CATÁLOGO DE PRODUCTOS
  // ==========================================================

  useEffect(() => {
    let current = true;

    setProductsLoading(true);
    setProductError("");

    api
      .products("", 0, 100)
      .then((data) => {
        if (current) setProducts(data);
      })
      .catch((e: unknown) => {
        if (!current) return;

        setProducts([]);
        setProductError(
          e instanceof Error
            ? e.message
            : "No se pudieron cargar los productos.",
        );
      })
      .finally(() => {
        if (current) setProductsLoading(false);
      });

    return () => {
      current = false;
    };
  }, [revision]);

  // ==========================================================
  // FORMATOS
  // ==========================================================

  const money = (sale: Sale | SaleDetail) =>
    new Intl.NumberFormat("es-PE", {
      style: "currency",
      currency: sale.currency || "PEN",
    }).format(Number(sale.total || 0));

  const productMoney = (value: string | number) =>
    new Intl.NumberFormat("es-PE", {
      style: "currency",
      currency: "PEN",
    }).format(Number(value || 0));

  const formatDate = (date: string) =>
    new Date(date).toLocaleString("es-PE", {
      dateStyle: "medium",
      timeStyle: "short",
    });

  // ==========================================================
  // FILTRAR PRODUCTOS
  // ==========================================================

  const visibleProducts = useMemo(() => {
    const query = productSearch.trim().toLocaleLowerCase("es");

    return products
      .filter((product) => {
        if (!showAllProducts && !product.is_active) return false;
        if (!query) return true;

        return (
          product.name.toLocaleLowerCase("es").includes(query) ||
          (product.sku ?? "").toLocaleLowerCase("es").includes(query)
        );
      })
      .slice(0, 100);
  }, [products, productSearch, showAllProducts]);

  // ==========================================================
  // CONSULTAR COMPRAS DE UN PRODUCTO
  //
  // Los resultados se muestran en la tabla principal.
  // No se crea una tabla adicional.
  // ==========================================================

  const viewProductCustomers = async (product: Product) => {
    // Si se vuelve a pulsar el producto seleccionado, se quita
    // el filtro y se recupera el historial habitual.
    if (selectedProduct?.id === product.id) {
      setSelectedProduct(null);
      setProductSales([]);
      setProductSalesError("");
      setProductSalesLoading(false);
      setPage(0);
      return;
    }

    setSelectedProduct(product);
    setProductSales([]);
    setProductSalesError("");
    setProductSalesLoading(true);
    setPage(0);

    try {
      const matchingSales: SaleDetail[] = [];
      let offset = 0;

      while (true) {
        const sales = await api.salesPage(
          offset,
          start,
          end,
          "confirmed",
        );

        const pageSales = sales.slice(0, PAGE_SIZE);

        const details = await Promise.all(
          pageSales.map(async (sale) => {
            try {
              return await api.sale(sale.id);
            } catch {
              return null;
            }
          }),
        );

        for (const detail of details) {
          if (
            detail &&
            detail.status === "confirmed" &&
            detail.items.some(
              (item) => item.product_id === product.id,
            )
          ) {
            matchingSales.push(detail);
          }
        }

        // El endpoint puede devolver una fila adicional
        // para indicar que existe una página siguiente.
        if (sales.length <= PAGE_SIZE) break;

        offset += PAGE_SIZE;
      }

      setProductSales(matchingSales);
    } catch (e: unknown) {
      setProductSalesError(
        e instanceof Error
          ? e.message
          : "No se pudieron consultar las compras del producto.",
      );
    } finally {
      setProductSalesLoading(false);
    }
  };

  // ==========================================================
  // DATOS QUE APARECEN EN LA TABLA PRINCIPAL
  // ==========================================================

  const displayedSales: (Sale | SaleDetail)[] = selectedProduct
    ? productSales
    : rows.slice(0, PAGE_SIZE);

  const confirmedSales = displayedSales.filter(
    (sale) => sale.status === "confirmed",
  );

  const voidedSales = displayedSales.filter(
    (sale) => sale.status === "voided",
  );

  const confirmedTotal = confirmedSales.reduce(
    (sum, sale) => sum + Number(sale.total || 0),
    0,
  );

  const currency = confirmedSales[0]?.currency || "PEN";

  const formatTotal = (value: number) =>
    new Intl.NumberFormat("es-PE", {
      style: "currency",
      currency,
    }).format(value);

  // ==========================================================
  // FILTROS
  // ==========================================================

  const clearFilters = () => {
    setStart("");
    setEnd("");
    setStatus("");
    setPage(0);
    setSelectedProduct(null);
    setProductSales([]);
    setProductSalesError("");
  };

  // ==========================================================
  // INTERFAZ
  // ==========================================================

  return (
    <section className="sales-page" aria-busy={loading}>
      <header className="sales-heading">
        <div>
          <p className="sales-eyebrow">Gestión comercial</p>
          <h1>Ventas</h1>
          <p className="sales-description">
            Consulta las operaciones comerciales de tu empresa.
          </p>
        </div>
      </header>

      {/* INDICADORES */}

      <div className="sales-summary">
        <article className="sales-summary-card">
          <div className="sales-summary-top">
            <span>Ventas confirmadas cargadas</span>
            <span className="sales-summary-icon">
              <ClipboardList size={18} />
            </span>
          </div>

          <p className="sales-summary-value">
            {loading || productSalesLoading
              ? "—"
              : confirmedSales.length}
          </p>

          <p className="sales-summary-detail">
            {selectedProduct
              ? "Ventas confirmadas del producto seleccionado"
              : "En la página actual"}
          </p>
        </article>

        <article className="sales-summary-card">
          <div className="sales-summary-top">
            <span>Importe confirmado cargado</span>
            <span className="sales-summary-icon">
              <CircleDollarSign size={18} />
            </span>
          </div>

          <p className="sales-summary-value">
            {loading || productSalesLoading
              ? "—"
              : formatTotal(confirmedTotal)}
          </p>

          <p className="sales-summary-detail">
            {selectedProduct
              ? "Importe total de las ventas que contienen el producto"
              : "Suma de las ventas confirmadas de esta página"}
          </p>
        </article>

        <article className="sales-summary-card">
          <div className="sales-summary-top">
            <span>Periodo consultado</span>
            <span className="sales-summary-icon">
              <CalendarDays size={18} />
            </span>
          </div>

          <p className="sales-summary-value sales-summary-period">
            {start || end
              ? `${start || "Inicio"} — ${end || "Actualidad"}`
              : "Todos"}
          </p>

          <p className="sales-summary-detail">
            Según los filtros seleccionados
          </p>
        </article>
      </div>

      {/* HISTORIAL Y PANEL LATERAL */}

      <div className="sales-layout">
        <section className="panel data-panel sales-history-panel">
          <div className="data-toolbar">
            <div>
              <strong>Historial de ventas</strong>
              <p>
                {selectedProduct
                  ? `Ventas confirmadas que incluyen ${selectedProduct.name}.`
                  : "Consulta el detalle, los pagos y el recibo de cada operación."}
              </p>
            </div>

            <div className="sales-history-toolbar-actions">
              {selectedProduct && (
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => {
                    setSelectedProduct(null);
                    setProductSales([]);
                    setProductSalesError("");
                    setPage(0);
                  }}
                >
                  <X size={14} />
                  Quitar producto
                </button>
              )}

              {canCreate && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setShow(true)}
                >
                  <Plus size={16} />
                  Nueva venta
                </button>
              )}
            </div>
          </div>

          {selectedProduct && (
            <div className="sales-selected-product-note">
              <Package size={15} />
              <span>
                Producto: <strong>{selectedProduct.name}</strong>
                {" · "}
                {selectedProduct.sku}
              </span>
              <span className="sales-selected-product-count">
                {productSalesLoading
                  ? "Consultando…"
                  : `${productSales.length} ventas`}
              </span>
            </div>
          )}

          {error && !selectedProduct && (
            <div className="inline-error" role="alert">
              <span>{error}</span>
              <button
                type="button"
                className="text-button"
                onClick={() => setRevision((value) => value + 1)}
              >
                Reintentar
              </button>
            </div>
          )}

          {productSalesError && selectedProduct && (
            <div className="inline-error" role="alert">
              <span>{productSalesError}</span>
              <button
                type="button"
                className="text-button"
                onClick={() => void viewProductCustomers(selectedProduct)}
              >
                Reintentar
              </button>
            </div>
          )}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>VENTA</th>
                  <th>FECHA</th>
                  <th>CLIENTE</th>
                  <th>VENDEDOR</th>
                  {selectedProduct && <th>CANTIDAD</th>}
                  <th>TOTAL</th>
                  <th>ESTADO</th>
                  <th>ACCIONES</th>
                </tr>
              </thead>

              <tbody>
                {!loading &&
                  !productSalesLoading &&
                  displayedSales.map((sale) => {
                    const item = selectedProduct
                      ? (sale as SaleDetail).items.find(
                          (line) =>
                            line.product_id === selectedProduct.id,
                        )
                      : undefined;

                    return (
                      <tr key={sale.id}>
                        <td>
                          <strong>
                            #{String(sale.id).padStart(5, "0")}
                          </strong>
                        </td>

                        <td>{formatDate(sale.sold_at)}</td>

                        <td>
                          {sale.customer_name ?? "Cliente general"}
                        </td>

                        <td>{sale.seller_name}</td>

                        {selectedProduct && (
                          <td>{item?.quantity ?? "—"}</td>
                        )}

                        <td className="sales-total-cell">
                          {selectedProduct && item
                            ? new Intl.NumberFormat("es-PE", {
                                style: "currency",
                                currency: sale.currency || "PEN",
                              }).format(Number(item.line_total))
                            : money(sale)}
                        </td>

                        <td>
                          <span
                            className={`status ${
                              sale.status === "confirmed"
                                ? "status-active"
                                : "status-inactive"
                            }`}
                          >
                            {sale.status === "confirmed"
                              ? "Confirmada"
                              : sale.status === "voided"
                                ? "Anulada"
                                : sale.status}
                          </span>
                        </td>

                        <td>
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => setSelected(sale.id)}
                          >
                            Ver recibo
                          </button>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>

          {(loading || productSalesLoading) && (
            <div className="table-empty" role="status">
              {productSalesLoading
                ? "Consultando las compras del producto…"
                : "Cargando ventas…"}
            </div>
          )}

          {!loading &&
            !productSalesLoading &&
            !error &&
            !productSalesError &&
            displayedSales.length === 0 && (
              <div className="table-empty">
                {selectedProduct
                  ? "No se encontraron ventas confirmadas con este producto en el periodo consultado."
                  : "No hay ventas que coincidan con estos filtros."}
              </div>
            )}

          {!selectedProduct && (
            <div className="sales-table-footer">
              <div className="sales-table-counts">
                <span>
                  <i className="sales-dot sales-dot-confirmed" />
                  {loading ? "—" : confirmedSales.length} confirmadas
                </span>

                <span>
                  <i className="sales-dot sales-dot-voided" />
                  {loading ? "—" : voidedSales.length} anuladas
                </span>
              </div>

              <div className="catalog-pagination">
                <span>
                  Página {page + 1} · {PAGE_SIZE} ventas por página
                </span>

                <div>
                  <button
                    type="button"
                    className="btn btn-light"
                    disabled={loading || page === 0}
                    onClick={() => setPage((value) => value - 1)}
                  >
                    Anterior
                  </button>

                  <button
                    type="button"
                    className="btn btn-light"
                    disabled={loading || rows.length <= PAGE_SIZE}
                    onClick={() => setPage((value) => value + 1)}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </div>
          )}

          {selectedProduct && !productSalesLoading && !productSalesError && (
            <div className="sales-table-footer">
              <div className="sales-table-counts">
                <span>
                  <i className="sales-dot sales-dot-confirmed" />
                  {confirmedSales.length} confirmadas
                </span>
                <span>
                  <Users size={14} />
                  Clientes asociados a las ventas mostradas
                </span>
              </div>
            </div>
          )}
        </section>

        {/* PANEL LATERAL */}

        <aside className="sales-sidebar">
          {/* FILTROS */}

          <section className="sales-side-card">
            <div className="sales-side-heading">
              <div className="sales-side-title-icon">
                <SlidersHorizontal size={17} />
              </div>

              <div>
                <h3>Filtros de consulta</h3>
                <p>Personaliza las operaciones mostradas.</p>
              </div>
            </div>

            <div className="sales-filter-fields">
              <label>
                <span>Estado</span>
                <select
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value);
                    setPage(0);
                    setSelectedProduct(null);
                    setProductSales([]);
                  }}
                >
                  <option value="">Todos</option>
                  <option value="confirmed">Confirmadas</option>
                  <option value="voided">Anuladas</option>
                </select>
              </label>

              <label>
                <span>Desde</span>
                <input
                  type="date"
                  value={start}
                  max={end || undefined}
                  onChange={(event) => {
                    setStart(event.target.value);
                    setPage(0);
                    setSelectedProduct(null);
                    setProductSales([]);
                  }}
                />
              </label>

              <label>
                <span>Hasta</span>
                <input
                  type="date"
                  value={end}
                  min={start || undefined}
                  onChange={(event) => {
                    setEnd(event.target.value);
                    setPage(0);
                    setSelectedProduct(null);
                    setProductSales([]);
                  }}
                />
              </label>
            </div>

            <button
              type="button"
              className="sales-clear-button"
              onClick={clearFilters}
            >
              <X size={14} />
              Limpiar filtros
            </button>
          </section>

          {/* LISTADO COMPACTO DE PRODUCTOS */}

          <section className="sales-side-card sales-products-card">
            <div className="sales-side-heading">
              <div className="sales-side-title-icon">
                <Package size={18} />
              </div>

              <div>
                <h3>Listado de productos</h3>
                <p>
                  {productsLoading
                    ? "Cargando catálogo…"
                    : `${visibleProducts.length} productos mostrados`}
                </p>
              </div>
            </div>

            <label className="sales-product-search">
              <Search size={16} />
              <input
                type="search"
                value={productSearch}
                onChange={(event) => setProductSearch(event.target.value)}
                placeholder="Buscar producto..."
                aria-label="Buscar producto por nombre o código"
              />

              {productSearch && (
                <button
                  type="button"
                  onClick={() => setProductSearch("")}
                  aria-label="Limpiar búsqueda de productos"
                >
                  <X size={14} />
                </button>
              )}
            </label>

            <button
              type="button"
              className={`sales-product-scope ${
                !showAllProducts ? "is-selected" : ""
              }`}
              onClick={() => setShowAllProducts(false)}
            >
              <CheckCircle2 size={15} />
              Productos activos
            </button>

            <button
              type="button"
              className={`sales-product-scope ${
                showAllProducts ? "is-selected" : ""
              }`}
              onClick={() => setShowAllProducts(true)}
            >
              <Package size={15} />
              Todos los productos
            </button>

            {productError && (
              <div className="sales-product-error" role="alert">
                <span>{productError}</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setRevision((value) => value + 1)}
                >
                  Reintentar
                </button>
              </div>
            )}

            <div className="sales-product-list">
              {productsLoading && (
                <p className="sales-product-message">
                  Cargando productos…
                </p>
              )}

              {!productsLoading &&
                !productError &&
                visibleProducts.map((product) => (
                  <article
                    className={`sales-product-item ${
                      selectedProduct?.id === product.id
                        ? "sales-product-item-selected"
                        : ""
                    }`}
                    key={product.id}
                  >
                    <div className="sales-product-compact">
                      <span className="sales-product-icon">
                        <Package size={15} />
                      </span>

                      <span className="sales-product-info">
                        <strong title={product.name}>
                          {product.name}
                        </strong>
                        <span>
                          {product.sku}
                          {product.category_name
                            ? ` · ${product.category_name}`
                            : ""}
                        </span>
                      </span>

                      <span className="sales-product-meta">
                        <strong>
                          {productMoney(product.unit_price)}
                        </strong>
                        <span>Stock: {product.stock ?? "—"}</span>
                      </span>

                      <button
                        type="button"
                        className="sales-product-eye-button"
                        onClick={() => void viewProductCustomers(product)}
                        aria-label={
                          selectedProduct?.id === product.id
                            ? `Quitar filtro de ${product.name}`
                            : `Ver ventas de ${product.name}`
                        }
                        aria-pressed={selectedProduct?.id === product.id}
                        title={
                          selectedProduct?.id === product.id
                            ? "Quitar filtro"
                            : "Ver ventas de este producto"
                        }
                      >
                        <Eye size={15} />
                      </button>
                    </div>
                  </article>
                ))}

              {!productsLoading &&
                !productError &&
                visibleProducts.length === 0 && (
                  <p className="sales-product-message">
                    No se encontraron productos.
                  </p>
                )}
            </div>
          </section>

          {/* RESUMEN FINANCIERO */}

          <section className="sales-side-card">
            <div className="sales-side-heading">
              <div className="sales-side-title-icon">
                <CircleDollarSign size={18} />
              </div>

              <div>
                <h3>Resumen financiero</h3>
                <p>Importes de las ventas cargadas.</p>
              </div>
            </div>

            <div className="sales-finance-row">
              <div>
                <span>Total compras</span>
                <small>No disponible en el historial de ventas</small>
              </div>
              <strong>—</strong>
            </div>

            <div className="sales-finance-row sales-finance-total">
              <div>
                <span>Total ventas</span>
                <small>
                  {selectedProduct
                    ? "Ventas confirmadas con el producto"
                    : "Confirmadas en esta página"}
                </small>
              </div>

              <strong>
                {loading || productSalesLoading
                  ? "—"
                  : formatTotal(confirmedTotal)}
              </strong>
            </div>

            <div className="sales-finance-progress">
              <span
                style={{
                  width:
                    confirmedSales.length + voidedSales.length > 0
                      ? `${
                          (confirmedSales.length /
                            (confirmedSales.length + voidedSales.length)) *
                          100
                        }%`
                      : "0%",
                }}
              />
            </div>
          </section>
        </aside>
      </div>

      {/* FORMULARIOS EXISTENTES */}

      {show && (
        <SaleForm
          onClose={() => setShow(false)}
          onCreated={() => {
            setShow(false);
            setPage(0);
            setSelectedProduct(null);
            setProductSales([]);
            setRevision((value) => value + 1);
          }}
        />
      )}

      {selected !== null && (
        <SaleReceipt
          id={selected}
          canVoid={canCreate}
          onClose={() => setSelected(null)}
          onVoided={() => setRevision((value) => value + 1)}
        />
      )}
    </section>
  );
}
