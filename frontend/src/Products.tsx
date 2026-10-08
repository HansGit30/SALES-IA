import CatalogPage from "./CatalogPage";
export default function ProductCatalog({canCreate = false}: {canCreate?: boolean}) { return <CatalogPage kind="products" canEdit={canCreate} />; }
