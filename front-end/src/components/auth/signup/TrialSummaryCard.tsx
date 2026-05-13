function formatMoneyBR(raw: string | undefined): string {
  const v = raw?.replace(",", ".") ?? "29.90";
  const n = parseFloat(v);
  if (Number.isNaN(n)) return "29,90";
  return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function addDays(d: Date, days: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x;
}

type Props = {
  trialDays: number;
};

export default function TrialSummaryCard({ trialDays }: Props) {
  const today = new Date();
  const chargeDate = addDays(today, trialDays);
  const price = formatMoneyBR(import.meta.env.VITE_TRIAL_SUBSCRIPTION_PRICE);

  const fmt = (d: Date) =>
    d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });

  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 p-6 dark:border-gray-800 dark:bg-white/[0.03]">
      <h3 className="text-base font-semibold text-gray-800 dark:text-white/90 mb-3">Resumo do trial</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
        Seu período de <strong>{trialDays} dias grátis</strong> começa agora. Nenhuma cobrança será feita hoje (
        <strong>{fmt(today)}</strong>). Cobrança automática de <strong>R$ {price}</strong> apenas em{" "}
        <strong>{fmt(chargeDate)}</strong> caso você não cancele.
      </p>
    </div>
  );
}
