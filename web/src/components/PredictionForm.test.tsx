import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { PredictionResponse } from "../lib/schemas";
import { PredictionForm } from "./PredictionForm";

it("submits the 17 typed features and renders the result", async () => {
  const user = userEvent.setup();
  const predict = vi.fn().mockResolvedValue({
    will_purchase: true,
    purchase_probability: 0.73,
    threshold: 0.6,
    model_version: "test-v1",
  });
  render(<PredictionForm predict={predict} />);

  await user.click(screen.getByRole("button", { name: "Predecir compra" }));

  expect(predict).toHaveBeenCalledOnce();
  expect(Object.keys(predict.mock.calls[0][0])).toHaveLength(17);
  expect(await screen.findByText("Compra probable")).toBeInTheDocument();
});

it("shows a recoverable error when the API fails", async () => {
  const user = userEvent.setup();
  const predict = vi.fn().mockRejectedValue(new Error("API unavailable"));
  render(<PredictionForm predict={predict} />);

  await user.click(screen.getByRole("button", { name: "Predecir compra" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible obtener la predicción",
  );
  expect(screen.getByRole("button", { name: "Predecir compra" })).toBeEnabled();
});

it("disables the form while the prediction is loading", async () => {
  const user = userEvent.setup();
  let resolvePrediction!: (value: PredictionResponse) => void;
  const prediction = new Promise<PredictionResponse>((resolve) => {
    resolvePrediction = resolve;
  });
  render(<PredictionForm predict={() => prediction} />);

  await user.click(screen.getByRole("button", { name: "Predecir compra" }));

  expect(screen.getByRole("button", { name: "Calculando…" })).toBeDisabled();
  resolvePrediction({
    will_purchase: false,
    purchase_probability: 0.2,
    threshold: 0.6,
    model_version: "test-v1",
  });
  expect(await screen.findByText("Compra poco probable")).toBeInTheDocument();
});

it("constrains categorical codes to positive integers", () => {
  render(<PredictionForm />);

  for (const label of [
    "Sistema operativo (código)",
    "Navegador (código)",
    "Región (código)",
    "Fuente de tráfico (código)",
  ]) {
    expect(screen.getByRole("spinbutton", { name: label })).toHaveAttribute("min", "1");
  }
});
