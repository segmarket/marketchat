import { useState } from "react";
import ListSearchPanel, { type SearchFieldConfig } from "../common/ListSearchPanel";
import {
  emptyProductsSearchFilters,
  hasActiveProductsFilters,
  type ProductsSearchFilters,
} from "../../features/products/searchTypes";

const FIELDS: SearchFieldConfig[] = [
  {
    type: "text",
    key: "sku",
    id: "product-search-sku",
    label: "SKU",
    placeholder: "Ex.: ARROZ-5KG",
  },
  {
    type: "text",
    key: "name",
    id: "product-search-name",
    label: "Nome do produto",
    placeholder: "Ex.: Arroz integral",
  },
  {
    type: "select",
    key: "status",
    id: "product-search-status",
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
  onSearch: (filters: ProductsSearchFilters) => void;
  onClear: () => void;
};

export default function ProductsSearchPanel({ busy, resultCount, onSearch, onClear }: Props) {
  const [draft, setDraft] = useState<ProductsSearchFilters>(emptyProductsSearchFilters);

  function handleFieldChange(key: string, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function handleSearch() {
    onSearch(draft);
  }

  function handleClear() {
    const empty = emptyProductsSearchFilters();
    setDraft(empty);
    onClear();
  }

  return (
    <ListSearchPanel
      ariaLabel="Buscar produto"
      title="Buscar produto"
      description="Filtre por SKU, nome ou status do produto."
      fields={FIELDS}
      values={draft}
      onFieldChange={handleFieldChange}
      busy={busy}
      resultCount={resultCount}
      resultSingular="produto encontrado"
      resultPlural="produtos encontrados"
      onSearch={handleSearch}
      onClear={handleClear}
      hasActiveFilters={hasActiveProductsFilters(draft)}
    />
  );
}
