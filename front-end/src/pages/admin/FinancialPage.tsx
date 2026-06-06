import PageMeta from "../../components/common/PageMeta";
import FinancialPanel from "../../components/financial/FinancialPanel";
import AdminPageLayout from "../../components/layout/AdminPageShell";

export default function FinancialPage() {
  return (
    <>
      <PageMeta
        title="Financeiro"
        description="Acompanhe seus ganhos, extrato de vendas e solicite saques via Pix."
      />
      <AdminPageLayout
        pageTitle="Financeiro"
        description="Acompanhe seus ganhos, extrato de vendas e solicite saques via Pix."
      >
        <FinancialPanel />
      </AdminPageLayout>
    </>
  );
}
