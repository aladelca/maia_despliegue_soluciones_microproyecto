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

export type SessionFeatures = z.infer<typeof sessionFeaturesSchema>;
export type PredictionResponse = z.infer<typeof predictionResponseSchema>;
