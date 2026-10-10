// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NetworkError, RateLimitedError, UnauthorizedError } from "../../lib/api-client";
import { LoginForm } from "./login-form";

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Senha"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("login form fields", () => {
  it("renders labelled e-mail and password inputs with a submit button", () => {
    render(<LoginForm signIn={vi.fn()} onSignedIn={vi.fn()} />);

    expect(screen.getByLabelText("E-mail")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Senha")).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });
});

describe("login submission", () => {
  it("sends the trimmed e-mail and the password exactly as typed", async () => {
    const signIn = vi.fn(async () => undefined);
    render(<LoginForm signIn={signIn} onSignedIn={vi.fn()} />);

    fillAndSubmit("  admin@example.com  ", "s3cret pass");

    await waitFor(() => expect(signIn).toHaveBeenCalledWith({ email: "admin@example.com", password: "s3cret pass" }));
  });

  it("notifies the parent once the session is established", async () => {
    const onSignedIn = vi.fn();
    render(<LoginForm signIn={async () => undefined} onSignedIn={onSignedIn} />);

    fillAndSubmit("admin@example.com", "s3cret");

    await waitFor(() => expect(onSignedIn).toHaveBeenCalledTimes(1));
  });

  it("shows the server's rejection message and keeps the form usable", async () => {
    const onSignedIn = vi.fn();
    const signIn = vi.fn(async () => {
      throw new UnauthorizedError(401, "Credenciais inválidas");
    });
    render(<LoginForm signIn={signIn} onSignedIn={onSignedIn} />);

    fillAndSubmit("admin@example.com", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciais inválidas");
    expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("tells the administrator how long to wait when throttled", async () => {
    const signIn = vi.fn(async () => {
      throw new RateLimitedError("Muitas tentativas", 42);
    });
    render(<LoginForm signIn={signIn} onSignedIn={vi.fn()} />);

    fillAndSubmit("admin@example.com", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent("Aguarde 42 segundos");
  });

  it("reports a connection failure instead of a generic error", async () => {
    const signIn = vi.fn(async () => {
      throw new NetworkError(new TypeError("Failed to fetch"));
    });
    render(<LoginForm signIn={signIn} onSignedIn={vi.fn()} />);

    fillAndSubmit("admin@example.com", "s3cret");

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível conectar ao servidor");
  });

  it("disables the submit button while a request is in flight to prevent double submission", async () => {
    let finish: () => void = () => undefined;
    const signIn = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)));
    render(<LoginForm signIn={signIn} onSignedIn={vi.fn()} />);

    fillAndSubmit("admin@example.com", "s3cret");

    expect(await screen.findByRole("button", { name: "Entrando…" })).toBeDisabled();
    finish();
    await waitFor(() => expect(signIn).toHaveBeenCalledTimes(1));
  });
});
