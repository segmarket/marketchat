import type { MouseEvent, ReactNode } from "react";
import { Link } from "react-router";

const baseTouch =
  "flex w-full items-center justify-center gap-2 rounded-xl px-6 py-4 text-center text-base font-semibold transition-all duration-300 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50";

export const linksPrimaryClass =
  `${baseTouch} animate-pulse bg-emerald-500 text-white shadow-lg shadow-emerald-500/25 hover:bg-emerald-600 hover:animate-none`;

export const linksSecondaryClass =
  `${baseTouch} border border-slate-700 bg-white/10 text-white hover:bg-white/20`;

type LinksPageButtonLinkProps = {
  to: string;
  children: ReactNode;
  className?: string;
};

export function LinksPageButtonLink({ to, children, className = linksSecondaryClass }: LinksPageButtonLinkProps) {
  return (
    <Link to={to} className={className}>
      {children}
    </Link>
  );
}

type LinksPageButtonExternalProps = {
  href: string;
  children: ReactNode;
  className?: string;
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void;
};

export function LinksPageButtonExternal({
  href,
  children,
  className = linksSecondaryClass,
  onClick,
}: LinksPageButtonExternalProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      onClick={onClick}
    >
      {children}
    </a>
  );
}
