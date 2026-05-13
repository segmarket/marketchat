type Props = { password: string };

export default function PasswordStrengthMeter({ password }: Props) {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  score = Math.min(4, Math.floor(score * 0.8));

  const labels = ["Fraca", "Razoável", "Boa", "Forte", "Muito forte"];
  const colors = ["bg-error-500", "bg-warning-500", "bg-warning-400", "bg-brand-500", "bg-success-500"];

  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i <= score ? colors[score] : "bg-gray-200 dark:bg-gray-700"
            }`}
          />
        ))}
      </div>
      {password.length > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{labels[score]}</p>
      )}
    </div>
  );
}
