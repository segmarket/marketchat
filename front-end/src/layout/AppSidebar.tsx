import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  LayoutDashboard,
  LifeBuoy,
  MessagesSquare,
  Package,
  Settings,
  ShoppingBag,
  Users,
  Wallet,
} from "lucide-react";
import { Link, useLocation } from "react-router";
import MarketchatLogo, { MARKETCHAT_LOGO_CLASS } from "../components/brand/MarketchatLogo";
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

const primaryNavItems: NavItem[] = [
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
    name: "Financeiro",
    path: "/admin/financial",
    icon: <Wallet className="size-5" strokeWidth={2} />,
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
];

const settingsNavItem: NavItem = {
  name: "Configurações",
  icon: <Settings className="size-5" strokeWidth={2} />,
  matchPrefix: "/admin/settings",
  subItems: [
    { name: "Mercados", to: "/admin/settings?section=markets" },
    { name: "Integrações", to: "/admin/settings?section=integrations", integrationsOnly: true },
    { name: "Minha Conta", to: "/admin/settings" },
    { name: "Privacidade", to: "/admin/settings?section=privacy", adminOnly: true },
    { name: "Plano e pagamento", to: "/admin/settings?tab=plan", adminOnly: true },
    { name: "Histórico de Faturas", to: "/admin/settings?tab=history", adminOnly: true },
  ],
};

const supportNavItem: NavItem = {
  name: "Meus Chamados",
  path: "/admin/support",
  icon: <LifeBuoy className="size-5" strokeWidth={2} />,
};

const secondaryNavItems: NavItem[] = [settingsNavItem, supportNavItem];

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
  const { isExpanded, isMobileOpen, isHovered, setIsHovered, closeMobileSidebar } = useSidebar();
  const location = useLocation();
  const currentSearch = new URLSearchParams(location.search);

  const handleNavClick = useCallback(() => {
    if (isMobileOpen) closeMobileSidebar();
  }, [isMobileOpen, closeMobileSidebar]);

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

  const settingsSubItems = settingsNavItem.subItems ?? [];

  const renderPrimaryLink = (item: NavItem) => {
    const active = isItemActive(item);
    return (
      <li key={item.name}>
        <Link
          to={item.path!}
          onClick={handleNavClick}
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
  };

  const renderSettingsSubLink = (sub: NavSubItem) => {
    const subActive = isSubItemActive(location.pathname, currentSearch, sub);
    return (
      <li key={sub.to}>
        <Link
          to={sub.to}
          onClick={handleNavClick}
          className={`menu-dropdown-item block ${
            subActive ? "menu-dropdown-item-active" : "menu-dropdown-item-inactive"
          }`}
        >
          {sub.name}
        </Link>
      </li>
    );
  };

  const renderDesktopSettingsAccordion = () => {
    const active = isItemActive(settingsNavItem);
    return (
      <li key={settingsNavItem.name}>
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
            {settingsNavItem.icon}
          </span>
          {showExpanded && (
            <>
              <span className="menu-item-text">{settingsNavItem.name}</span>
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
              {settingsSubItems.map(renderSettingsSubLink)}
            </ul>
          </div>
        )}
      </li>
    );
  };

  return (
    <aside
      className={`fixed top-0 left-0 z-50 mt-16 flex h-screen flex-col border-r border-gray-200 bg-white px-5 text-gray-900 transition-all duration-300 ease-in-out dark:border-gray-800 dark:bg-gray-900 lg:mt-0 ${
        showExpanded ? "w-[290px]" : isHovered ? "w-[290px]" : "w-[90px]"
      } ${isMobileOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`hidden py-8 lg:flex ${!showExpanded ? "lg:justify-center" : "justify-start"}`}
      >
        <Link to="/admin" onClick={handleNavClick}>
          <MarketchatLogo
            variant={showExpanded ? "theme" : "mascotTheme"}
            className={
              showExpanded
                ? MARKETCHAT_LOGO_CLASS
                : "h-10 w-10 max-h-10 object-contain object-center"
            }
          />
        </Link>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col overflow-hidden pt-4 lg:pt-0">
        {/* Mobile: lista única com Configurações expandida */}
        <div className="no-scrollbar flex-1 overflow-y-auto pb-4 lg:hidden">
          <h2 className="mb-4 flex text-xs font-medium uppercase leading-[20px] text-gray-400">
            Menu
          </h2>
          <ul className="flex flex-col gap-2">
            {primaryNavItems.map(renderPrimaryLink)}
            <li className="px-3 pt-3 text-xs font-medium uppercase text-gray-400">
              Configurações
            </li>
            {settingsSubItems.map(renderSettingsSubLink)}
            {renderPrimaryLink(supportNavItem)}
          </ul>
        </div>

        {/* Desktop: primários + secundários com accordion */}
        <div className="hidden min-h-0 flex-1 flex-col overflow-hidden lg:flex">
          <div className="no-scrollbar flex-1 overflow-y-auto pb-4 duration-300 ease-linear">
            <h2
              className={`mb-4 flex text-xs font-medium uppercase leading-[20px] text-gray-400 ${
                !showExpanded ? "lg:justify-center" : "justify-start"
              }`}
            >
              {showExpanded ? "Menu" : <HorizontaLDots className="size-6" />}
            </h2>
            <ul className="flex flex-col gap-2">{primaryNavItems.map(renderPrimaryLink)}</ul>
          </div>

          <div className="shrink-0 border-t border-gray-200 pt-4 pb-6 dark:border-gray-800">
            <ul className="flex flex-col gap-2">
              {renderDesktopSettingsAccordion()}
              {renderPrimaryLink(supportNavItem)}
            </ul>
          </div>
        </div>
      </nav>
    </aside>
  );
};

export default AppSidebar;
