import { Link } from "react-router";
import PageMeta from "../../components/common/PageMeta";
import MarketingBrandLogo from "../../components/marketing/MarketingBrandLogo";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white font-outfit text-gray-900 antialiased">
      <PageMeta
        title="Política de Privacidade | MarketChat"
        description="Como o MarketChat coleta, usa e protege seus dados pessoais."
      />
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="inline-flex items-center gap-2">
            <MarketingBrandLogo showWordmark={false} />
          </Link>
          <Link to="/" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            Voltar à landing
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-bold text-gray-900">Política de Privacidade</h1>
        <p className="mt-2 text-sm text-gray-500">Última atualização: maio de 2026</p>

        <div className="prose prose-gray mt-8 max-w-none space-y-6 text-sm leading-relaxed text-gray-700">
          <section>
            <h2 className="text-lg font-semibold text-gray-900">1. Quem somos</h2>
            <p>
              O MarketChat é uma plataforma de gestão para mercados autônomos. Esta política descreve
              como tratamos dados pessoais de visitantes, leads e clientes.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">2. Dados que coletamos</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Dados de cadastro: nome, e-mail, telefone, empresa e dados de pagamento.</li>
              <li>Dados de navegação: cookies, endereço IP, páginas visitadas e origem da campanha (UTMs).</li>
              <li>Parâmetros de marketing: utm_source, utm_medium, utm_campaign, gclid e fbclid quando presentes na URL.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">3. Cookies e tecnologias similares</h2>
            <p>
              Utilizamos cookies essenciais para o funcionamento do site e cookies analíticos/de marketing
              (via Google Tag Manager) para medir campanhas e melhorar conversões. Você pode aceitar ou
              recusar cookies não essenciais pelo banner exibido na landing page.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">4. Finalidade do tratamento</h2>
            <p>
              Os dados são utilizados para criar e gerenciar sua conta, processar assinaturas, prestar
              suporte, cumprir obrigações legais e mensurar a eficácia de campanhas publicitárias.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">5. Compartilhamento</h2>
            <p>
              Podemos compartilhar dados com provedores de pagamento (Asaas), infraestrutura de
              hospedagem e ferramentas de analytics quando necessário para operar o serviço, sempre
              observando medidas de segurança adequadas.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">6. Seus direitos (LGPD)</h2>
            <p>
              Você pode solicitar acesso, correção, exclusão ou portabilidade dos seus dados, além de
              revogar consentimentos, entrando em contato pelo e-mail{" "}
              <a href="mailto:contato@marketchat.com.br" className="text-brand-600 hover:underline">
                contato@marketchat.com.br
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900">7. Retenção</h2>
            <p>
              Mantemos os dados pelo tempo necessário para cumprir as finalidades descritas e obrigações
              legais, incluindo registros de atribuição de campanhas vinculados à criação da conta.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
