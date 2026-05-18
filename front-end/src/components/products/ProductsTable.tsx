import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";
import Button from "../ui/button/Button";
import { formatCurrencyBRL } from "../../features/products/format";
import type { Product } from "../../features/products/types";
import ProductStatusBadge from "./ProductStatusBadge";

type Props = {
  products: Product[];
  loading: boolean;
  filtersActive?: boolean;
  onEdit: (product: Product) => void;
};

function SkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((row) => (
        <TableRow key={row}>
          {[1, 2, 3, 4, 5].map((col) => (
            <TableCell key={col} className="px-4 py-3">
              <div className="h-4 w-full max-w-[10rem] animate-pulse rounded bg-gray-100 dark:bg-white/10" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export default function ProductsTable({ products, loading, filtersActive = false, onEdit }: Props) {
  if (!loading && products.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {filtersActive
          ? "Nenhum produto encontrado com os filtros informados."
          : "Nenhum produto cadastrado. Importe uma planilha ou use o modelo para começar."}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              SKU
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Nome
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Preço
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Status
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Ações
            </TableCell>
          </TableRow>
        </TableHeader>
        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
          {loading ? (
            <SkeletonRows />
          ) : (
            products.map((product) => (
              <TableRow key={product.id}>
                <TableCell className="px-4 py-3 text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {product.sku}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {product.name}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {formatCurrencyBRL(product.price)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <ProductStatusBadge status={product.status} />
                </TableCell>
                <TableCell className="px-4 py-3">
                  <Button size="sm" variant="outline" onClick={() => onEdit(product)}>
                    Editar
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
