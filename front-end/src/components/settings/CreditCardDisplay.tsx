import type { PaymentMethodSummary } from "../../features/settings/types";

type CreditCardDisplayProps = {
  summary: PaymentMethodSummary;
};

export default function CreditCardDisplay({ summary }: CreditCardDisplayProps) {
  const brand = summary.card_brand?.toUpperCase() ?? "CARTÃO";
  const lastFour = summary.card_last_four ?? "••••";

  return (
    <div className="relative mx-auto w-full max-w-sm overflow-hidden rounded-2xl bg-gradient-to-br from-brand-500 via-brand-600 to-brand-700 p-6 text-white shadow-lg">
      <p className="text-xs font-medium uppercase tracking-wider text-white/80">{brand}</p>
      <p className="mt-8 font-mono text-lg tracking-widest">•••• •••• •••• {lastFour}</p>
      <p className="mt-6 text-sm text-white/90">{summary.display_label}</p>
    </div>
  );
}
