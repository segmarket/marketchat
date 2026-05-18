import { useState } from "react";
import ListSearchPanel, { type SearchFieldConfig } from "../common/ListSearchPanel";
import {
  emptyMarketsSearchFilters,
  hasActiveMarketsFilters,
  type MarketsSearchFilters,
} from "../../features/markets/searchTypes";

const FIELDS: SearchFieldConfig[] = [
  {
    type: "text",
    key: "name",
    id: "market-search-name",
    label: "Nome do condomínio",
    placeholder: "Ex.: Vista Alegre",
  },
  {
    type: "text",
    key: "address",
    id: "market-search-address",
    label: "Endereço",
    placeholder: "Rua, bairro ou cidade",
  },
  {
    type: "select",
    key: "status",
    id: "market-search-status",
    label: "Status",
    options: [
      { value: "", label: "Todos os status" },
      { value: "active", label: "Ativo" },
      { value: "inactive", label: "Inativo" },
    ],
  },
];

type Props = {
  busy?: boolean;
  resultCount?: number;
  onSearch: (filters: MarketsSearchFilters) => void;
  onClear: () => void;
};

export default function MarketsSearchPanel({ busy, resultCount, onSearch, onClear }: Props) {
  const [draft, setDraft] = useState<MarketsSearchFilters>(emptyMarketsSearchFilters);

  function handleFieldChange(key: string, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function handleSearch() {
    onSearch(draft);
  }

  function handleClear() {
    const empty = emptyMarketsSearchFilters();
    setDraft(empty);
    onClear();
  }

  return (
    <ListSearchPanel
      ariaLabel="Buscar mercado"
      title="Buscar mercado"
      description="Filtre por nome, endereço ou status do condomínio."
      fields={FIELDS}
      values={draft}
      onFieldChange={handleFieldChange}
      busy={busy}
      resultCount={resultCount}
      resultSingular="mercado encontrado"
      resultPlural="mercados encontrados"
      onSearch={handleSearch}
      onClear={handleClear}
      hasActiveFilters={hasActiveMarketsFilters(draft)}
    />
  );
}
