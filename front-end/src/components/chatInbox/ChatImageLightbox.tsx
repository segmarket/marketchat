import { useEffect, useState, type MouseEvent } from "react";
import { Download, Loader2, X } from "lucide-react";
import { toast } from "sonner";

type Props = {
  src: string;
  onClose: () => void;
};

function filenameFromSrc(src: string, fallback = "anexo-chat.jpg"): string {
  try {
    const path = new URL(src, window.location.origin).pathname;
    const last = path.split("/").filter(Boolean).pop();
    if (last && /\.[a-z0-9]+$/i.test(last)) return decodeURIComponent(last);
  } catch {
    // ignore invalid URL
  }
  return fallback;
}

async function downloadImage(src: string, filename: string): Promise<void> {
  const response = await fetch(src);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export default function ChatImageLightbox({ src, onClose }: Props) {
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [onClose]);

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      await downloadImage(src, filenameFromSrc(src));
    } catch {
      toast.error("Não foi possível baixar a imagem.");
    } finally {
      setDownloading(false);
    }
  };

  const stopPropagation = (event: MouseEvent<HTMLElement>) => {
    event.stopPropagation();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Imagem ampliada"
      className="fixed inset-0 z-[100000] flex items-center justify-center p-4"
    >
      <button
        type="button"
        aria-label="Fechar visualização"
        className="absolute inset-0 bg-black/90"
        onClick={onClose}
      />

      <div className="absolute right-4 top-4 z-10 flex items-center gap-2">
        <button
          type="button"
          aria-label="Baixar imagem"
          disabled={downloading}
          onClick={(event) => {
            stopPropagation(event);
            void handleDownload();
          }}
          className="rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20 disabled:opacity-60"
        >
          {downloading ? (
            <Loader2 className="size-6 animate-spin" aria-hidden />
          ) : (
            <Download className="size-6" aria-hidden />
          )}
        </button>
        <button
          type="button"
          aria-label="Fechar"
          onClick={onClose}
          className="rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
        >
          <X className="size-6" aria-hidden />
        </button>
      </div>

      <img
        src={src}
        alt="Anexo ampliado"
        className="relative z-10 max-h-[90vh] max-w-[95vw] object-contain"
        onClick={stopPropagation}
      />
    </div>
  );
}
