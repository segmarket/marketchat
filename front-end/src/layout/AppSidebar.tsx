import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  LayoutDashboard,
  MessagesSquare,
  Package,
  Settings,
  ShoppingBag,
  Users,
} from "lucide-react";
import { Link, useLocation } from "react-router";
import { HorizontaLDots } from "../icons";
import { useSidebar } from "../context/SidebarContext";

type NavSubItem = {
  name: string;
  to: string;
  adminOnly?: boolean;
  integrationsOnly?: boolean;
};

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  matchPrefix?: string;
  subItems?: NavSubItem[];
};

const mainNavItems: NavItem[] = [
  {
    name: "Dashboard",
    path: "/admin",
    icon: <LayoutDashboard className="size-5" strokeWidth={2} />,
  },
  {
    name: "Histórico de Chamados",
    path: "/admin/chat-logs",
    icon: <MessagesSquare className="size-5" strokeWidth={2} />,
  },
  {
    name: "Painel de Vendas",
    path: "/admin/sales",
    icon: <ShoppingBag className="size-5" strokeWidth={2} />,
  },
  {
    name: "Moradores",
    path: "/admin/residents",
    icon: <Users className="size-5" strokeWidth={2} />,
  },
  {
    name: "Produtos",
    path: "/admin/products",
    icon: <Package className="size-5" strokeWidth={2} />,
  },
  {
    name: "Configurações",
    icon: <Settings className="size-5" strokeWidth={2} />,
    matchPrefix: "/admin/settings",
    subItems: [
      { name: "Mercados", to: "/admin/settings?section=markets" },
      { name: "Integrações", to: "/admin/settings?section=integrations", integrationsOnly: true },
      { name: "Minha Conta", to: "/admin/settings" },
      { name: "Plano e pagamento", to: "/admin/settings?tab=plan", adminOnly: true },
      { name: "Histórico de Faturas", to: "/admin/settings?tab=history", adminOnly: true },
    ],
  },
];

function parseNavTarget(to: string): { pathname: string; search: URLSearchParams } {
  const [pathname, search = ""] = to.split("?");
  return { pathname, search: new URLSearchParams(search) };
}

function isSubItemActive(
  pathname: string,
  currentSearch: URLSearchParams,
  subItem: NavSubItem,
): boolean {
  const { pathname: targetPath, search: targetSearch } = parseNavTarget(subItem.to);
  if (pathname !== targetPath) return false;

  if (subItem.to === "/admin/settings") {
    const tab = currentSearch.get("tab");
    const section = currentSearch.get("section");
    return !tab && !section;
  }

  for (const [key, value] of targetSearch.entries()) {
    if (currentSearch.get(key) !== value) return false;
  }
  return true;
}

function isNavItemActive(pathname: string, item: NavItem): boolean {
  if (item.path === "/admin") {
    return pathname === "/admin" || pathname === "/admin/";
  }
  if (item.subItems?.length) {
    return pathname === "/admin/settings" || pathname.startsWith("/admin/settings/");
  }
  if (item.path) {
    return pathname === item.path || pathname.startsWith(`${item.path}/`);
  }
  return false;
}

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const location = useLocation();
  const currentSearch = new URLSearchParams(location.search);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [subMenuHeight, setSubMenuHeight] = useState(0);
  const subMenuRef = useRef<HTMLDivElement | null>(null);

  const showExpanded = isExpanded || isHovered || isMobileOpen;

  const isItemActive = useCallback(
    (item: NavItem) => isNavItemActive(location.pathname, item),
    [location.pathname],
  );

  useEffect(() => {
    if (location.pathname.startsWith("/admin/settings")) {
      setSettingsOpen(true);
    }
  }, [location.pathname]);

  useEffect(() => {
    if (settingsOpen && subMenuRef.current) {
      setSubMenuHeight(subMenuRef.current.scrollHeight);
    }
  }, [settingsOpen, showExpanded]);

  const settingsSubItems =
    mainNavItems.find((item) => item.name === "Configurações")?.subItems ?? [];

  return (
    <aside
      className={`fixed top-0 left-0 z-50 mt-16 flex h-screen flex-col border-r border-gray-200 bg-white px-5 text-gray-900 transition-all duration-300 ease-in-out dark:border-gray-800 dark:bg-gray-900 lg:mt-0 ${
        showExpanded ? "w-[290px]" : isHovered ? "w-[290px]" : "w-[90px]"
      } ${isMobileOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`flex py-8 ${!showExpanded ? "lg:justify-center" : "justify-start"}`}
      >
        <Link to="/admin">
          <img
            src="/images/brand/logo_marketchat.png"
            alt="MarketChat"
            className={
              showExpanded
                ? "h-9 w-auto max-h-9 object-contain object-left"
                : "h-8 w-auto max-h-8 object-contain object-left"
            }
            decoding="async"
          />
        </Link>
      </div>

      <nav className="no-scrollbar mb-6 flex flex-1 flex-col overflow-y-auto duration-300 ease-linear">
        <h2
          className={`mb-4 flex text-xs leading-[20px] font-medium uppercase text-gray-400 ${
            !showExpanded ? "lg:justify-center" : "justify-start"
          }`}
        >
          {showExpanded ? "Menu" : <HorizontaLDots className="size-6" />}
        </h2>
        <ul className="flex flex-col gap-2">
          {mainNavItems.map((item) => {
            const active = isItemActive(item);
            const hasSub = Boolean(item.subItems?.length);

            if (hasSub) {
              return (
                <li key={item.name}>
                  <button
                    type="button"
                    onClick={() => setSettingsOpen((open) => !open)}
                    className={`menu-item group w-full cursor-pointer ${
                      active ? "menu-item-active" : "menu-item-inactive"
                    } ${!showExpanded ? "lg:justify-center" : "lg:justify-start"}`}
                  >
                    <span
                      className={`menu-item-icon-size ${
                        active ? "menu-item-icon-active" : "menu-item-icon-inactive"
                      }`}
                    >
                      {item.icon}
                    </span>
                    {showExpanded && (
                      <>
                        <span className="menu-item-text">{item.name}</span>
                        <ChevronDown
                          className={`ml-auto size-5 transition-transform duration-200 ${
                            settingsOpen ? "rotate-180 text-brand-500" : "text-gray-400"
                          }`}
                        />
                      </>
                    )}
                  </button>
                  {showExpanded && (
                    <div
                      ref={subMenuRef}
                      className="overflow-hidden transition-all duration-300"
                      style={{ height: settingsOpen ? `${subMenuHeight}px` : "0px" }}
                    >
                      <ul className="mt-2 ml-9 space-y-1">
                        {settingsSubItems.map((sub) => {
                          const subActive = isSubItemActive(
                            location.pathname,
                            currentSearch,
                            sub,
                          );
                          return (
                            <li key={sub.to}>
                              <Link
                                to={sub.to}
                                className={`menu-dropdown-item block ${
                                  subActive
                                    ? "menu-dropdown-item-active"
                                    : "menu-dropdown-item-inactive"
                                }`}
                              >
                                {sub.name}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </li>
              );
            }

            return (
              <li key={item.path}>
                <Link
                  to={item.path!}
                  className={`menu-item group ${
                    active ? "menu-item-active" : "menu-item-inactive"
                  } ${!showExpanded ? "lg:justify-center" : "lg:justify-start"}`}
                >
                  <span
                    className={`menu-item-icon-size ${
                      active ? "menu-item-icon-active" : "menu-item-icon-inactive"
                    }`}
                  >
                    {item.icon}
                  </span>
                  {showExpanded && <span className="menu-item-text">{item.name}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};

export default AppSidebar;
