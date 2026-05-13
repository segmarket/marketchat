type Props = { step: 1 | 2 | 3 };

export default function SignupProgressBar({ step }: Props) {
  const pct = step === 1 ? 33 : step === 2 ? 66 : 100;
  return (
    <div className="mb-8">
      <div className="flex justify-between text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
        <span className={step >= 1 ? "text-brand-500" : ""}>Conta</span>
        <span className={step >= 2 ? "text-brand-500" : ""}>Empresa</span>
        <span className={step >= 3 ? "text-brand-500" : ""}>Pagamento</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
