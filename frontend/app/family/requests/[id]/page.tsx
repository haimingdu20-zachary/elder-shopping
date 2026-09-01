import FamilyRequestDetail from "@/components/FamilyRequestDetail";

export default async function FamilyRequestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FamilyRequestDetail id={id} />;
}
