/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useRef, useState } from "react";
import { observer } from "mobx-react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useOutsideClickDetector } from "@plane/hooks";

// A panel whose outside-click callback reads render state (`if (isOpen) close()`), like the top-bar search.
// `Wrapped` is rendered inside a mobx `observer`, as most of the app's components are.
function Panel() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setIsOpen(false), []);
  const handleOutsideClick = useCallback(() => {
    if (isOpen) close();
  }, [isOpen, close]);
  useOutsideClickDetector(ref, handleOutsideClick);

  return (
    <div>
      <div ref={ref}>
        <button type="button" onClick={() => setIsOpen(true)}>
          open
        </button>
        {isOpen && <div data-testid="panel">panel</div>}
      </div>
      <div data-testid="elsewhere">elsewhere</div>
    </div>
  );
}
const ObservedPanel = observer(Panel);

describe.each([
  ["a plain component", Panel],
  ["a mobx observer component", ObservedPanel],
])("useOutsideClickDetector in %s", (_name, Component) => {
  it("closes the panel on a press outside, using the latest state", () => {
    render(<Component />);
    fireEvent.click(screen.getByText("open"));
    expect(screen.queryByTestId("panel")).not.toBeNull();

    fireEvent.mouseDown(screen.getByTestId("elsewhere"));
    expect(screen.queryByTestId("panel")).toBeNull();
  });

  it("keeps the panel open on a press inside", () => {
    render(<Component />);
    fireEvent.click(screen.getByText("open"));

    fireEvent.mouseDown(screen.getByTestId("panel"));
    expect(screen.queryByTestId("panel")).not.toBeNull();
  });
});
