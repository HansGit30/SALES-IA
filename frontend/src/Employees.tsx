import DirectoryPage from "./DirectoryPage";
export default function Employees({canCreate = false}: {canCreate?: boolean}) { return <DirectoryPage kind="employees" canEdit={canCreate} />; }