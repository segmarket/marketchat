import { Link } from "react-router";
import LegalDocumentLayout from "../../components/marketing/LegalDocumentLayout";
import {
  COMPANY_LEGAL_INTRO,
  LEGAL_CONTACT_EMAIL,
  LEGAL_LAST_UPDATED,
  platformFeePercentLabel,
} from "../../constants/legalContent";

export default function TermsOfServicePage() {
  const feePercent = platformFeePercentLabel();

  return (
    <LegalDocumentLayout
      title="Termos de Uso | MarketChat"
      description="Termos de uso da plataforma MarketChat para operadores de mercados autônomos."
      path="/termos"
    >
      <h1 className="text-3xl font-bold text-gray-900">Termos de Uso – MarketChat</h1>
      <p className="mt-2 text-sm text-gray-600">Última atualização: {LEGAL_LAST_UPDATED}</p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-gray-700">
        <p>
          {COMPANY_LEGAL_INTRO}. Ao acessar nosso painel e utilizar nossa tecnologia, você
          (Cliente/Operador) concorda com as condições abaixo e com nossa{" "}
          <Link to="/privacidade" className="font-medium text-brand-600 hover:underline">
            Política de Privacidade
          </Link>
          .
        </p>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">1. O Serviço</h2>
          <p className="mt-3">
            O MarketChat é uma plataforma de Software as a Service (SaaS) que fornece um assistente
            virtual integrado ao WhatsApp e um painel administrativo para gestão de vendas,
            automação de pagamentos (Pix) e monitoramento de mercados autônomos. Nós fornecemos a
            tecnologia, não os produtos físicos.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">
            2. Responsabilidades do Operador (Cliente)
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong>Abastecimento e Precificação:</strong> Você é o único responsável por
              abastecer seu mercado, precificar os produtos no painel do MarketChat e garantir a
              validade e qualidade dos itens vendidos.
            </li>
            <li>
              <strong>Legalidade:</strong> É expressamente proibido utilizar nossa plataforma para a
              venda de produtos ilícitos ou em desacordo com as regras do condomínio/local de
              instalação.
            </li>
            <li>
              <strong>Relacionamento com o Morador:</strong> O MarketChat atua como intermediário
              tecnológico. Disputas sobre produtos estragados, devoluções ou mau comportamento de
              moradores devem ser resolvidas diretamente entre você e o consumidor final.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">
            3. Pagamentos, Taxas e Saques (Carteira Virtual)
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong>Mensalidade:</strong> O uso da plataforma é condicionado ao pagamento da
              assinatura mensal acordada no momento do cadastro. O atraso no pagamento pode resultar
              na suspensão automática do robô do WhatsApp.
            </li>
            <li>
              <strong>Taxa Transacional:</strong> Sobre cada venda realizada via Pix na plataforma,
              incide uma taxa de processamento de {feePercent}%. O valor líquido é creditado na
              Carteira Virtual (Ledger) do Cliente.
            </li>
            <li>
              <strong>Saques:</strong> O saldo disponível pode ser transferido para a conta
              bancária do Cliente via chave Pix cadastrada no painel, sujeito aos prazos de
              processamento do gateway parceiro (Asaas) e disponibilidade do sistema bancário.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">4. Disponibilidade do Sistema (SLA)</h2>
          <p className="mt-3">
            O MarketChat empenha os melhores esforços para manter a plataforma online 24/7. Contudo,
            por dependermos de serviços de terceiros (WhatsApp/Meta e Gateways Financeiros), não
            podemos garantir imunidade absoluta a instabilidades ou quedas operacionais que fujam ao
            nosso controle técnico.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">5. Suspensão e Cancelamento</h2>
          <p className="mt-3">
            Você pode cancelar sua assinatura a qualquer momento, sem multa. O MarketChat reserva-se
            o direito de suspender contas que violem estes Termos de Uso, apresentem alto índice de
            fraudes ou realizem atividades suspeitas na API de pagamentos.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">6. Contato</h2>
          <p className="mt-3">
            Dúvidas sobre estes termos devem ser encaminhadas para:{" "}
            <a
              href={`mailto:${LEGAL_CONTACT_EMAIL}`}
              className="font-medium text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-sm"
            >
              {LEGAL_CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>
      </div>
    </LegalDocumentLayout>
  );
}
