
import { fetchWithReadRetry } from "./http";

const API =
  import.meta.env.VITE_API_BASE_URL ??
  "https://sales-ia-afew.onrender.com/api/v1";

const TOKEN_KEY = "salesia.access_token";

// ============================================================
// AUTENTICACIÓN / TOKEN
// ============================================================

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ============================================================
// PDF
// ============================================================

export async function downloadPdf(
  kind: "reports" | "sales",
  id: number
) {
  let response: Response;

  try {
    response = await fetchWithReadRetry(
      `${API}/${kind}/${id}/pdf`,
      {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      }
    );
  } catch {
    throw new Error(
      "No se pudo conectar con el servidor para descargar el PDF."
    );
  }

  if (response.status === 401) {
    clearToken();

    window.dispatchEvent(
      new Event("salesia:session-expired")
    );
  }

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => null);

    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : body?.detail?.message ??
            "No se pudo generar el PDF. Inténtalo nuevamente."
    );
  }

  const url = URL.createObjectURL(
    await response.blob()
  );

  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = `salesia-${
    kind === "sales" ? "venta" : "reporte"
  }-${id}.pdf`;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(
    () => URL.revokeObjectURL(url),
    60000
  );
}

// ============================================================
// REQUEST BASE
// ============================================================

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  let response: Response;

  try {
    response = await fetchWithReadRetry(
      `${API}${path}`,
      {
        ...options,

        headers: {
          "Content-Type": "application/json",

          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),

          ...options.headers,
        },
      }
    );
  } catch {
    throw new Error(
      "No se pudo conectar con el servidor. Comprueba que el backend esté iniciado y vuelve a intentar; tus datos permanecen en el formulario."
    );
  }

  if (response.status === 401) {
    clearToken();

    window.dispatchEvent(
      new Event("salesia:session-expired")
    );
  }

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => null);

    const detail = body?.detail;

    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (item: { msg?: string }) =>
                  item.msg ?? "Dato inválido"
              )
              .join(" · ")
          : detail?.message ??
              `Error ${response.status}`
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================
// TIPOS GENERALES
// ============================================================

export type PricingRules = {
  default_tax_percent: string;
  default_discount_percent: string;
  allow_pricing_override: boolean;
};

export type SessionUser = {
  id: number;
  company_id: number;
  email: string;
  full_name: string;
  role: string;
  must_change_password?: boolean;
};

export type Category = {
  id: number;
  name: string;
  is_active: boolean;
};

export type Customer = {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
};

export type Product = {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  unit_price: string;
  is_active: boolean;
  category_id?: number | null;
  category_name: string | null;
  stock: string;
};

export type Summary = {
  customer_count: number;
  transaction_count: number;
  revenue: string;
  average_ticket: string;
  median_ticket: string;
  currency: string;
};

export type Breakdown = {
  customers: {
    id: number | null;
    name: string;
    currency: string;
    transactions: number;
    revenue: string;
    average_ticket: string;
    purchase_days: number;
    last_purchase: string;
  }[];

  products: {
    id: number;
    name: string;
    currency: string;
    units: string;
    revenue: string;
    share_percent: string;
    transactions: number;
  }[];

  sellers: {
    id: number;
    name: string;
    currency: string;
    average_ticket: string;
    revenue: string;
    transactions: number;
  }[];

  frequencies: {
    currency: string;
    band: number;
    frequency: number;
  }[];

  ranking_limit: number;
};

export type DashboardFilters = {
  branch_id?: string;
  employee_id?: string;
  product_id?: string;
  category_id?: string;
};

export type DashboardOptions = {
  employees: {
    id: number;
    name: string;
    is_active: boolean;
  }[];

  products: {
    id: number;
    name: string;
    sku: string;
    category_id: number | null;
    is_active: boolean;
  }[];

  categories: {
    id: number;
    name: string;
    is_active: boolean;
  }[];
};

// ============================================================
// DASHBOARD
// ============================================================

function dashboardQuery(
  start: string,
  end: string,
  filters: DashboardFilters
) {
  const params = new URLSearchParams({
    start,
    end,
  });

  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      params.set(key, value);
    }
  }

  return params.toString();
}

// ============================================================
// VENTAS / INVENTARIO / PEDIDOS
// ============================================================

export type Sale = {
  id: number;
  status: string;
  currency: string;
  total: string;
  sold_at: string;
  customer_name: string | null;
  seller_name: string;
};

export type InventoryRow = {
  product_id: number;
  sku: string;
  name: string;
  quantity: string;
  updated_at: string;
};

export type Order = {
  id: number;
  status:
    | "pending"
    | "converted"
    | "cancelled";

  customer_name?: string | null;
  author_name?: string;
  total: string;
  currency: string;
  sale_id: number | null;
  cancel_reason: string | null;
  created_at: string;
};

export type OrderDetail = Order & {
  items: {
    product_id: number;
    name: string;
    sku: string;
    quantity: string;
    unit_price: string;
    line_total: string;
  }[];
};

export type SaleDetail = Sale & {
  company_name: string;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  void_reason: string | null;
  voided_at: string | null;

  items: {
    product_id: number;
    name: string;
    sku: string;
    quantity: string;
    unit_price: string;
    discount: string;
    tax: string;
    line_total: string;
  }[];

  payments: {
    method: string;
    amount: string;
    status: string;
    paid_at: string | null;
  }[];
};

// ============================================================
// BAYES AUTOMÁTICO
// ============================================================

export type BayesEvent = {
  value: string;
  label: string;
  description: string;
};

export type BayesResult = {
  analysis_id: number;
  dataset_id: number;

  event_a: string;
  event_b: string;

  event_a_label: string;
  event_b_label: string;

  start: string | null;
  end: string | null;

  data_source: string;

  total_observations: number;

  p_a: number;
  p_b_given_a: number;
  p_b: number;
  p_a_given_b: number;

  event_a_count: number;
  event_b_count: number;
  both_count: number;

  average_ticket: number;
  average_units: number;

  interpretation: string;
};

// ============================================================
// ANALYTICS / PROBABILIDAD
// ============================================================

export type Analysis = {
  id: number;
  dataset_id: number;
  analysis_type: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: string;
};

// ============================================================
// VARIANZA Y DESVIACIÓN ESTÁNDAR
// ============================================================

export type DispersionVariable =
  | "total"
  | "units"
  | "discount_total";

export type DispersionRequest = {
  variable: DispersionVariable;
  start?: string;
  end?: string;
  branch_id?: number;
};

export type DispersionResult = {
  analysis_id: number;
  dataset_id: number;
  variable: DispersionVariable;
  variable_label: string;
  start: string | null;
  end: string | null;
  data_source: string;
  observations: number;
  mean: number;
  median: number;
  variance: number;
  standard_deviation: number;
  minimum: number;
  maximum: number;
  interpretation: string;
};

// ============================================================
// API
// ============================================================

export const api = {
  // ----------------------------------------------------------
  // CLIENTES
  // ----------------------------------------------------------

  customerHistory: (
    id: number,
    offset = 0
  ) =>
    request<CustomerHistoryData>(
      `/customers/${id}/history?offset=${offset}`
    ),

  // ----------------------------------------------------------
  // SUCURSALES
  // ----------------------------------------------------------

  branchSummary: (id: number) =>
    request<{
      staff: number;
      units: string;
      products: number;
      sales_visible: boolean;
      sales: {
        currency: string;
        transactions: number;
        revenue: string;
      }[];
    }>(`/branches/${id}/summary`),

  branches: () =>
    request<Branch[]>("/branches"),

  saveBranch: (
    payload: BranchInput,
    id?: number
  ) =>
    request<Branch>(
      id ? `/branches/${id}` : "/branches",
      {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // USUARIOS / SEGURIDAD
  // ----------------------------------------------------------

  resetUserPassword: (
    id: number,
    admin_password: string,
    temporary_password: string
  ) =>
    request<void>(
      `/users/${id}/reset-password`,
      {
        method: "POST",
        body: JSON.stringify({
          admin_password,
          temporary_password,
        }),
      }
    ),

  changePassword: (
    current_password: string,
    new_password: string
  ) =>
    request<void>(
      "/auth/password",
      {
        method: "POST",
        body: JSON.stringify({
          current_password,
          new_password,
        }),
      }
    ),

  logoutAll: () =>
    request<void>(
      "/auth/logout-all",
      {
        method: "POST",
      }
    ),

  // ----------------------------------------------------------
  // DATASETS
  // ----------------------------------------------------------

  datasets: (offset = 0) =>
    request<DatasetSummary[]>(
      `/analytics/datasets?offset=${offset}`
    ),

  datasetDetail: (
    id: number,
    offset = 0
  ) =>
    request<DatasetDetail>(
      `/analytics/datasets/${id}?offset=${offset}`
    ),

  // ----------------------------------------------------------
  // DASHBOARD
  // ----------------------------------------------------------

  dashboardOptions: () =>
    request<DashboardOptions>(
      "/analytics/filter-options"
    ),

  dashboardBreakdown: (
    start: string,
    end: string,
    filters: DashboardFilters = {}
  ) =>
    request<Breakdown>(
      `/analytics/breakdown?${dashboardQuery(
        start,
        end,
        filters
      )}`
    ),

  dashboardSummary: (
    start: string,
    end: string,
    filters: DashboardFilters = {}
  ) =>
    request<Summary>(
      `/analytics/summary?${dashboardQuery(
        start,
        end,
        filters
      )}`
    ),

  dashboardSeries: (
    start: string,
    end: string,
    filters: DashboardFilters = {}
  ) =>
    request<
      {
        day: string;
        transactions: number;
        revenue: string;
      }[]
    >(
      `/analytics/sales-series?${dashboardQuery(
        start,
        end,
        filters
      )}`
    ),

  // ----------------------------------------------------------
  // VENTAS
  // ----------------------------------------------------------

  sale: (id: number) =>
    request<SaleDetail>(
      `/sales/${id}`
    ),

  salesPage: (
    offset: number,
    start: string,
    end: string,
    status: string
  ) => {
    const params = new URLSearchParams({
      offset: String(offset),
      limit: "26",
    });

    if (start) {
      params.set("start", start);
    }

    if (end) {
      params.set("end", end);
    }

    if (status) {
      params.set("status", status);
    }

    return request<Sale[]>(
      `/sales?${params.toString()}`
    );
  },

  sales: (
    start?: string,
    end?: string,
    days = 30
  ) =>
    request<Sale[]>(
      `/sales?${
        start || end
          ? rangeQuery(start, end)
          : periodQuery(days)
      }`
    ),

  createSale: (
    payload: {
      branch_id?: number | null;
      customer_id?: number | null;

      items: {
        product_id: number;
        quantity: number;
        discount_percent?: number;
        tax_percent?: number;
      }[];

      payments: {
        method: string;
        amount: number;
      }[];
    }
  ) =>
    request<Sale>(
      "/sales",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  voidSale: (
    id: number,
    reason: string,
    refund_confirmed: boolean,
    restock_confirmed: boolean
  ) =>
    request<{
      id: number;
      status: string;
    }>(
      `/sales/${id}/void`,
      {
        method: "POST",
        body: JSON.stringify({
          reason,
          refund_confirmed,
          restock_confirmed,
        }),
      }
    ),

  // ----------------------------------------------------------
  // INVENTARIO
  // ----------------------------------------------------------

  inventory: (branch = "") =>
    request<InventoryRow[]>(
      `/inventory${
        branch
          ? `?branch_id=${encodeURIComponent(branch)}`
          : ""
      }`
    ),

  inventoryMovements: (
    productId?: number,
    offset = 0,
    branch = ""
  ) => {
    const params = new URLSearchParams({
      limit: "26",
      offset: String(offset),
    });

    if (productId) {
      params.set(
        "product_id",
        String(productId)
      );
    }

    if (branch) {
      params.set(
        "branch_id",
        branch
      );
    }

    return request<InventoryMovement[]>(
      `/inventory/movements?${params.toString()}`
    );
  },

  adjustInventory: (
    product_id: number,
    quantity_delta: number,
    reason: string,
    branch = ""
  ) =>
    request<InventoryRow>(
      "/inventory/adjustments",
      {
        method: "POST",
        body: JSON.stringify({
          product_id,
          quantity_delta,
          reason,
          branch_id: branch
            ? Number(branch)
            : null,
        }),
      }
    ),

  // ----------------------------------------------------------
  // PEDIDOS
  // ----------------------------------------------------------

  orders: (offset = 0) =>
    request<Order[]>(
      `/orders?offset=${offset}&limit=26`
    ),

  order: (id: number) =>
    request<OrderDetail>(
      `/orders/${id}`
    ),

  createOrder: (
    payload: {
      branch_id?: number | null;
      customer_id: number | null;

      items: {
        product_id: number;
        quantity: number;
        discount_percent?: number;
        tax_percent?: number;
      }[];
    }
  ) =>
    request<Order>(
      "/orders",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  confirmOrder: (
    id: number,
    method: string,
    amount: number
  ) =>
    request<{
      id: number;
      sale_id: number;
    }>(
      `/orders/${id}/confirm`,
      {
        method: "POST",
        body: JSON.stringify({
          payments: [
            {
              method,
              amount,
            },
          ],
        }),
      }
    ),

  cancelOrder: (
    id: number,
    reason: string
  ) =>
    request<Order>(
      `/orders/${id}/cancel`,
      {
        method: "POST",
        body: JSON.stringify({
          reason,
        }),
      }
    ),

  // ----------------------------------------------------------
  // LOGIN
  // ----------------------------------------------------------

  login: (
    email: string,
    password: string,
    company_id: number
  ) =>
    request<{
      access_token: string;
      user: SessionUser;
    }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          company_id,
        }),
      }
    ),

  // ----------------------------------------------------------
  // CLIENTES
  // ----------------------------------------------------------

  customers: (
    q = "",
    offset = 0,
    limit = 50
  ) =>
    request<Customer[]>(
      `/customers?q=${encodeURIComponent(
        q
      )}&offset=${offset}&limit=${limit}`
    ),

  updateCustomer: (
    id: number,
    payload: {
      name: string;
      email: string | null;
      phone: string | null;
      is_active: boolean;
    }
  ) =>
    request<Customer>(
      `/customers/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      }
    ),

  createCustomer: (
    payload: {
      name: string;
      email?: string;
      phone?: string;
    }
  ) =>
    request<Customer>(
      "/customers",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // CATEGORÍAS
  // ----------------------------------------------------------

  categories: () =>
    request<Category[]>(
      "/categories"
    ),

  createCategory: (
    name: string
  ) =>
    request<Category>(
      "/categories",
      {
        method: "POST",
        body: JSON.stringify({
          name,
        }),
      }
    ),

  updateCategory: (
    id: number,
    name: string,
    is_active: boolean
  ) =>
    request<Category>(
      `/categories/${id}`,
      {
        method: "PUT",
        body: JSON.stringify({
          name,
          is_active,
        }),
      }
    ),

  // ----------------------------------------------------------
  // EMPLEADOS
  // ----------------------------------------------------------

  updateEmployee: (
    id: number,
    full_name: string,
    is_active: boolean,
    branch_id: number | null = null
  ) =>
    request<{
      id: number;
      full_name: string;
      is_active: boolean;
    }>(
      `/employees/${id}`,
      {
        method: "PUT",
        body: JSON.stringify({
          full_name,
          is_active,
          branch_id,
        }),
      }
    ),

  employees: () =>
    request<
      {
        id: number;
        full_name: string;
        is_active: boolean;
        branch_id: number | null;
        branch_name: string | null;
        user_id: number | null;
        email: string | null;
      }[]
    >("/employees"),

  createEmployee: (
    full_name: string,
    user_id?: number | null,
    branch_id: number | null = null
  ) =>
    request<{
      id: number;
      full_name: string;
    }>(
      "/employees",
      {
        method: "POST",
        body: JSON.stringify({
          full_name,
          user_id,
          branch_id,
        }),
      }
    ),

  // ----------------------------------------------------------
  // PRODUCTOS
  // ----------------------------------------------------------

  products: (
    q = "",
    offset = 0,
    limit = 50,
    branch = ""
  ) =>
    request<Product[]>(
      `/products?q=${encodeURIComponent(
        q
      )}&offset=${offset}&limit=${limit}${
        branch
          ? "&branch_id=" + branch
          : ""
      }`
    ),

  updateProduct: (
    id: number,
    payload: {
      sku: string;
      name: string;
      description: string | null;
      unit_price: number;
      category_id: number | null;
      is_active: boolean;
    }
  ) =>
    request<Product>(
      `/products/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      }
    ),

  createProduct: (
    payload: {
      sku: string;
      name: string;
      description?: string | null;
      unit_price: number;
      category_id?: number | null;
    }
  ) =>
    request<Product>(
      "/products",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // ANALYTICS
  // ----------------------------------------------------------

  summary: (days = 30) =>
    request<Summary>(
      `/analytics/summary?${periodQuery(days)}`
    ),

  salesSeries: (days = 30) =>
    request<
      {
        day: string;
        transactions: number;
        revenue: string;
      }[]
    >(
      `/analytics/sales-series?${periodQuery(
        days
      )}`
    ),

  analyzeSales: (
    metric:
      | "sales_total"
      | "units_per_sale",
    start?: string,
    end?: string
  ) =>
    request<{
      id: number;
      dataset_id: number;
      parameters: Record<string, unknown>;
      result: Record<
        string,
        string | number
      >;
    }>(
      "/analytics/analyses",
      {
        method: "POST",
        body: JSON.stringify({
          metric,
          start: start || null,
          end: end || null,
        }),
      }
    ),

  analysisHistory: () =>
    request<Analysis[]>(
      "/analytics/analyses"
    ),

  // ----------------------------------------------------------
  // VARIANZA Y DESVIACIÓN ESTÁNDAR
  // ----------------------------------------------------------

  dispersion: (
    payload: DispersionRequest
  ) =>
    request<DispersionResult>(
      "/probability/dispersion/calculate",
      {
        method: "POST",
        body: JSON.stringify({
          variable: payload.variable,
          start: payload.start || null,
          end: payload.end || null,
          branch_id: payload.branch_id ?? null,
        }),
      }
    ),

  // ==========================================================
  // BAYES AUTOMÁTICO
  // ==========================================================

  /**
   * Obtiene los eventos disponibles para
   * calcular Bayes utilizando los datos
   * reales almacenados en SalesIA.
   */
  bayesEvents: () =>
    request<BayesEvent[]>(
      "/probability/bayes/events"
    ),

  /**
   * Ejecuta el análisis de Bayes.
   *
   * Las probabilidades se calculan
   * automáticamente en el backend.
   */
  bayes: (
    payload: {
      event_a: string;
      event_b: string;
      start?: string;
      end?: string;
    }
  ) =>
    request<BayesResult>(
      "/probability/bayes",
      {
        method: "POST",
        body: JSON.stringify({
          event_a: payload.event_a,
          event_b: payload.event_b,
          start: payload.start || null,
          end: payload.end || null,
        }),
      }
    ),

  // ----------------------------------------------------------
  // VARIABLE ALEATORIA
  // ----------------------------------------------------------

  randomVariable: (
    payload: {
      name: string;

      outcomes: {
        value: number;
        probability: number;
      }[];

      description?: string;
    }
  ) =>
    request<Record<string, number | string>>(
      "/probability/random-variables/analyze",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // INSIGHTS
  // ----------------------------------------------------------

  insightTrace: (id: number) =>
    request<InsightTrace>(
      `/insights/${id}/trace`
    ),

  insights: (offset = 0) =>
    request<Insight[]>(
      `/insights?offset=${offset}&limit=26`
    ),

  generateInsights: (end?: string) =>
    request<{
      created: number;
      updated: number;
      unchanged: number;
      resolved: number;
      matched: number;
      generated_at: string;
    }>(
      `/insights/generate${
        end
          ? `?end=${encodeURIComponent(end)}`
          : ""
      }`,
      {
        method: "POST",
      }
    ),

  // ----------------------------------------------------------
  // REPORTES
  // ----------------------------------------------------------

  reportFilterOptions: () =>
    request<ReportFilterOptions>(
      "/reports/filter-options"
    ),

  reports: (offset = 0) =>
    request<Report[]>(
      `/reports?offset=${offset}&limit=26`
    ),

  report: (id: number) =>
    request<ReportSnapshot>(
      `/reports/${id}`
    ),

  createSalesReport: (
    start?: string,
    end?: string,
    report_type: ReportKind = "sales",
    filters: Partial<
      Record<ReportFilterKey, number>
    > = {}
  ) =>
    request<ReportSnapshot>(
      "/reports/sales",
      {
        method: "POST",
        body: JSON.stringify({
          start: start || null,
          end: end || null,
          report_type,
          ...filters,
        }),
      }
    ),

  downloadReport: async (
    id: number
  ) => {
    let response: Response;

    try {
      response = await fetchWithReadRetry(
        `${API}/reports/${id}/download`,
        {
          headers: {
            Authorization: `Bearer ${getToken()}`,
          },
        }
      );
    } catch {
      throw new Error(
        "No se pudo conectar con el servidor para descargar el reporte."
      );
    }

    if (response.status === 401) {
      clearToken();

      window.dispatchEvent(
        new Event("salesia:session-expired")
      );
    }

    if (!response.ok) {
      const body = await response
        .json()
        .catch(() => null);

      throw new Error(
        body?.detail?.message ??
          body?.detail ??
          "No se pudo descargar el reporte"
      );
    }

    const url = URL.createObjectURL(
      await response.blob()
    );

    const anchor =
      document.createElement("a");

    anchor.href = url;
    anchor.download =
      `salesia-reporte-${id}.csv`;

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    window.setTimeout(
      () => URL.revokeObjectURL(url),
      60000
    );
  },

  downloadSalesCsv: async (
    start?: string,
    end?: string
  ) => {
    const query =
      start || end
        ? rangeQuery(start, end)
        : "";

    let response: Response;

    try {
      response = await fetchWithReadRetry(
        `${API}/reports/sales.csv${
          query ? `?${query}` : ""
        }`,
        {
          headers: {
            Authorization: `Bearer ${getToken()}`,
          },
        }
      );
    } catch {
      throw new Error(
        "No se pudo conectar con el servidor para exportar las ventas."
      );
    }

    if (response.status === 401) {
      clearToken();

      window.dispatchEvent(
        new Event("salesia:session-expired")
      );
    }

    if (!response.ok) {
      throw new Error(
        "No se pudo exportar el reporte"
      );
    }

    const blob = await response.blob();

    const url =
      URL.createObjectURL(blob);

    const anchor =
      document.createElement("a");

    anchor.href = url;
    anchor.download =
      "salesia-ventas.csv";

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    window.setTimeout(
      () => URL.revokeObjectURL(url),
      1000
    );
  },

  // ----------------------------------------------------------
  // USUARIOS
  // ----------------------------------------------------------

  users: () =>
    request<ManagedUser[]>(
      "/users"
    ),

  updateUser: (
    id: number,
    payload: {
      full_name: string;
      role: string;
      is_active: boolean;
    }
  ) =>
    request(
      `/users/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      }
    ),

  createUser: (
    payload: {
      email: string;
      full_name: string;
      password: string;
      role: string;
    }
  ) =>
    request<ManagedUser>(
      "/users",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // PRECIOS
  // ----------------------------------------------------------

  pricing: () =>
    request<PricingRules>(
      "/pricing"
    ),

  savePricing: (
    payload: PricingRules
  ) =>
    request<PricingRules>(
      "/pricing",
      {
        method: "PUT",
        body: JSON.stringify(payload),
      }
    ),

  // ----------------------------------------------------------
  // AUDITORÍA
  // ----------------------------------------------------------

  auditLogs: (
    offset = 0,
    action = "",
    start = "",
    end = ""
  ) =>
    request<AuditEvent[]>(
      "/audit?" +
        new URLSearchParams({
          offset: String(offset),
          limit: "26",

          ...(action
            ? { action }
            : {}),

          ...(start
            ? { start }
            : {}),

          ...(end
            ? { end }
            : {}),
        })
    ),

  auditActions: () =>
    request<string[]>(
      "/audit/actions"
    ),
};

// ============================================================
// UTILIDADES DE FECHAS
// ============================================================

const formatDate = (d: Date) =>
  `${d.getFullYear()}-${String(
    d.getMonth() + 1
  ).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;

const periodQuery = (
  days = 30
) => {
  const end = new Date();

  const start = new Date(end);

  start.setDate(
    start.getDate() - days + 1
  );

  return `start=${formatDate(
    start
  )}&end=${formatDate(end)}`;
};

const rangeQuery = (
  start?: string,
  end?: string
) => {
  const params =
    new URLSearchParams();

  if (start) {
    params.set("start", start);
  }

  if (end) {
    params.set("end", end);
  }

  return params.toString()
    ? params.toString()
    : periodQuery();
};

// ============================================================
// TIPOS ANALYTICS
// ============================================================

export type Insight = {
  id: number;
  rule_code: string;
  title: string;
  message: string;
  evidence: Record<string, unknown>;
  severity: string;
  created_at: string;
  status: string;
  evaluated_at: string;
  resolved_at: string | null;
};

export type Report = {
  id: number;
  report_type: string;
  parameters: Record<string, unknown>;
  created_at: string;
  available: boolean;
};

export type ReportSnapshot = {
  id: number;
  report_type: ReportKind;
  generated_at: string;

  groups?: ReportGroup[];

  parameters: {
    start: string | null;
    end: string | null;
    timezone: string;

    filters?: Partial<
      Record<
        ReportFilterKey,
        {
          id: number;
          name: string;
        }
      >
    >;
  };

  summary: {
    sales_count: number;
    voided_count: number;

    by_currency: {
      currency: string;
      sales_count: number;
      revenue: string;
      average_ticket: string;
      median_ticket: string;
      minimum: string;
      maximum: string;
    }[];
  };

  rows: {
    id: number;
    sold_at: string;
    status: string;
    customer: string | null;
    seller: string;
    subtotal: string;
    discount_total: string;
    tax_total: string;
    total: string;
    currency: string;
  }[];
};

export type InventoryMovement = {
  id: number;
  product_id: number;
  product_name: string;
  sale_id: number | null;
  movement_type: string;
  quantity_delta: string;
  reason: string | null;
  created_at: string;
  created_by: string;
};

export type ManagedUser = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type ReportFilterKey =
  | "branch_id"
  | "customer_id"
  | "employee_id"
  | "product_id";

export type ReportFilterOptions =
  Record<
    ReportFilterKey,
    {
      id: number;
      name: string;
    }[]
  >;

export type AuditEvent = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<
    string,
    unknown
  > | null;
  created_at: string;
  actor_email: string | null;
};

export type BranchInput = {
  code: string;
  name: string;
  address: string;
  city: string;
  phone: string | null;
  manager_name: string | null;
  manager_email: string | null;
  latitude: string | null;
  longitude: string | null;
  is_active: boolean;
};

export type Branch =
  BranchInput & {
    id: number;
    company_id: number;
    created_at: string;
  };

export type CustomerHistoryData = {
  customer: Customer;

  scope: string;

  totals: {
    currency: string;
    sales_count: number;
    revenue: string;
  }[];

  sales: {
    id: number;
    sold_at: string;
    branch_name: string | null;
    status: string;
    total: string;
    currency: string;
  }[];
};

export type ReportKind =
  | "sales"
  | "statistical"
  | "products"
  | "customers"
  | "sellers";

export type ReportGroup = {
  entity_id: number | null;
  name: string;
  currency: string;
  sales_count: number;
  units: string;
  revenue: string;
  average: string;
};

export type InsightTrace = {
  available: boolean;
  analysis_id?: number;
  dataset_id?: number;
  analysis_type?: string;

  observations: {
    source_ref: string;
    numeric_value: string;
    unit: string;
    observed_at: string;
  }[];
};

export type DatasetSummary = {
  id: number;
  name: string;
  source: string;
  created_at: string;
  variable_count: number;
  observation_count: number;
};

export type DatasetDetail = {
  dataset: {
    id: number;
    name: string;
    source: string;
    filters: Record<string, unknown>;
  };

  variables: {
    id: number;
    name: string;
    data_type: string;
    unit: string | null;
  }[];

  observations: {
    id: number;
    variable_id: number;
    numeric_value: string | null;
    text_value: string | null;
    source_ref: string;
    observed_at: string | null;
  }[];

  analyses: {
    id: number;
    analysis_type: string;

    parameters: {
      outcomes?: {
        value: number;
        probability: number;
      }[];
    };

    result: Record<string, unknown>;
  }[];
};
