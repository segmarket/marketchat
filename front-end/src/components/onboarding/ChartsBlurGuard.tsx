import { Lock } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  locked: boolean;
  children: ReactNode;
};

export default function ChartsBlurGuard({ locked, children }: Props) {
  if (!locked) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      <div className="blur-[4px] pointer-events-none select-none opacity-60">{children}</div>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-gray-200 bg-white shadow-theme-sm dark:border-gray-700 dark:bg-gray-900">
          <Lock className="size-5 text-gray-600 dark:text-gray-300" aria-hidden />
        </div>
        <p className="max-w-md text-sm font-medium text-gray-700 dark:text-gray-300">
          Conclua as missões de configuração acima para liberar as estatísticas em tempo real do
          seu condomínio.
        </p>
      </div>
    </div>
  );
}
