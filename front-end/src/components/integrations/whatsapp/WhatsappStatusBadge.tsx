import Badge from "../../ui/badge/Badge";
import type { WhatsappIntegrationState } from "../../../features/integrations/types";

type Props = {
  state: WhatsappIntegrationState;
};

export default function WhatsappStatusBadge({ state }: Props) {
  const { connected, connection_status, session_expired } = state;

  if (session_expired) {
    return (
      <Badge color="warning" size="md" variant="solid">
        <span className="animate-pulse">SESSÃO EXPIRADA</span>
      </Badge>
    );
  }

  if (connected || connection_status === "open") {
    return (
      <Badge color="success" size="md" variant="solid">
        CONECTADO
      </Badge>
    );
  }

  if (connection_status === "connecting") {
    return (
      <Badge color="warning" size="md" variant="solid">
        <span className="animate-pulse">CONECTANDO</span>
      </Badge>
    );
  }

  return (
    <Badge color="error" size="md" variant="solid">
      DESCONECTADO
    </Badge>
  );
}
