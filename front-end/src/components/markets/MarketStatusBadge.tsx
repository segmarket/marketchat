import Badge from "../ui/badge/Badge";
import { statusBadgeColor, statusLabel } from "../../features/markets/format";
import type { MarketStatus } from "../../features/markets/types";

type Props = {
  status: MarketStatus;
};

export default function MarketStatusBadge({ status }: Props) {
  return (
    <Badge color={statusBadgeColor(status)} size="sm">
      {statusLabel(status)}
    </Badge>
  );
}
