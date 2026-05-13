import GridShape from "../../components/common/GridShape";

export default function AuthLoadingPage() {
  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen p-6 overflow-hidden z-1">
      <GridShape />
      <div className="relative z-10 flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-gray-200 rounded-full border-t-brand-500 animate-spin dark:border-gray-700 dark:border-t-brand-400" />
        <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Carregando sessão...</p>
      </div>
    </div>
  );
}
