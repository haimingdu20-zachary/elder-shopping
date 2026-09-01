import AfterSalePage from "@/components/AfterSalePage";

export default async function Page({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  return <AfterSalePage orderId={orderId} />;
}

