import type { FormEvent, ReactNode } from "react";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";

export type SearchFieldConfig =
  | {
      type: "text";
      key: string;
      id: string;
      label: string;
      placeholder?: string;
      inputType?: string;
      formatOnChange?: (value: string) => string;
    }
  | {
      type: "select";
      key: string;
      id: string;
      label: string;
      options: { value: string; label: string }[];
    };

type Props = {
  ariaLabel: string;
  title: string;
  description: string;
  fields: SearchFieldConfig[];
  values: Record<string, string>;
  onFieldChange: (key: string, value: string) => void;
  busy?: boolean;
  resultCount?: number;
  resultSingular: string;
  resultPlural: string;
  onSearch: () => void;
  onClear: () => void;
  hasActiveFilters: boolean;
  actions?: ReactNode;
};

const selectClassName =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

function gridColsClass(count: number): string {
  if (count <= 1) return "grid-cols-1";
  if (count === 2) return "grid-cols-1 md:grid-cols-2";
  return "grid-cols-1 md:grid-cols-3";
}

export default function ListSearchPanel({
  ariaLabel,
  title,
  description,
  fields,
  values,
  onFieldChange,
  busy = false,
  resultCount,
  resultSingular,
  resultPlural,
  onSearch,
  onClear,
  hasActiveFilters,
  actions,
}: Props) {
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSearch();
  }

  const resultLabel =
    resultCount === undefined
      ? undefined
      : `${resultCount} ${resultCount === 1 ? resultSingular : resultPlural}`;

  return (
    <section
      aria-label={ariaLabel}
      className="mb-6 rounded-xl border border-gray-200 bg-gray-50/80 p-4 dark:border-gray-800 dark:bg-white/[0.02] md:p-5"
    >
      <header className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-800 dark:text-white/90">{title}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        {resultLabel !== undefined && (
          <p className="text-sm font-medium text-gray-600 dark:text-gray-300">{resultLabel}</p>
        )}
      </header>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className={`grid gap-4 ${gridColsClass(fields.length)}`}>
          {fields.map((field) => {
            if (field.type === "select") {
              return (
                <div key={field.key}>
                  <label
                    htmlFor={field.id}
                    className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    {field.label}
                  </label>
                  <select
                    id={field.id}
                    value={values[field.key] ?? ""}
                    onChange={(e) => onFieldChange(field.key, e.target.value)}
                    disabled={busy}
                    className={selectClassName}
                  >
                    {field.options.map((opt) => (
                      <option key={opt.value || "__all__"} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              );
            }

            return (
              <div key={field.key}>
                <label
                  htmlFor={field.id}
                  className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  {field.label}
                </label>
                <Input
                  id={field.id}
                  type={field.inputType ?? "text"}
                  placeholder={field.placeholder}
                  value={values[field.key] ?? ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    onFieldChange(field.key, field.formatOnChange ? field.formatOnChange(raw) : raw);
                  }}
                  disabled={busy}
                />
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Buscando…" : "Buscar"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={busy || !hasActiveFilters}
            onClick={onClear}
          >
            Limpar filtros
          </Button>
          {actions}
        </div>
      </form>
    </section>
  );
}
