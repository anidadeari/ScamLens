import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatePanel, type StateTone } from "@/components/ui";

describe("future integration states", () => {
  it.each<StateTone>(["empty", "loading", "success", "caution", "error", "unavailable"])(
    "renders a named %s state without invented results",
    (tone) => {
      render(<StatePanel tone={tone} title={`${tone} state`} description="Plain-language supporting detail" />);
      expect(screen.getByText(`${tone} state`)).toBeInTheDocument();
      expect(screen.getByText("Plain-language supporting detail")).toBeInTheDocument();
    },
  );
});
