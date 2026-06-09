import { api } from "../../services/api";

export async function downloadTenantLgpdExport(): Promise<void> {
  const response = await api.get("/api/lgpd/export/", {
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "marketchat-lgpd-export.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function anonymizeResidentByPhone(phone: string): Promise<{
  resident_id: number;
  is_anonymized: boolean;
  message: string;
}> {
  const { data } = await api.post("/api/lgpd/residents/anonymize/", { phone });
  return data;
}
