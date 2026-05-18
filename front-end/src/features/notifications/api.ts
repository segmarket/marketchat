import { api } from "../../services/api";
import type { NotificationItem, NotificationsLatestResponse } from "./types";

export async function fetchLatestNotifications(): Promise<NotificationsLatestResponse> {
  const { data } = await api.get<NotificationsLatestResponse>("/api/notifications/latest/");
  return data;
}

export async function markNotificationRead(id: number): Promise<NotificationItem> {
  const { data } = await api.post<NotificationItem>(`/api/notifications/${id}/read/`);
  return data;
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  const { data } = await api.post<{ marked_read: number }>("/api/notifications/read-all/");
  return data;
}
