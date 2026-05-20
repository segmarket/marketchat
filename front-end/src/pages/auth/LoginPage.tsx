import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "../AuthPages/AuthPageLayout";
import SignInForm from "../../components/auth/SignInForm";

/** Página de autenticação canônica em `/signin`; `/login` redireciona para cá. */
export default function LoginPage() {
  return (
    <>
      <PageMeta title="Entrar | MarketChat" description="Acesse sua conta MarketChat." />
      <AuthLayout>
        <SignInForm />
      </AuthLayout>
    </>
  );
}
