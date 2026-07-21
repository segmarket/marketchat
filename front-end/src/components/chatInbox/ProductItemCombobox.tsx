import { useEffect, useId, useRef, useState } from "react";
import {
  searchProducts,
  type ProductSearchHit,
} from "../../features/products/api";
import Input from "../form/input/InputField";

export type ProductItemSelection = {
  name: string;
  price: string;
};

type Props = {
  value: string;
  onChange: (name: string) => void;
  onSelect: (item: ProductItemSelection) => void;
  placeholder?: string;
};

function formatUnitPrice(raw: string): string {
  const n = Number.parseFloat(raw);
  if (Number.isNaN(n)) return raw;
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function ProductItemCombobox({
  value,
  onChange,
  onSelect,
  placeholder = "Nome do item",
}: Props) {
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<ProductSearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const requestSeq = useRef(0);

  useEffect(() => {
    const q = value.trim();
    if (q.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const seq = ++requestSeq.current;
    const timer = window.setTimeout(() => {
      void searchProducts(q)
        .then((hits) => {
          if (seq !== requestSeq.current) return;
          setResults(hits);
          setHighlight(0);
          setOpen(true);
        })
        .catch(() => {
          if (seq !== requestSeq.current) return;
          setResults([]);
        })
        .finally(() => {
          if (seq !== requestSeq.current) return;
          setLoading(false);
        });
    }, 250);

    return () => window.clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    function onDocPointerDown(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocPointerDown);
    return () => document.removeEventListener("mousedown", onDocPointerDown);
  }, []);

  function pick(hit: ProductSearchHit) {
    onSelect({ name: hit.name, price: formatUnitPrice(hit.price) });
    setOpen(false);
    setResults([]);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) {
      if (e.key === "Escape") setOpen(false);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((i) => (i + 1) % results.length);
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((i) => (i - 1 + results.length) % results.length);
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const hit = results[highlight];
      if (hit) pick(hit);
      return;
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const showList = open && (loading || results.length > 0);

  return (
    <div ref={wrapRef} className="relative">
      <Input
        type="text"
        placeholder={placeholder}
        value={value}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (results.length > 0) setOpen(true);
        }}
        onKeyDown={onKeyDown}
        onBlur={() => {
          // Fecha após o click na lista processar
          window.setTimeout(() => {
            if (!wrapRef.current?.contains(document.activeElement)) {
              setOpen(false);
            }
          }, 150);
        }}
      />
      {showList ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-theme-md dark:border-gray-700 dark:bg-gray-900"
        >
          {loading && results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
              Buscando…
            </li>
          ) : (
            results.map((hit, index) => (
              <li key={hit.id} role="option" aria-selected={index === highlight}>
                <button
                  type="button"
                  className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm ${
                    index === highlight
                      ? "bg-brand-50 text-brand-700 dark:bg-white/10 dark:text-white"
                      : "text-gray-800 hover:bg-gray-50 dark:text-white/90 dark:hover:bg-white/5"
                  }`}
                  onMouseDown={(e) => e.preventDefault()}
                  onMouseEnter={() => setHighlight(index)}
                  onClick={() => pick(hit)}
                >
                  <span className="truncate">{hit.name}</span>
                  <span className="shrink-0 text-xs text-gray-500 dark:text-gray-400">
                    {formatUnitPrice(hit.price)}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
