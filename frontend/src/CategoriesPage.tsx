import DirectoryPage from "./DirectoryPage";
export default function CategoriesPage({canCreate = false}: {canCreate?: boolean}) { return <DirectoryPage kind="categories" canEdit={canCreate} />; }