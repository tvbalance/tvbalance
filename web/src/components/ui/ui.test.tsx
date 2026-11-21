import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { applyTheme, setTheme } from "../../theme";
import { Dialog } from "./dialog";
import { Field, Input, Switch } from "./field";
import { Tabs } from "./tabs";
import { ToastProvider, useToast } from "./toast";

afterEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
});

describe("Field", () => {
  it("ties the label and the error to the control", () => {
    render(<Field label="Name" error="Required">{(props) => <Input {...props} />}</Field>);
    const input = screen.getByLabelText("Name");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Required");
    expect(screen.getByRole("alert")).toHaveTextContent("Required");
  });

  it("describes the control with the hint when there is no error", () => {
    render(<Field label="PIN" hint="4 to 8 digits">{(props) => <Input {...props} />}</Field>);
    expect(screen.getByLabelText("PIN")).toHaveAccessibleDescription("4 to 8 digits");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("Switch", () => {
  it("toggles and exposes its state", async () => {
    function Harness() {
      const [on, setOn] = useState(false);
      return <Switch checked={on} onChange={setOn} label="Enabled" />;
    }
    render(<Harness />);
    const toggle = screen.getByRole("switch", { name: "Enabled" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-checked", "true");
  });
});

describe("Tabs", () => {
  it("shows one panel and moves with the arrow keys", async () => {
    render(
      <Tabs
        label="Sections"
        tabs={[
          { id: "a", label: "A", content: <p>panel a</p> },
          { id: "b", label: "B", content: <p>panel b</p> },
        ]}
      />,
    );
    expect(screen.getByText("panel a")).toBeVisible();
    expect(screen.queryByText("panel b")).toBeNull();
    screen.getByRole("tab", { name: "A" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "B" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "B" })).toHaveFocus();
    expect(screen.getByText("panel b")).toBeVisible();
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "A" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("Dialog", () => {
  it("is named, described and closes with Escape", async () => {
    function Harness() {
      const [open, setOpen] = useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen} title="Remove TV" description="This cannot be undone">
          <button>Confirm</button>
        </Dialog>
      );
    }
    render(<Harness />);
    const dialog = screen.getByRole("dialog", { name: "Remove TV" });
    expect(dialog).toHaveAccessibleDescription("This cannot be undone");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("Toast", () => {
  it("announces a message", async () => {
    function Harness() {
      const toast = useToast();
      return <button onClick={() => toast("Saved")}>save</button>;
    }
    render(
      <ToastProvider>
        <Harness />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByText("save"));
    expect(screen.getByRole("status")).toHaveTextContent("Saved");
  });
});

describe("theme", () => {
  it("applies and remembers the choice, and follows the system again on request", () => {
    setTheme("dark");
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("tvbalance.theme")).toBe("dark");
    applyTheme();
    expect(document.documentElement).toHaveClass("dark");
    setTheme("light");
    expect(document.documentElement).not.toHaveClass("dark");
    setTheme("system");
    expect(localStorage.getItem("tvbalance.theme")).toBeNull();
  });
});
