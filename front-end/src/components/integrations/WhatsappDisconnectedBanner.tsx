import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import WhatsAppConfig from "../../pages/admin/WhatsAppConfig";
import { Modal } from "../ui/modal";

/**
 * Banner crítico quando o WhatsApp caiu.
 * Reconecta com o mesmo fluxo da tela de Integrações (WhatsAppConfig).
 */
export function WhatsappDisconnectedBanner() {
  const { user, refreshUser } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  const show =
    Boolean(user?.has_whatsapp_instance) && user?.is_whatsapp_connected === false;

  useEffect(() => {
    if (!show) {
      setModalOpen(false);
      return;
    }
    const id = setInterval(() => {
      void refreshUser();
    }, 15000);
    return () => clearInterval(id);
  }, [show, refreshUser]);

  // Fechou a conexão (pelo modal ou por outra aba) → some o banner e o modal.
  useEffect(() => {
    if (user?.is_whatsapp_connected) {
      setModalOpen(false);
    }
  }, [user?.is_whatsapp_connected]);

  if (!show) {
    return null;
  }

  const canReconnect = Boolean(user?.is_tenant_admin);

  return (
    <>
      <div className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-3 bg-red-600 p-3 text-center text-sm text-white shadow-sm">
        <span>
          ⚠️ ALERTA: Seu WhatsApp está desconectado e o bot parou de responder os clientes.
        </span>
        {canReconnect ? (
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="rounded-lg bg-white px-4 py-1.5 text-sm font-semibold text-red-700 shadow hover:bg-red-50"
          >
            Reconectar Agora
          </button>
        ) : (
          <span className="text-xs text-red-100">
            Peça a um administrador da empresa para reconectar.
          </span>
        )}
      </div>
      {canReconnect ? (
        <Modal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          className="max-h-[90vh] max-w-3xl overflow-y-auto p-4 sm:p-6"
        >
          <h3 className="pr-10 text-lg font-semibold text-gray-900 dark:text-white/90">
            Reconectar WhatsApp
          </h3>
          <p className="mt-1 mb-4 text-sm text-gray-600 dark:text-gray-400">
            Use o mesmo fluxo das Integrações: gere o QR e escaneie com o celular da loja.
          </p>
          <WhatsAppConfig
            embedded
            onConnected={() => {
              void refreshUser();
              setModalOpen(false);
            }}
          />
        </Modal>
      ) : null}
    </>
  );
}
