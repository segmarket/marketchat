import { cartStatusBadgeClass, cartStatusLabel } from "../../features/sales/format";

type Props = {
  status: string;
};

export default function CartStatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cartStatusBadgeClass(status)}`}
    >
      {cartStatusLabel(status)}
    </span>
  );
}
