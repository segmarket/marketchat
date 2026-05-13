import PageMeta from "../../components/common/PageMeta";
import ComponentCard from "../../components/common/ComponentCard";

export default function BillingPage() {
  return (
    <>
      <PageMeta title="Cobrança | MarketChat" description="Regularize o pagamento da sua conta." />
      <div className="max-w-2xl">
        <ComponentCard title="Pagamento necessário">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Sua conta está com o acesso limitado por pendência de cobrança. Atualize seu método de pagamento
            ou entre em contato com o suporte para reativar todos os recursos.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            Após regularizar na operadora de pagamentos, o acesso é restabelecido automaticamente.
          </p>
        </ComponentCard>
      </div>
    </>
  );
}
