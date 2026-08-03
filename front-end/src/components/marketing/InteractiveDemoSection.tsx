import { useState } from "react";
import WhatsAppDemoChat, { DEMO_CHAT_SUGGESTIONS } from "./WhatsAppDemoChat";

const chipClassName =
  "shrink-0 snap-start whitespace-nowrap rounded-full bg-white px-3.5 py-2 text-sm font-medium text-brand-800 shadow-sm ring-1 ring-brand-100 transition hover:bg-brand-50 hover:ring-brand-200";

export default function InteractiveDemoSection() {
  const [draft, setDraft] = useState("");
  const [mediaTrigger, setMediaTrigger] = useState(0);

  return (
    <section
      id="demo-bot"
      className="scroll-mt-24 bg-slate-50 px-2 py-10 sm:px-6 sm:py-16 lg:px-8 lg:py-20"
    >
      <div className="mx-auto grid max-w-7xl items-center gap-8 overflow-x-hidden lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0 max-w-full">
          <p className="mb-3 inline-flex rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-200">
            Demonstração ao vivo
          </p>
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Teste o cérebro da nossa IA na prática
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-gray-600">
            Muito mais que um buscador de produtos. Nosso bot lida com clientes bravos,
            ignora spams de fornecedores, perdoa erros de digitação e aciona sua equipe
            quando necessário.
          </p>

          <p className="mt-6 text-sm font-semibold text-gray-900 sm:mt-8">
            Escolha um cenário e envie no chat:
          </p>
          <div className="mt-3 flex max-w-full gap-2 overflow-x-auto overflow-y-hidden pb-2 snap-x snap-mandatory no-scrollbar md:flex-wrap md:overflow-visible md:pb-0 md:snap-none">
            {DEMO_CHAT_SUGGESTIONS.map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => setDraft(item.text)}
                className={chipClassName}
              >
                {item.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setMediaTrigger((n) => n + 1)}
              className={chipClassName}
            >
              📷 Simular Envio de Foto
            </button>
          </div>
          <p className="mt-3 text-sm text-gray-500">
            Para ver o Pix: compre um produto, finalize até o bot pedir a foto e use o
            atalho ou a câmera. Fora desse momento, a imagem é rejeitada como no WhatsApp
            real.
          </p>
        </div>

        <div className="relative z-10 w-full min-w-0 max-w-full lg:flex lg:justify-end">
          <WhatsAppDemoChat
            draft={draft}
            onDraftChange={setDraft}
            mediaTrigger={mediaTrigger}
          />
        </div>
      </div>
    </section>
  );
}
