import { Link } from "react-router";
import LegalDocumentLayout from "../../components/marketing/LegalDocumentLayout";
import {
  COMPANY_LEGAL_INTRO,
  DPO_EMAIL,
  LEGAL_LAST_UPDATED,
} from "../../constants/legalContent";

export default function PrivacyPolicyPage() {
  return (
    <LegalDocumentLayout
      title="Política de Privacidade | MarketChat"
      description="Como o MarketChat coleta, usa e protege os dados de operadores e moradores, em conformidade com a LGPD."
      path="/privacidade"
    >
      <h1 className="text-3xl font-bold text-gray-900">Política de Privacidade – MarketChat</h1>
      <p className="mt-2 text-sm text-gray-600">Última atualização: {LEGAL_LAST_UPDATED}</p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-gray-700">
        <p>
          {COMPANY_LEGAL_INTRO} valoriza a privacidade de seus usuários. Esta Política descreve como
          coletamos, usamos e protegemos os dados pessoais de nossos Clientes (Operadores de Mercado)
          e dos Consumidores finais (Moradores), em conformidade com a Lei Geral de Proteção de Dados
          (LGPD — Lei nº 13.709/2018).
        </p>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">1. Dados que Coletamos</h2>
          <p className="mt-3">
            <strong>Do Cliente (Operador do Mercado):</strong> Nome completo, CPF/CNPJ, e-mail,
            telefone, chave Pix e dados de faturamento para processamento da assinatura.
          </p>
          <p className="mt-3">
            <strong>Do Consumidor (Morador):</strong> Número de telefone (via WhatsApp), nome (se
            fornecido), histórico de conversas com o assistente virtual, registros de compras, código
            Pix transacionado e fotos ambientais (ex.: verificação de geladeira/Photo-Lock).{" "}
            <strong>Não armazenamos dados de cartão de crédito dos consumidores.</strong>
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">2. Finalidade do Uso dos Dados</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>Viabilizar o atendimento automatizado e o processamento de vendas via WhatsApp.</li>
            <li>
              Prevenção de fraudes e auditoria de incidentes de segurança (uso de fotos do local).
            </li>
            <li>Processamento financeiro e repasse de valores (Saques Pix).</li>
            <li>Suporte técnico e envio de comunicações essenciais sobre o sistema.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">3. Compartilhamento de Dados</h2>
          <p className="mt-3">
            O MarketChat <strong>não vende</strong> seus dados. Compartilhamos informações
            estritamente necessárias com parceiros de infraestrutura tecnológica:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong>Gateways de pagamento:</strong> Para processamento de assinaturas,
              geração de cobranças Pix e transferências bancárias.
            </li>
            <li>
              <strong>Provedores de comunicação:</strong> Para tráfego de mensagens no WhatsApp
              (incluindo a infraestrutura oficial do WhatsApp Business).
            </li>
            <li>
              <strong>Hospedagem em Nuvem:</strong> Para armazenamento seguro do banco de dados e
              arquivos.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">4. Retenção e Exclusão de Dados</h2>
          <p className="mt-3">
            Os dados são armazenados pelo tempo necessário para a prestação do serviço.
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5">
            <li>
              <strong>Fotos de Auditoria (Photo-Lock):</strong> São excluídas automaticamente de
              nossos servidores após 30 dias.
            </li>
            <li>
              <strong>Dados Financeiros:</strong> Por exigência do Banco Central e leis fiscais
              brasileiras, registros de transações (extratos de Pix) são mantidos por até 5 (cinco)
              anos, não podendo ser apagados antes deste prazo, mesmo mediante solicitação.
            </li>
            <li>
              <strong>Anonimização:</strong> Consumidores podem solicitar a exclusão de seus dados
              de contato. O MarketChat realizará a anonimização irreversível do número de telefone
              e nome, mantendo apenas os dados transacionais essenciais.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900">5. Seus Direitos (Art. 18 da LGPD)</h2>
          <p className="mt-3">
            Você tem direito de confirmar a existência de tratamento, acessar seus dados, corrigir
            informações incompletas, solicitar anonimização e revogar o consentimento.
          </p>
          <p className="mt-3">
            Para exercer seus direitos, entre em contato com nosso Encarregado de Proteção de Dados
            (DPO) através do e-mail:{" "}
            <a
              href={`mailto:${DPO_EMAIL}`}
              className="font-medium text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-sm"
            >
              {DPO_EMAIL}
            </a>
            .
          </p>
        </section>

        <p className="border-t border-gray-200 pt-6 text-gray-600">
          Consulte também nossos{" "}
          <Link to="/termos" className="font-medium text-brand-600 hover:underline">
            Termos de Uso
          </Link>
          .
        </p>
      </div>
    </LegalDocumentLayout>
  );
}
