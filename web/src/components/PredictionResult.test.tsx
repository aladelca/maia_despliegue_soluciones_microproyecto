import { render, screen } from "@testing-library/react";

import { PredictionResult } from "./PredictionResult";

it("renders probability, threshold, model, and baseline comparison", () => {
  render(
    <PredictionResult
      baselineRate={0.22}
      result={{
        will_purchase: true,
        purchase_probability: 0.73,
        threshold: 0.6,
        model_version: "abc123",
      }}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent("Compra probable");
  expect(screen.getByText("73,0%")).toBeInTheDocument();
  expect(screen.getByText(/Umbral 60,0%/)).toBeInTheDocument();
  expect(screen.getByText(/Tasa base 22.0%/)).toBeInTheDocument();
  expect(screen.getByText(/abc123/)).toBeInTheDocument();
});
