/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useLatestCallback } from "@plane/hooks";

const seen: string[] = [];

// Registers one document listener in an effect, like the calendar drop target and the peek dismissal do.
function Listener({ value }: { value: string }) {
  const onPress = useLatestCallback(() => seen.push(value));
  useEffect(() => {
    document.addEventListener("mousedown", onPress);
    return () => document.removeEventListener("mousedown", onPress);
  }, [onPress]);
  return <div>{value}</div>;
}
const ObservedListener = observer(Listener);

function WithState({ Component }: { Component: typeof Listener }) {
  const [value, setValue] = useState("first");
  return (
    <>
      <button type="button" onClick={() => setValue("second")}>
        change
      </button>
      <Component value={value} />
    </>
  );
}

describe.each([
  ["a plain component", Listener],
  ["a mobx observer component", ObservedListener],
])("useLatestCallback in %s", (_name, Component) => {
  beforeEach(() => {
    seen.length = 0;
  });

  it("calls the callback of the latest props", () => {
    const { rerender } = render(<Component value="first" />);
    rerender(<Component value="second" />);

    fireEvent.mouseDown(document.body);
    expect(seen).toEqual(["second"]);
  });

  it("calls the callback of the latest state, and only once", () => {
    render(<WithState Component={Component} />);
    fireEvent.click(screen.getByText("change"));

    fireEvent.mouseDown(document.body);
    expect(seen).toEqual(["second"]);
  });
});
