export const datasetSummary = {
  sessions: 12_330,
  purchases: 1_908,
  nonPurchases: 10_422,
  conversionRate: 0.15474452554744525,
  duplicateRows: 125,
  columns: 18,
} as const;

export const monthlyConversion = [
  { label: "Feb", value: 0.016304347826086956 },
  { label: "Mar", value: 0.10068169900367069 },
  { label: "May", value: 0.10850178359096314 },
  { label: "Jun", value: 0.10069444444444445 },
  { label: "Jul", value: 0.1527777777777778 },
  { label: "Ago", value: 0.17551963048498845 },
  { label: "Sep", value: 0.19196428571428573 },
  { label: "Oct", value: 0.20947176684881602 },
  { label: "Nov", value: 0.25350233488992663 },
  { label: "Dic", value: 0.1250723798494499 },
] as const;
export const visitorConversion = [
  { label: "Nuevo", value: 0.24911452184179456 },
  { label: "Otro", value: 0.18823529411764706 },
  { label: "Recurrente", value: 0.1393232868922377 },
] as const;

export const trafficConversion = [
  { label: "1", value: 0.10689514483884129 },
  { label: "2", value: 0.21645796064400716 },
  { label: "3", value: 0.08771929824561403 },
  { label: "4", value: 0.15434985968194576 },
  { label: "5", value: 0.2153846153846154 },
  { label: "6", value: 0.11936936936936937 },
  { label: "7", value: 0.3 },
  { label: "8", value: 0.27696793002915454 },
  { label: "9", value: 0.09523809523809523 },
  { label: "10", value: 0.2 },
  { label: "11", value: 0.1902834008097166 },
  { label: "12", value: 0 },
  { label: "13", value: 0.058265582655826556 },
  { label: "14", value: 0.15384615384615385 },
  { label: "15", value: 0 },
  { label: "16", value: 0.3333333333333333 },
  { label: "17", value: 0 },
  { label: "18", value: 0 },
  { label: "19", value: 0.058823529411764705 },
  { label: "20", value: 0.25252525252525254 },
] as const;

export const signalComparison = [
  { label: "PageValues", purchase: 27.264518194696016, noPurchase: 1.9759977673701787 },
  { label: "Bounce rate", purchase: 0.005117152640461216, noPurchase: 0.025317232197850703 },
  { label: "Exit rate", purchase: 0.019555168256813416, noPurchase: 0.04737827052648244 },
] as const;

export const experimentSummary = {
  candidates: 66,
  failedCandidates: 0,
  folds: 5,
  auditRows: 2_466,
  auditGroups: 2_439,
  instance: "t3.medium",
  region: "us-east-1",
  selectionMetric: "PR-AUC CV",
  thresholdMetric: "F1 OOF",
} as const;

export const topCandidates = [
  {
    rank: 1,
    family: "CatBoost",
    configuration: "depth 8 · lr 0.03 · l2 5",
    featureSet: "engineered + PageValues",
    prAuc: 0.7562165275630438,
    f1: 0.6857658097715846,
    durationSeconds: 56.83419422700001,
  },
  {
    rank: 2,
    family: "XGBoost",
    configuration: "depth 5 · lr 0.03 · child 3",
    featureSet: "engineered + PageValues",
    prAuc: 0.7557886773393103,
    f1: 0.6810600422154334,
    durationSeconds: 11.772245872000099,
  },
  {
    rank: 3,
    family: "CatBoost",
    configuration: "depth 6 · lr 0.03 · l2 3",
    featureSet: "engineered + PageValues",
    prAuc: 0.7537955593223669,
    f1: 0.6785216269584236,
    durationSeconds: 28.417911850999985,
  },
  {
    rank: 4,
    family: "CatBoost",
    configuration: "depth 4 · lr 0.06 · l2 7",
    featureSet: "engineered + PageValues",
    prAuc: 0.7530118428977637,
    f1: 0.6702044846980886,
    durationSeconds: 18.18017580100002,
  },
  {
    rank: 5,
    family: "CatBoost",
    configuration: "depth 4 · lr 0.03 · l2 3",
    featureSet: "engineered + PageValues",
    prAuc: 0.7526568276780355,
    f1: 0.6698298083124159,
    durationSeconds: 18.82720137199999,
  },
] as const;
