import Badge from "../../ui/badge/Badge";
import type { WhatsappIntegrationState } from "../../../features/integrations/types";
import { formatPhoneBR, platformLabel } from "../../../features/integrations/format";
import WhatsappProfileAvatar from "./WhatsappProfileAvatar";

type Props = {
  state: WhatsappIntegrationState;
};

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === "android") {
    return (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M17.6 9.48l1.84-3.18c.16-.28.06-.62-.22-.78-.28-.16-.62-.06-.78.22l-1.88 3.24a11.5 11.5 0 0 0-8.32 0L6.36 5.74a.5.5 0 0 0-.78-.22.5.5 0 0 0-.22.78L7.4 9.48A8.09 8.09 0 0 0 4 14.5h16a8.09 8.09 0 0 0-3.4-5.02zM8.5 16.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5zm7 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5z" />
      </svg>
    );
  }
  if (platform === "ios") {
    return (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.48-.12-1.06.493-2.2 1.256-3.04.817-.94 2.35-1.64 2.908-1.52zm2.715 19.07c-.747 1.08-1.08 1.56-2.02 2.51-1.39 1.45-3.35 3.27-5.75 3.28-2.16.01-2.71-1.41-5.03-1.39-2.32.02-2.81 1.42-4.97 1.4-2.4-.02-4.28-1.88-5.67-3.33C-2.11 15.96 2.55 8.62 7.84 8.5c2.16.05 3.67 1.48 5.03 1.51 1.35-.03 3.78-1.87 6.38-1.59 1.08.05 4.11.44 6.05 3.32-5.2 3.15-4.35 11.2.87 13.98z" />
      </svg>
    );
  }
  return null;
}

export default function WhatsappDeviceCard({ state }: Props) {
  const displayName = state.profile_name || state.instance_name || "WhatsApp";
  const phone = formatPhoneBR(state.phone_number || state.pair_phone);

  return (
    <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
      <WhatsappProfileAvatar
        src={state.profile_picture_url}
        alt={displayName}
        connected={state.connected}
      />
      <div className="min-w-0 flex-1 space-y-2">
        <h3 className="text-theme-xl font-semibold text-gray-900 dark:text-white/90">{displayName}</h3>
        {phone && <p className="text-theme-sm text-gray-600 dark:text-gray-400">{phone}</p>}
        {state.platform !== "unknown" && (
          <Badge color="light" size="sm" startIcon={<PlatformIcon platform={state.platform} />}>
            {platformLabel(state.platform)}
          </Badge>
        )}
      </div>
    </div>
  );
}