import { useState } from "react";
import { Dropdown } from "../ui/dropdown/Dropdown";
import { DropdownItem } from "../ui/dropdown/DropdownItem";
import { useNotifications } from "../../context/NotificationsContext";
import {
  formatRelativeTime,
  severityStyles,
  unreadBadgeLabel,
} from "../../features/notifications/format";
import type { NotificationItem } from "../../features/notifications/types";

function NotificationRow({
  item,
  onSelect,
}: {
  item: NotificationItem;
  onSelect: (id: number) => void;
}) {
  const styles = severityStyles(item.severity);

  return (
    <li>
      <DropdownItem
        onItemClick={() => onSelect(item.id)}
        className={`flex gap-3 rounded-lg border-l-[3px] p-3 px-4 py-3 hover:bg-gray-100 dark:hover:bg-white/5 ${styles.border}`}
      >
        <span
          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${styles.dot}`}
          aria-hidden
        />
        <span className="block min-w-0 flex-1">
          <span className={`mb-1 block text-theme-sm font-semibold ${styles.title}`}>
            {item.title}
          </span>
          <span className="mb-1.5 line-clamp-2 block text-theme-sm text-gray-600 dark:text-gray-400">
            {item.message}
          </span>
          <span className="flex flex-wrap items-center gap-2 text-theme-xs text-gray-500 dark:text-gray-400">
            {item.market_name ? <span>{item.market_name}</span> : null}
            {item.market_name ? (
              <span className="h-1 w-1 rounded-full bg-gray-400" aria-hidden />
            ) : null}
            <span>{formatRelativeTime(item.created_at)}</span>
          </span>
        </span>
      </DropdownItem>
    </li>
  );
}

export default function NotificationDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const { items, unreadCount, loading, markRead, markAllRead } = useNotifications();

  const badge = unreadBadgeLabel(unreadCount);

  function toggleDropdown() {
    setIsOpen((open) => !open);
  }

  function closeDropdown() {
    setIsOpen(false);
  }

  async function handleSelect(id: number) {
    await markRead(id);
  }

  async function handleMarkAllRead() {
    await markAllRead();
    closeDropdown();
  }

  return (
    <div className="relative">
      <button
        type="button"
        className="relative flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 transition-colors dropdown-toggle hover:bg-gray-100 hover:text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
        onClick={toggleDropdown}
        aria-label="Notificações"
      >
        {badge ? (
          <span className="absolute -right-0.5 -top-0.5 z-10 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-error-500 px-1 text-[10px] font-semibold text-white">
            {badge}
          </span>
        ) : null}
        <svg
          className="fill-current"
          width="20"
          height="20"
          viewBox="0 0 20 20"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M10.75 2.29248C10.75 1.87827 10.4143 1.54248 10 1.54248C9.58583 1.54248 9.25004 1.87827 9.25004 2.29248V2.83613C6.08266 3.20733 3.62504 5.9004 3.62504 9.16748V14.4591H3.33337C2.91916 14.4591 2.58337 14.7949 2.58337 15.2091C2.58337 15.6234 2.91916 15.9591 3.33337 15.9591H4.37504H15.625H16.6667C17.0809 15.9591 17.4167 15.6234 17.4167 15.2091C17.4167 14.7949 17.0809 14.4591 16.6667 14.4591H16.375V9.16748C16.375 5.9004 13.9174 3.20733 10.75 2.83613V2.29248ZM14.875 14.4591V9.16748C14.875 6.47509 12.6924 4.29248 10 4.29248C7.30765 4.29248 5.12504 6.47509 5.12504 9.16748V14.4591H14.875ZM8.00004 17.7085C8.00004 18.1228 8.33583 18.4585 8.75004 18.4585H11.25C11.6643 18.4585 12 18.1228 12 17.7085C12 17.2943 11.6643 16.9585 11.25 16.9585H8.75004C8.33583 16.9585 8.00004 17.2943 8.00004 17.7085Z"
            fill="currentColor"
          />
        </svg>
      </button>
      <Dropdown
        isOpen={isOpen}
        onClose={closeDropdown}
        className="absolute -right-[240px] mt-[17px] flex h-[480px] w-[350px] flex-col rounded-2xl border border-gray-200 bg-white p-3 shadow-theme-lg dark:border-gray-800 dark:bg-gray-dark sm:w-[361px] lg:right-0"
      >
        <div className="mb-3 flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-700">
          <h5 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
            Notificações
          </h5>
          <button
            type="button"
            onClick={toggleDropdown}
            className="text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="Fechar"
          >
            <svg
              className="fill-current"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M6.21967 7.28131C5.92678 6.98841 5.92678 6.51354 6.21967 6.22065C6.51256 5.92775 6.98744 5.92775 7.28033 6.22065L11.999 10.9393L16.7176 6.22078C17.0105 5.92789 17.4854 5.92788 17.7782 6.22078C18.0711 6.51367 18.0711 6.98855 17.7782 7.28144L13.0597 12L17.7782 16.7186C18.0711 17.0115 18.0711 17.4863 17.7782 17.7792C17.4854 18.0721 17.0105 18.0721 16.7176 17.7792L11.999 13.0607L7.28033 17.7794C6.98744 18.0722 6.51256 18.0722 6.21967 17.7794C5.92678 17.4865 5.92678 17.0116 6.21967 16.7187L10.9384 12L6.21967 7.28131Z"
                fill="currentColor"
              />
            </svg>
          </button>
        </div>

        <ul className="custom-scrollbar flex h-auto flex-1 flex-col overflow-y-auto">
          {loading && items.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
              Carregando alertas…
            </li>
          ) : items.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
              Nenhum alerta pendente
            </li>
          ) : (
            items.map((item) => (
              <NotificationRow key={item.id} item={item} onSelect={handleSelect} />
            ))
          )}
        </ul>

        {unreadCount > 0 ? (
          <button
            type="button"
            onClick={() => void handleMarkAllRead()}
            className="mt-3 block w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-center text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Marcar todas como lidas
          </button>
        ) : null}
      </Dropdown>
    </div>
  );
}
