import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import ComponentCard from "../../components/common/ComponentCard";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import OnboardingSpotlight from "../../components/onboarding/OnboardingSpotlight";
import Button from "../../components/ui/button/Button";
import DisconnectConfirmModal from "../../components/integrations/whatsapp/DisconnectConfirmModal";
import WhatsappActionCenter from "../../components/integrations/whatsapp/WhatsappActionCenter";
import WhatsappDeviceCard from "../../components/integrations/whatsapp/WhatsappDeviceCard";
import WhatsappHealthGrid from "../../components/integrations/whatsapp/WhatsappHealthGrid";
import WhatsappStatusBadge from "../../components/integrations/whatsapp/WhatsappStatusBadge";
import {
  disconnectWhatsapp,
  fetchWhatsappIntegration,
  fetchWhatsappQrcode,
  fetchWhatsappStatus,
  provisionWhatsapp,
  refreshWhatsappAvatar,
  restartWhatsapp,
} from "../../features/integrations/api";
import type { WhatsappDashboard } from "../../features/integrations/types";
import { WHATSAPP_CONNECT_SPOTLIGHT_COPY } from "../../features/onboarding/whatsappConnectSpotlightCopy";
import { useOnboardingStatus } from "../../features/onboarding/useOnboardingStatus";
import { useModal } from "../../hooks/useModal";
import { getAxiosErrorMessage } from "../../utils/apiError";

const POLL_MS = 3000;
const RECONNECT_POLL_MS = 15000;
const QR_FAIL_MSG = "Não foi possível gerar o QR Code no momento, tente novamente.";

function isConnected(state: WhatsappDashboard): boolean {
  return state.connected || state.connection_status === "open";
}

function isQrFlow(state: WhatsappDashboard, qrcodeImage: string): boolean {
  if (!state.has_instance) return false;
  if (isConnected(state)) return false;
  return state.connection_status === "connecting" || Boolean(qrcodeImage);
}

type Props = {
  embedded?: boolean;
};

type ConnectSpotlightStep = "TRIGGER" | "SCAN";

export default function WhatsAppConfig({ embedded = false }: Props) {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [state, setState] = useState<WhatsappDashboard | null>(null);
  const [qrcodeImage, setQrcodeImage] = useState("");
  const [accessHint, setAccessHint] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const loadInFlightRef = useRef(false);
  const avatarFetchStartedRef = useRef(false);
  const disconnectModal = useModal();
  const [connectStep, setConnectStep] = useState<ConnectSpotlightStep | null>(null);
  const spotlightWasEligibleRef = useRef(false);
  const { status: onboarding, loading: onboardingLoading } = useOnboardingStatus();

  const canManage = Boolean(state?.can_manage_integrations);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const load = useCallback(async () => {
    if (loadInFlightRef.current) return;
    loadInFlightRef.current = true;
    setLoading(true);
    try {
      const data = await fetchWhatsappIntegration();
      setState(data);
      if (data.qrcode_image) setQrcodeImage(data.qrcode_image);
      if (!data.can_manage_integrations) {
        if (data.is_platform_superuser && !data.has_tenant) {
          setAccessHint(
            "Você está logado como administrador da plataforma, sem empresa vinculada. Para conectar o WhatsApp, entre com a conta de administrador da empresa.",
          );
        } else {
          setAccessHint(
            "Apenas administradores da empresa podem conectar ou desconectar o WhatsApp.",
          );
        }
      } else {
        setAccessHint(null);
      }
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar integrações." }));
    } finally {
      loadInFlightRef.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    return () => stopPolling();
  }, [load, stopPolling]);

  useEffect(() => {
    if (!state || loading) return;
    if (!isConnected(state)) return;
    if ((state.profile_picture_url || "").trim()) return;

    const cacheKey = `mc-wa-avatar:v2:${state.instance_name}`;
    if (sessionStorage.getItem(cacheKey) === "done") return;
    if (avatarFetchStartedRef.current) return;
    avatarFetchStartedRef.current = true;
    sessionStorage.setItem(cacheKey, "done");

    let cancelled = false;
    void refreshWhatsappAvatar()
      .then((data) => {
        if (!cancelled) setState(data);
      })
      .catch(() => {
        /* avatar opcional; painel já está visível */
      });

    return () => {
      cancelled = true;
    };
  }, [state, loading]);

  const pollStatus = useCallback(async () => {
    try {
      const data = await fetchWhatsappStatus();
      setState(data);
      if (data.qrcode_image) setQrcodeImage(data.qrcode_image);
      if (isConnected(data)) {
        stopPolling();
        setQrcodeImage("");
        setConnectStep(null);
        toast.success("WhatsApp conectado com sucesso.");
      }
    } catch {
      /* polling silencioso */
    }
  }, [stopPolling]);

  const shouldPollQr =
    Boolean(state?.has_instance && state.is_active) &&
    !isConnected(state!) &&
    (state?.connection_status === "connecting" || Boolean(qrcodeImage));

  const shouldPollReconnect =
    Boolean(state?.needs_reconnect && state.is_active) &&
    !isConnected(state!) &&
    state?.connection_status === "close" &&
    !qrcodeImage;

  useEffect(() => {
    stopPolling();
    if (!shouldPollQr) return;
    void pollStatus();
    pollRef.current = setInterval(() => void pollStatus(), POLL_MS);
    return () => stopPolling();
  }, [shouldPollQr, pollStatus, stopPolling]);

  useEffect(() => {
    stopPolling();
    if (!shouldPollReconnect) return;
    void pollStatus();
    pollRef.current = setInterval(() => void pollStatus(), RECONNECT_POLL_MS);
    return () => stopPolling();
  }, [shouldPollReconnect, pollStatus, stopPolling]);

  async function handleReconnect() {
    setBusy(true);
    try {
      if (state?.is_active) {
        const restarted = await restartWhatsapp();
        setState(restarted);
        if (restarted.qrcode_image) {
          setQrcodeImage(restarted.qrcode_image);
        } else if (!isConnected(restarted)) {
          const qr = await fetchWhatsappQrcode();
          setState(qr);
          if (qr.qrcode_image) setQrcodeImage(qr.qrcode_image);
          else toast.error(QR_FAIL_MSG);
        }
        toast.success("Escaneie o novo QR Code para reconectar o WhatsApp.");
      } else {
        await handleConnect();
      }
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: QR_FAIL_MSG }));
    } finally {
      setBusy(false);
    }
  }

  async function handleConnect() {
    setBusy(true);
    try {
      const data = await provisionWhatsapp();
      setState(data);
      if (data.qrcode_image) {
        setQrcodeImage(data.qrcode_image);
      } else if (!isConnected(data)) {
        const qr = await fetchWhatsappQrcode();
        setState(qr);
        if (qr.qrcode_image) setQrcodeImage(qr.qrcode_image);
        else toast.error(QR_FAIL_MSG);
      }
      toast.success("Escaneie o QR Code no WhatsApp para concluir a conexão.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: QR_FAIL_MSG }));
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshQr() {
    setBusy(true);
    try {
      const data = await fetchWhatsappQrcode();
      setState(data);
      if (data.qrcode_image) {
        setQrcodeImage(data.qrcode_image);
        toast.message("QR Code atualizado.");
      } else if (isConnected(data)) {
        setQrcodeImage("");
        toast.success("WhatsApp já está conectado.");
      } else {
        toast.error(QR_FAIL_MSG);
      }
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: QR_FAIL_MSG }));
    } finally {
      setBusy(false);
    }
  }

  async function handleRestart() {
    setBusy(true);
    try {
      const data = await restartWhatsapp();
      setState(data);
      toast.success("Reinício solicitado. Aguarde a reconexão.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao reiniciar WhatsApp." }));
    } finally {
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    setBusy(true);
    try {
      const data = await disconnectWhatsapp();
      setState(data);
      setQrcodeImage("");
      stopPolling();
      disconnectModal.closeModal();
      if (spotlightEligible) {
        setConnectStep("TRIGGER");
      } else {
        setConnectStep(null);
      }
      toast.success("WhatsApp desconectado.");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao desconectar." }));
    } finally {
      setBusy(false);
    }
  }

  const connected = state ? isConnected(state) : false;
  const showQr = state ? isQrFlow(state, qrcodeImage) : false;
  const showStaleConnecting =
    Boolean(
      state?.has_instance &&
        !connected &&
        !showQr &&
        state.connection_status === "connecting",
    );
  const showReconnect =
    Boolean(state?.needs_reconnect && !connected && !showQr && !showStaleConnecting);

  const showFirstConnect =
    Boolean(state && !connected && !showQr && !showStaleConnecting && !showReconnect);

  const spotlightEligible =
    !loading &&
    !onboardingLoading &&
    onboarding !== null &&
    !onboarding.step_whatsapp_connected &&
    state !== null &&
    !connected &&
    canManage &&
    (showFirstConnect || showStaleConnecting);

  useEffect(() => {
    if (spotlightEligible && !spotlightWasEligibleRef.current) {
      setConnectStep("TRIGGER");
    }
    if (!spotlightEligible || connected) {
      setConnectStep(null);
      spotlightWasEligibleRef.current = false;
    } else {
      spotlightWasEligibleRef.current = true;
    }
  }, [spotlightEligible, connected]);

  useEffect(() => {
    if (connectStep === "SCAN" && spotlightEligible && !qrcodeImage && !busy && !showQr) {
      setConnectStep("TRIGGER");
    }
  }, [connectStep, spotlightEligible, qrcodeImage, busy, showQr]);

  async function handleConnectSpotlight() {
    setConnectStep("SCAN");
    try {
      await handleConnect();
    } catch {
      if (spotlightEligible) {
        setConnectStep("TRIGGER");
      }
    }
  }

  function renderConnectButton(label = "Conectar WhatsApp") {
    const button = (
      <Button onClick={() => void handleConnectSpotlight()} disabled={busy}>
        {busy ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            Conectando…
          </span>
        ) : (
          label
        )}
      </Button>
    );

    if (connectStep === "TRIGGER") {
      return (
        <OnboardingSpotlight
          message={WHATSAPP_CONNECT_SPOTLIGHT_COPY.trigger}
          align="center"
          intense
        >
          {button}
        </OnboardingSpotlight>
      );
    }

    return button;
  }

  function renderQrPanel() {
    const panel = (
      <div className="flex flex-col items-center gap-4 rounded-xl border border-gray-200 bg-gray-50 p-6 dark:border-gray-800 dark:bg-gray-900/50">
        <WhatsappStatusBadge state={state!} />
        {qrcodeImage ? (
          <>
            <p className="text-center text-sm text-gray-600 dark:text-gray-400">
              Abra o WhatsApp → Aparelhos conectados → Conectar aparelho e escaneie o código:
            </p>
            <img
              src={qrcodeImage}
              alt="QR Code WhatsApp"
              className="h-56 w-56 rounded-lg bg-white p-2"
            />
          </>
        ) : (
          <p className="text-center text-sm text-gray-600 dark:text-gray-400">
            Gerando QR Code… aguarde alguns instantes.
          </p>
        )}
        <p className="text-xs text-gray-500">
          Atualizamos o status automaticamente a cada poucos segundos.
        </p>
        {canManage && qrcodeImage ? (
          <Button variant="outline" onClick={() => void handleRefreshQr()} disabled={busy}>
            Atualizar QR
          </Button>
        ) : null}
      </div>
    );

    if (connectStep === "SCAN") {
      return (
        <OnboardingSpotlight
          message={WHATSAPP_CONNECT_SPOTLIGHT_COPY.scan}
          align="center"
          highlightMode="block"
          calloutPlacement="above"
        >
          {panel}
        </OnboardingSpotlight>
      );
    }

    return panel;
  }

  return (
    <>
      {!embedded && (
        <>
          <PageMeta
            title="Integrações | MarketChat"
            description="Gerencie a conexão WhatsApp da sua empresa."
            noIndex
          />
          <PageBreadcrumb pageTitle="Integrações" />
        </>
      )}

      <ComponentCard title="WhatsApp">
        {loading ? (
          <p className="text-sm text-gray-500 animate-pulse dark:text-gray-400">Carregando…</p>
        ) : !state ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">Não foi possível carregar o painel.</p>
        ) : (
          <div className="space-y-6">
            {showFirstConnect && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Conecte o WhatsApp da sua empresa. Cada conta possui uma conexão isolada e segura.
              </p>
            )}

            {showReconnect && (
              <p className="rounded-lg border border-warning-200 bg-warning-50 px-3 py-2 text-sm text-warning-900 dark:border-warning-900/40 dark:bg-warning-950/30 dark:text-warning-100">
                {state.disconnect_reason ||
                  "Seu WhatsApp foi desconectado. Reconecte para voltar a receber mensagens."}
              </p>
            )}

            {!canManage && accessHint && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100">
                {accessHint}
              </p>
            )}

            {showStaleConnecting && connectStep !== "SCAN" && (
              <div className="flex flex-col items-center gap-4 py-6 text-center">
                <p className="max-w-md text-sm text-gray-600 dark:text-gray-400">
                  A conexão anterior não foi encontrada. Gere um novo QR Code para vincular o
                  WhatsApp.
                </p>
                {canManage ? renderConnectButton() : null}
              </div>
            )}

            {showReconnect && (
              <div className="flex flex-col items-center gap-4 py-6 text-center">
                <WhatsappStatusBadge state={state} />
                {state.was_connected && (state.profile_name || state.phone_number) && (
                  <WhatsappDeviceCard state={state} />
                )}
                <p className="max-w-md text-sm text-gray-600 dark:text-gray-400">
                  Reconecte o WhatsApp para retomar o envio e recebimento de mensagens pelo
                  MarketChat.
                </p>
                {canManage && (
                  <Button onClick={() => void handleReconnect()} disabled={busy}>
                    {busy ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                        Reconectando…
                      </span>
                    ) : (
                      "Reconectar WhatsApp"
                    )}
                  </Button>
                )}
              </div>
            )}

            {showFirstConnect && connectStep !== "SCAN" && (
              <div className="flex flex-col items-center gap-4 py-6 text-center">
                <p className="max-w-md text-sm text-gray-600 dark:text-gray-400">
                  Vincule o número da empresa para enviar e receber mensagens pelo MarketChat.
                </p>
                {canManage ? renderConnectButton() : null}
              </div>
            )}

            {(showQr || connectStep === "SCAN") && (qrcodeImage || connectStep === "SCAN") ? (
              renderQrPanel()
            ) : null}

            {connected && (
              <div className="space-y-6">
                <div className="flex flex-col items-center gap-3 sm:items-start">
                  <WhatsappStatusBadge state={state} />
                </div>
                <WhatsappDeviceCard state={state} />
                <WhatsappHealthGrid
                  evolutionApiStatus={state.evolution_api_status}
                  webhookStatus={state.webhook_status}
                />
                <WhatsappActionCenter
                  canManage={canManage}
                  busy={busy}
                  onRestart={() => void handleRestart()}
                  onDisconnect={disconnectModal.openModal}
                />
              </div>
            )}
          </div>
        )}
      </ComponentCard>

      <DisconnectConfirmModal
        isOpen={disconnectModal.isOpen}
        busy={busy}
        onClose={disconnectModal.closeModal}
        onConfirm={() => void handleDisconnect()}
      />
    </>
  );
}
