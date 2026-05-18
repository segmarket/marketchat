import { BarChart3, Bell, TrendingUp } from "lucide-react";

export default function DashboardMockup() {
  return (
    <div className="w-full max-w-[340px] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl ring-1 ring-gray-100">
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
        <p className="text-sm font-semibold text-gray-800">Painel Operacional</p>
        <p className="text-xs text-gray-500">Mercado Aurora · hoje</p>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4">
        <div className="rounded-lg border border-gray-100 bg-brand-50 p-3">
          <TrendingUp className="h-5 w-5 text-brand-600" />
          <p className="mt-2 text-xs text-gray-500">Retenção do robô</p>
          <p className="text-lg font-bold text-gray-900">87%</p>
        </div>
        <div className="rounded-lg border border-gray-100 bg-success-50 p-3">
          <BarChart3 className="h-5 w-5 text-success-600" />
          <p className="mt-2 text-xs text-gray-500">Pico 18h–21h</p>
          <p className="text-lg font-bold text-gray-900">142 msgs</p>
        </div>
      </div>
      <div className="mx-4 mb-4 flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 px-3 py-2">
        <Bell className="mt-0.5 h-4 w-4 shrink-0 text-error-600" />
        <div>
          <p className="text-xs font-semibold text-error-700">Alerta crítico</p>
          <p className="text-xs text-error-600">Falha no pagamento — pedido #1842</p>
        </div>
      </div>
      <div className="h-24 bg-gradient-to-t from-brand-50 to-white px-4">
        <div className="flex h-full items-end justify-between gap-1">
          {[40, 65, 45, 80, 55, 90, 70].map((h, i) => (
            <div
              key={i}
              className="w-full rounded-t bg-brand-400"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
