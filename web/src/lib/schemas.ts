import { z } from "zod";

const nonNegativeInteger = z.coerce.number().int().nonnegative();
const nonNegativeNumber = z.coerce.number().nonnegative().finite();
const rate = z.coerce.number().min(0).max(1).finite();
const positiveCategory = z.coerce.number().int().positive();

export const sessionFeaturesSchema = z
  .object({
    Administrative: nonNegativeInteger,
    Administrative_Duration: nonNegativeNumber,
    Informational: nonNegativeInteger,
    Informational_Duration: nonNegativeNumber,
    ProductRelated: nonNegativeInteger,
    ProductRelated_Duration: nonNegativeNumber,
    BounceRates: rate,
    ExitRates: rate,
    PageValues: nonNegativeNumber,
    SpecialDay: rate,
    Month: z.enum(["Feb", "Mar", "May", "June", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]),
    OperatingSystems: positiveCategory,
    Browser: positiveCategory,
    Region: positiveCategory,
    TrafficType: positiveCategory,
    VisitorType: z.enum(["New_Visitor", "Returning_Visitor", "Other"]),
    Weekend: z.boolean(),
  })
  .strict();

export const predictionResponseSchema = z.object({
  will_purchase: z.boolean(),
  purchase_probability: z.number().min(0).max(1),
  threshold: z.number().min(0).max(1),
  model_version: z.string().min(1),
});

export const modelMetadataSchema = z.object({
  model_version: z.string().min(1),
  feature_names: z.array(z.string()),
  threshold: z.number().min(0).max(1),
  champion: z.string().nullable().optional(),
  mlflow_run_id: z.string().nullable().optional(),
  mlflow_experiment: z.string().nullable().optional(),
  feature_set: z.string().nullable().optional(),
  include_page_values: z.boolean().nullable().optional(),
  baseline_rate: z.number().min(0).max(1).nullable().optional(),
  data_version: z.string().nullable().optional(),
  validation_metrics: z.record(z.string(), z.unknown()),
  test_metrics: z.record(z.string(), z.unknown()),
});

export type SessionFeatures = z.infer<typeof sessionFeaturesSchema>;
export type PredictionResponse = z.infer<typeof predictionResponseSchema>;
export type ModelMetadata = z.infer<typeof modelMetadataSchema>;
