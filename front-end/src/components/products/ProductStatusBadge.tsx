import Badge from "../ui/badge/Badge";
import { statusBadgeColor, statusLabel } from "../../features/products/format";
import type { ProductStatus } from "../../features/products/types";

type Props = {
  status: ProductStatus;
};

export default function ProductStatusBadge({ status }: Props) {
  return (
    <Badge color={statusBadgeColor(status)} size="sm">
      {statusLabel(status)}
    </Badge>
  );
}
