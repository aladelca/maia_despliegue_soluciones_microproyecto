import type { Metadata } from "next";

import "./styles.css";

export const metadata: Metadata = {
  title: "Predicción de intención de compra",
  description: "Prototipo académico para estimar conversión de sesiones online.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
