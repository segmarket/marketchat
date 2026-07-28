import { useCallback, useEffect, useState } from "react";
import { Calendar, Copy, Power } from "lucide-react";
import { toast } from "sonner";
import Button from "../ui/button/Button";
import Switch from "../form/switch/Switch";
import Input from "../form/input/InputField";
import { Modal } from "../ui/modal";
import {
  fetchBotSchedule,
  patchBotGlobalActive,
  saveBotSchedule,
} from "../../features/settings/api";
import type { BotScheduleDay } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

const DAY_LABELS = [
  "Segunda-feira",
  "Terça-feira",
  "Quarta-feira",
  "Quinta-feira",
  "Sexta-feira",
  "Sábado",
  "Domingo",
] as const;

function toTimeInput(value: string): string {
  const parts = (value || "09:00").split(":");
  return `${parts[0]?.padStart(2, "0") ?? "09"}:${parts[1]?.padStart(2, "0") ?? "00"}`;
}

function toApiTime(value: string): string {
  return `${toTimeInput(value)}:00`;
}

function emptyWeek(): BotScheduleDay[] {
  return DAY_LABELS.map((_, day) => ({
    day_of_week: day,
    is_active: false,
    start_time: "09:00:00",
    end_time: "18:00:00",
  }));
}

function applyDaysFromResponse(days: BotScheduleDay[]): BotScheduleDay[] {
  const byDay = new Map(days.map((d) => [d.day_of_week, d]));
  return emptyWeek().map((slot) => {
    const row = byDay.get(slot.day_of_week);
    return row
      ? {
          ...row,
          start_time: toApiTime(row.start_time),
          end_time: toApiTime(row.end_time),
        }
      : slot;
  });
}

export default function BotScheduleSettings() {
  const [days, setDays] = useState<BotScheduleDay[]>(emptyWeek);
  const [isBotActiveGlobal, setIsBotActiveGlobal] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [togglingGlobal, setTogglingGlobal] = useState(false);
  const [confirmOffOpen, setConfirmOffOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchBotSchedule();
      setIsBotActiveGlobal(data.is_bot_active_global !== false);
      setDays(applyDaysFromResponse(data.days));
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function updateDay(dayOfWeek: number, patch: Partial<BotScheduleDay>) {
    setDays((prev) =>
      prev.map((row) => (row.day_of_week === dayOfWeek ? { ...row, ...patch } : row)),
    );
  }

  function replicateWeekdays() {
    const monday = days.find((d) => d.day_of_week === 0);
    if (!monday) return;
    setDays((prev) =>
      prev.map((row) =>
        row.day_of_week >= 1 && row.day_of_week <= 4
          ? {
              ...row,
              is_active: monday.is_active,
              start_time: monday.start_time,
              end_time: monday.end_time,
            }
          : row,
      ),
    );
    toast.success("Expediente de segunda replicado para terça a sexta.");
  }

  async function setGlobalActive(next: boolean) {
    setTogglingGlobal(true);
    try {
      const data = await patchBotGlobalActive(next);
      setIsBotActiveGlobal(data.is_bot_active_global);
      setDays(applyDaysFromResponse(data.days));
      toast.success(
        next ? "Chatbot reativado para toda a conta." : "Chatbot desligado para toda a conta.",
      );
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setTogglingGlobal(false);
      setConfirmOffOpen(false);
    }
  }

  function onMasterToggle(checked: boolean) {
    if (!checked) {
      setConfirmOffOpen(true);
      return;
    }
    void setGlobalActive(true);
  }

  async function handleSave() {
    for (const day of days) {
      if (day.is_active && toTimeInput(day.start_time) >= toTimeInput(day.end_time)) {
        toast.error(
          `${DAY_LABELS[day.day_of_week]}: o término precisa ser depois do início.`,
        );
        return;
      }
    }

    setSaving(true);
    try {
      const payload = days.map((d) => ({
        ...d,
        start_time: toApiTime(d.start_time),
        end_time: toApiTime(d.end_time),
      }));
      const data = await saveBotSchedule(payload);
      setIsBotActiveGlobal(data.is_bot_active_global !== false);
      setDays(applyDaysFromResponse(data.days));
      toast.success("Horário comercial salvo com sucesso.");
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-2" aria-hidden>
        <div className="h-20 animate-pulse rounded-xl bg-gray-100 dark:bg-white/10" />
        <div className="h-10 animate-pulse rounded-lg bg-gray-100 dark:bg-white/10" />
        <div className="h-10 animate-pulse rounded-lg bg-gray-100 dark:bg-white/10" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <Power className="size-5" aria-hidden />
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                  Status Geral do Chatbot
                </h2>
                {isBotActiveGlobal ? (
                  <span className="rounded-full bg-success-50 px-2.5 py-0.5 text-xs font-semibold text-success-700 dark:bg-success-500/15 dark:text-success-400">
                    Online
                  </span>
                ) : (
                  <span className="rounded-full bg-error-50 px-2.5 py-0.5 text-xs font-semibold text-error-700 dark:bg-error-500/15 dark:text-error-400">
                    Pausado (Chave Geral)
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Desliga o bot em todas as conversas, com prioridade sobre horário comercial e
                atendimento humano.
              </p>
            </div>
          </div>
          <Switch
            label={isBotActiveGlobal ? "Ligado" : "Desligado"}
            checked={isBotActiveGlobal}
            disabled={togglingGlobal}
            onChange={onMasterToggle}
          />
        </div>
      </div>

      <div
        className={
          isBotActiveGlobal ? undefined : "opacity-50 pointer-events-none select-none"
        }
        aria-disabled={!isBotActiveGlobal}
      >
        <div className="mb-4 flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
            <Calendar className="size-4" aria-hidden />
          </span>
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">
              Horário Comercial (Pausa do Bot)
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Defina o horário em que você ou sua equipe atende. Durante esses horários, o
              bot ficará pausado. Fora desses horários (noites, madrugadas e folgas), o bot
              assumirá automaticamente.
            </p>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
          <ul className="divide-y divide-gray-200 dark:divide-gray-800">
            {days.map((day) => {
              const isMonday = day.day_of_week === 0;
              return (
                <li
                  key={day.day_of_week}
                  className="flex flex-wrap items-center gap-x-3 gap-y-2 bg-white px-3 py-2.5 dark:bg-white/[0.03] sm:flex-nowrap"
                >
                  <Switch
                    label={day.is_active ? "Expediente" : "Folga"}
                    checked={day.is_active}
                    onChange={(checked) => updateDay(day.day_of_week, { is_active: checked })}
                  />

                  <div className="flex min-w-[9rem] flex-1 items-center gap-2">
                    <span className="text-sm font-medium text-gray-800 dark:text-white/90">
                      {DAY_LABELS[day.day_of_week]}
                    </span>
                    {isMonday ? (
                      <button
                        type="button"
                        onClick={replicateWeekdays}
                        className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-white/5"
                      >
                        <Copy className="size-3" aria-hidden />
                        Replicar para todos os dias úteis
                      </button>
                    ) : null}
                  </div>

                  {day.is_active ? (
                    <div className="ml-auto flex items-center gap-2">
                      <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                        Início
                        <Input
                          type="time"
                          className="!h-9 w-[7.5rem] !px-2 !py-1.5"
                          value={toTimeInput(day.start_time)}
                          onChange={(e) =>
                            updateDay(day.day_of_week, {
                              start_time: toApiTime(e.target.value),
                            })
                          }
                        />
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                        Fim
                        <Input
                          type="time"
                          className="!h-9 w-[7.5rem] !px-2 !py-1.5"
                          value={toTimeInput(day.end_time)}
                          onChange={(e) =>
                            updateDay(day.day_of_week, {
                              end_time: toApiTime(e.target.value),
                            })
                          }
                        />
                      </label>
                    </div>
                  ) : (
                    <p className="ml-auto text-sm text-gray-500 dark:text-gray-400">
                      Sem expediente. Bot ativo 24h
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        <div className="mt-5 flex justify-end">
          <Button
            type="button"
            variant="primary"
            onClick={() => void handleSave()}
            disabled={saving || !isBotActiveGlobal}
          >
            {saving ? "Salvando…" : "Salvar horários"}
          </Button>
        </div>
      </div>

      <Modal
        isOpen={confirmOffOpen}
        onClose={() => setConfirmOffOpen(false)}
        className="mx-4 max-w-md p-6"
      >
        <h3 className="pr-8 text-lg font-semibold text-gray-900 dark:text-white">
          Desligar o chatbot?
        </h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Tem certeza? O bot deixará de atender todos os novos clientes e ignorará sua grade
          de horários até ser reativado.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setConfirmOffOpen(false)}
            disabled={togglingGlobal}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => void setGlobalActive(false)}
            disabled={togglingGlobal}
            className="!bg-error-500 hover:!bg-error-600"
          >
            {togglingGlobal ? "Desligando…" : "Desligar Bot"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
