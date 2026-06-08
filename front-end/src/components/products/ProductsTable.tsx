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

const mobileCardClassName =
  "mb-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03]";

function SkeletonTableRows() {
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

function SkeletonMobileCards() {
  return (
    <div className="space-y-3 md:hidden">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 animate-pulse rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5"
        />
      ))}
    </div>
  );
}

function ProductMobileCard({
  product,
  onEdit,
}: {
  product: Product;
  onEdit: (product: Product) => void;
}) {
  return (
    <div className={mobileCardClassName}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{product.sku}</span>
        <ProductStatusBadge status={product.status} />
      </div>
      <p className="mt-3 font-semibold text-gray-800 dark:text-white/90">{product.name}</p>
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-lg font-bold text-gray-800 dark:text-white/90">
          {formatCurrencyBRL(product.price)}
        </span>
      </div>
      <Button
        size="sm"
        variant="outline"
        className="mt-3 min-h-[44px] w-full"
        onClick={() => onEdit(product)}
      >
        Editar
      </Button>
    </div>
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

  if (loading) {
    return (
      <>
        <div className="hidden overflow-x-auto md:block">
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
            <TableBody>
              <SkeletonTableRows />
            </TableBody>
          </Table>
        </div>
        <SkeletonMobileCards />
      </>
    );
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
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
            {products.map((product) => (
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
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="block md:hidden">
        {products.map((product) => (
          <ProductMobileCard key={product.id} product={product} onEdit={onEdit} />
        ))}
      </div>
    </>
  );
}
