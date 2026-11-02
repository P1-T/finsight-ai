import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "solid" | "outline" | "ghost";

export function Button({
  children,
  className = "",
  variant = "solid",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return <button className={`ui-button ui-button-${variant} ${className}`.trim()} {...props}>{children}</button>;
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`ui-input ${className}`.trim()} {...props} />;
}

export function Card({ children, className = "", ...props }: HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return <section className={`ui-card ${className}`.trim()} {...props}>{children}</section>;
}

export function Badge({ children, className = "", ...props }: HTMLAttributes<HTMLSpanElement> & { children: ReactNode }) {
  return <span className={`ui-badge ${className}`.trim()} {...props}>{children}</span>;
}

export function Table({ children, className = "", ...props }: HTMLAttributes<HTMLTableElement> & { children: ReactNode }) {
  return <table className={`ui-table ${className}`.trim()} {...props}>{children}</table>;
}

export function TableHead({ children, className = "", ...props }: HTMLAttributes<HTMLTableSectionElement> & { children: ReactNode }) {
  return <thead className={className} {...props}>{children}</thead>;
}

export function TableBody({ children, className = "", ...props }: HTMLAttributes<HTMLTableSectionElement> & { children: ReactNode }) {
  return <tbody className={className} {...props}>{children}</tbody>;
}

export function TableRow({ children, className = "", ...props }: HTMLAttributes<HTMLTableRowElement> & { children: ReactNode }) {
  return <tr className={className} {...props}>{children}</tr>;
}

export function TableCell({ children, className = "", as: Element = "td", ...props }: HTMLAttributes<HTMLTableCellElement> & { children: ReactNode; as?: "td" | "th" }) {
  return <Element className={className} {...props}>{children}</Element>;
}
