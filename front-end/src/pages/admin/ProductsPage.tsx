import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import OnboardingSpotlight from "../../components/onboarding/OnboardingSpotlight";
import ProductEditModal from "../../components/products/ProductEditModal";
import ProductImportConfirmModal from "../../components/products/ProductImportConfirmModal";
import ProductsSearchPanel from "../../components/products/ProductsSearchPanel";
import ProductsTable from "../../components/products/ProductsTable";
import Button from "../../components/ui/button/Button";
import {
  buildProductsQueryParams,
  confirmProductsImport,
  downloadProductsTemplate,
  fetchProducts,
  uploadProductsPreview,
} from "../../features/products/api";
import {
  emptyProductsSearchFilters,
  hasActiveProductsFilters,
  type ProductsSearchFilters,
} from "../../features/products/searchTypes";
import type { ImportPreviewResponse, Product } from "../../features/products/types";
import { PRODUCT_IMPORT_SPOTLIGHT_COPY } from "../../features/onboarding/productImportSpotlightCopy";
import { useOnboardingStatus } from "../../features/onboarding/useOnboardingStatus";
import { getAxiosErrorMessage } from "../../utils/apiError";

type Props = {
  embedded?: boolean;
};

type SpotlightStep = "DOWNLOAD" | "IMPORT";

export default function ProductsPage({ embedded = false }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [appliedFilters, setAppliedFilters] = useState<ProductsSearchFilters>(
    emptyProductsSearchFilters(),
  );
  const [analyzing, setAnalyzing] = useState(false);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreviewResponse | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [spotlightStep, setSpotlightStep] = useState<SpotlightStep | null>(null);
  const spotlightWasEligibleRef = useRef(false);
  const { status: onboarding, loading: onboardingLoading } = useOnboardingStatus();

  const loadProducts = useCallback(async (filters: ProductsSearchFilters) => {
    setLoading(true);
    try {
      const params = buildProductsQueryParams(filters);
      const data = await fetchProducts(params);
      setProducts(data);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar produtos." }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts(appliedFilters);
  }, [appliedFilters, loadProducts]);

  const filtersActive = hasActiveProductsFilters(appliedFilters);

  const spotlightEligible =
    !loading &&
    !onboardingLoading &&
    onboarding !== null &&
    !onboarding.step_product_created &&
    products.length === 0 &&
    !filtersActive;

  useEffect(() => {
    if (spotlightEligible && !spotlightWasEligibleRef.current) {
      setSpotlightStep("DOWNLOAD");
    }
    if (!spotlightEligible) {
      setSpotlightStep(null);
      spotlightWasEligibleRef.current = false;
    } else {
      spotlightWasEligibleRef.current = true;
    }
  }, [spotlightEligible]);

  async function handleDownloadTemplate() {
    await downloadProductsTemplate();
    toast.success("Modelo baixado.");
  }

  async function handleDownloadTemplateSpotlight() {
    try {
      await handleDownloadTemplate();
      setSpotlightStep("IMPORT");
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao baixar modelo." }));
    }
  }

  function handleImportClick() {
    fileInputRef.current?.click();
  }

  function handleImportClickSpotlight() {
    setSpotlightStep(null);
    handleImportClick();
  }

  function resetFileInput() {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function closeImportModal() {
    setImportModalOpen(false);
    setImportPreview(null);
    resetFileInput();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSpotlightStep(null);

    const file = e.target.files?.[0];
    if (!file) return;

    setAnalyzing(true);
    try {
      const preview = await uploadProductsPreview(file);
      setImportPreview(preview);
      setImportModalOpen(true);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao analisar planilha." }));
      resetFileInput();
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleConfirmImport() {
    if (!importPreview?.import_token) return;
    setConfirmBusy(true);
    try {
      const result = await confirmProductsImport(importPreview.import_token);
      toast.success(
        `Importação concluída: ${result.created} novo(s), ${result.updated} atualizado(s).`,
      );
      closeImportModal();
      await loadProducts(appliedFilters);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao confirmar importação." }));
    } finally {
      setConfirmBusy(false);
    }
  }

  function handleProductSaved(updated: Product) {
    setProducts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }

  const listBusy = loading || analyzing;

  const downloadButton = (
    <Button
      variant="outline"
      onClick={() => void handleDownloadTemplate()}
      disabled={analyzing}
    >
      Baixar Modelo de Planilha
    </Button>
  );

  const importButton = (
    <Button onClick={handleImportClick} disabled={analyzing}>
      {analyzing ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          Analisando planilha…
        </span>
      ) : (
        "Importar Planilha"
      )}
    </Button>
  );

  const panelBody = (
    <>
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-end">
          <div className="flex flex-wrap gap-2">
            {spotlightStep === "DOWNLOAD" ? (
              <OnboardingSpotlight message={PRODUCT_IMPORT_SPOTLIGHT_COPY.download}>
                <Button
                  variant="outline"
                  onClick={() => void handleDownloadTemplateSpotlight()}
                  disabled={analyzing}
                >
                  Baixar Modelo de Planilha
                </Button>
              </OnboardingSpotlight>
            ) : (
              downloadButton
            )}

            {spotlightStep === "IMPORT" ? (
              <OnboardingSpotlight message={PRODUCT_IMPORT_SPOTLIGHT_COPY.import}>
                <Button onClick={handleImportClickSpotlight} disabled={analyzing}>
                  {analyzing ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Analisando planilha…
                    </span>
                  ) : (
                    "Importar Planilha"
                  )}
                </Button>
              </OnboardingSpotlight>
            ) : (
              importButton
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.csv"
              className="hidden"
              onChange={(e) => void handleFileChange(e)}
            />
          </div>
        </div>

        <ProductsSearchPanel
          busy={listBusy}
          resultCount={loading ? undefined : products.length}
          onSearch={setAppliedFilters}
          onClear={() => setAppliedFilters(emptyProductsSearchFilters())}
        />

        <ProductsTable
          products={products}
          loading={loading}
          filtersActive={filtersActive}
          onEdit={(product) => setEditingProduct(product)}
        />
    </>
  );

  return (
    <>
      {!embedded ? (
        <AdminPageLayout
          pageTitle="Produtos"
          metaDescription="Gerenciamento de produtos e estoque"
          description="Importe planilhas e gerencie o catálogo do mercado."
        >
          {panelBody}
        </AdminPageLayout>
      ) : (
        panelBody
      )}

      <ProductEditModal
        product={editingProduct}
        isOpen={Boolean(editingProduct)}
        onClose={() => setEditingProduct(null)}
        onSaved={handleProductSaved}
      />

      <ProductImportConfirmModal
        isOpen={importModalOpen}
        preview={importPreview}
        busy={confirmBusy}
        onClose={closeImportModal}
        onConfirm={() => void handleConfirmImport()}
      />
    </>
  );
}
