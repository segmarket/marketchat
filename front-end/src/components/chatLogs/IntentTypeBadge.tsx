import { intentBadgeClass, intentTypeLabel } from "../../features/chatLogs/format";

type Props = {
  intentType: string;
};

export default function IntentTypeBadge({ intentType }: Props) {
  if (!intentType) {
    return <span className="text-theme-sm text-gray-400">—</span>;
  }
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${intentBadgeClass(intentType)}`}
    >
      {intentTypeLabel(intentType)}
    </span>
  );
}
