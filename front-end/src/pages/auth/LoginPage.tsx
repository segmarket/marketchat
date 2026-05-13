import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "../AuthPages/AuthPageLayout";
import SignInForm from "../../components/auth/SignInForm";

/** Página de login em `/login` (alias legado: `/signin`). */
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
