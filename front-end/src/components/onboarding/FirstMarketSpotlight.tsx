import type { ReactNode } from "react";
import OnboardingSpotlight from "./OnboardingSpotlight";

const FIRST_MARKET_MESSAGE =
  "Vamos começar. Cadastre seu primeiro condomínio para liberar as estatísticas do seu painel.";

type Props = {
  children: ReactNode;
};

export default function FirstMarketSpotlight({ children }: Props) {
  return (
    <OnboardingSpotlight message={FIRST_MARKET_MESSAGE} align="end">
      {children}
    </OnboardingSpotlight>
  );
}
