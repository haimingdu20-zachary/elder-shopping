import FamilyOrderDetail from "@/components/FamilyOrderDetail";

export default async function FamilyOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FamilyOrderDetail id={id} />;
}
