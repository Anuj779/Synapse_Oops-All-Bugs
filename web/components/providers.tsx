"use client";

import { FluentProvider, webLightTheme, type Theme } from "@fluentui/react-components";
import type { ReactNode } from "react";

const theme: Theme = {
  ...webLightTheme,
  colorBrandBackground: "#c9511a",
  colorBrandBackgroundHover: "#a53f12",
  colorBrandBackgroundPressed: "#84330e",
  colorBrandForeground1: "#a53f12",
  colorBrandStroke1: "#c9511a",
  colorNeutralBackground1: "#f7f6f3",
  colorNeutralBackground2: "#ffffff",
  colorNeutralForeground1: "#18211d",
  borderRadiusMedium: "10px",
  borderRadiusLarge: "16px",
};

export function Providers({ children }: { children: ReactNode }) {
  return <FluentProvider theme={theme}>{children}</FluentProvider>;
}
