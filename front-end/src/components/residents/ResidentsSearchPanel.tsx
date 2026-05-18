import { useState } from "react";
import ListSearchPanel, { type SearchFieldConfig } from "../common/ListSearchPanel";
import { maskPhoneInput } from "../../features/residents/format";
import type { ResidentMarketOption } from "../../features/residents/types";
import {
  emptyResidentsSearchFilters,
  hasActiveResidentsFilters,
  type ResidentsSearchFilters,
} from "../../features/residents/searchTypes";

type Props = {
  markets: ResidentMarketOption[];
  busy?: boolean;
  resultCount?: number;
  onSearch: (filters: ResidentsSearchFilters) => void;
  onClear: () => void;
};

export default function ResidentsSearchPanel({
  markets,
  busy = false,
  resultCount,
  onSearch,
  onClear,
}: Props) {
  const [draft, setDraft] = useState<ResidentsSearchFilters>(emptyResidentsSearchFilters);

  const fields: SearchFieldConfig[] = [
    {
      type: "text",
      key: "name",
      id: "resident-search-name",
      label: "Nome",
      placeholder: "Ex.: Maria Silva",
    },
    {
      type: "text",
      key: "phone",
      id: "resident-search-phone",
      label: "WhatsApp",
      placeholder: "(11) 99999-9999",
      inputType: "tel",
      formatOnChange: maskPhoneInput,
    },
    {
      type: "select",
      key: "marketId",
      id: "resident-search-market",
      label: "Condomínio / Mercado",
      options: [
        { value: "", label: "Todos os condomínios" },
        ...markets.map((m) => ({ value: String(m.id), label: m.name })),
      ],
    },
  ];

  function handleFieldChange(key: string, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function handleSearch() {
    onSearch(draft);
  }

  function handleClear() {
    const empty = emptyResidentsSearchFilters();
    setDraft(empty);
    onClear();
  }

  return (
    <ListSearchPanel
      ariaLabel="Buscar morador"
      title="Buscar morador"
      description="Filtre por nome, WhatsApp ou condomínio cadastrado."
      fields={fields}
      values={draft}
      onFieldChange={handleFieldChange}
      busy={busy}
      resultCount={resultCount}
      resultSingular="morador encontrado"
      resultPlural="moradores encontrados"
      onSearch={handleSearch}
      onClear={handleClear}
      hasActiveFilters={hasActiveResidentsFilters(draft)}
    />
  );
}
