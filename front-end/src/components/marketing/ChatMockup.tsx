export default function ChatMockup() {
  return (
    <div className="mx-auto w-full max-w-[280px] overflow-hidden rounded-[2rem] border-4 border-gray-800 bg-gray-900 shadow-2xl">
      <div className="bg-[#075E54] px-4 py-3">
        <p className="text-sm font-semibold text-white">Mercado Condomínio</p>
        <p className="text-xs text-white/80">online</p>
      </div>
      <div className="min-h-[320px] space-y-3 bg-[#ECE5DD] p-4">
        <div className="ml-auto max-w-[85%] rounded-lg rounded-tr-none bg-[#DCF8C6] px-3 py-2 text-sm text-gray-800 shadow-sm">
          Oi
        </div>
        <div className="max-w-[85%] rounded-lg rounded-tl-none bg-white px-3 py-2 text-sm text-gray-800 shadow-sm">
          Olá, <span className="font-semibold">Maria</span>! Bem-vinda ao mercado do{" "}
          <span className="font-medium">Residencial Aurora</span>. O que deseja hoje?
        </div>
        <div className="ml-auto max-w-[85%] rounded-lg rounded-tr-none bg-[#DCF8C6] px-3 py-2 text-sm text-gray-800 shadow-sm">
          quero uma coquinha zero
        </div>
        <div className="max-w-[85%] rounded-lg rounded-tl-none bg-white px-3 py-2 text-sm text-gray-800 shadow-sm">
          Encontrei: <span className="font-semibold">Coca Cola Lata Zero 350ml</span> — R$
          5,90. Adicionar ao carrinho?
        </div>
        <div className="ml-auto max-w-[85%] rounded-lg rounded-tr-none bg-[#DCF8C6] px-3 py-2 text-sm text-gray-800 shadow-sm">
          sim, pode adicionar
        </div>
      </div>
    </div>
  );
}
