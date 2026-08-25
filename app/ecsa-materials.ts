export type EcsaAnswer = "yes" | "no";
export type EcsaSubtest = "wholistic" | "analytic";
export type EcsaItemSet = "practice" | "original" | "extended";

export type EcsaTrial = {
  id: string;
  sequence: number;
  subtest: EcsaSubtest;
  practice: boolean;
  itemSet: EcsaItemSet;
  asset: string;
  correctAnswer: EcsaAnswer;
};

export const ECSA_VERSION = "e-csa-wa-peterson-approved-materials-v1";
export const ECSA_SCORING_VERSION = "median-correct-rt-h-over-a-v0.1";
export const ECSA_TRIALS: EcsaTrial[] = [
  { id: "wholistic_practice_01", sequence: 1, subtest: "wholistic", practice: true, itemSet: "practice", asset: "/ecsa/wholistic_practice_01.png", correctAnswer: "yes" },
  { id: "wholistic_practice_02", sequence: 2, subtest: "wholistic", practice: true, itemSet: "practice", asset: "/ecsa/wholistic_practice_02.png", correctAnswer: "no" },
  { id: "wholistic_001", sequence: 3, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_001.png", correctAnswer: "no" },
  { id: "wholistic_002", sequence: 4, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_002.png", correctAnswer: "yes" },
  { id: "wholistic_003", sequence: 5, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_003.png", correctAnswer: "no" },
  { id: "wholistic_004", sequence: 6, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_004.png", correctAnswer: "no" },
  { id: "wholistic_005", sequence: 7, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_005.png", correctAnswer: "yes" },
  { id: "wholistic_006", sequence: 8, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_006.png", correctAnswer: "yes" },
  { id: "wholistic_007", sequence: 9, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_007.png", correctAnswer: "no" },
  { id: "wholistic_008", sequence: 10, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_008.png", correctAnswer: "yes" },
  { id: "wholistic_009", sequence: 11, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_009.png", correctAnswer: "no" },
  { id: "wholistic_010", sequence: 12, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_010.png", correctAnswer: "yes" },
  { id: "wholistic_011", sequence: 13, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_011.png", correctAnswer: "no" },
  { id: "wholistic_012", sequence: 14, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_012.png", correctAnswer: "yes" },
  { id: "wholistic_013", sequence: 15, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_013.png", correctAnswer: "no" },
  { id: "wholistic_014", sequence: 16, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_014.png", correctAnswer: "yes" },
  { id: "wholistic_015", sequence: 17, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_015.png", correctAnswer: "yes" },
  { id: "wholistic_016", sequence: 18, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_016.png", correctAnswer: "no" },
  { id: "wholistic_017", sequence: 19, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_017.png", correctAnswer: "yes" },
  { id: "wholistic_018", sequence: 20, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_018.png", correctAnswer: "no" },
  { id: "wholistic_019", sequence: 21, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_019.png", correctAnswer: "yes" },
  { id: "wholistic_020", sequence: 22, subtest: "wholistic", practice: false, itemSet: "original", asset: "/ecsa/wholistic_020.png", correctAnswer: "no" },
  { id: "wholistic_021", sequence: 23, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_021.png", correctAnswer: "no" },
  { id: "wholistic_022", sequence: 24, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_022.png", correctAnswer: "no" },
  { id: "wholistic_023", sequence: 25, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_023.png", correctAnswer: "no" },
  { id: "wholistic_024", sequence: 26, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_024.png", correctAnswer: "no" },
  { id: "wholistic_025", sequence: 27, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_025.png", correctAnswer: "no" },
  { id: "wholistic_026", sequence: 28, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_026.png", correctAnswer: "no" },
  { id: "wholistic_027", sequence: 29, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_027.png", correctAnswer: "no" },
  { id: "wholistic_028", sequence: 30, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_028.png", correctAnswer: "no" },
  { id: "wholistic_029", sequence: 31, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_029.png", correctAnswer: "no" },
  { id: "wholistic_030", sequence: 32, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_030.png", correctAnswer: "no" },
  { id: "wholistic_031", sequence: 33, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_031.png", correctAnswer: "yes" },
  { id: "wholistic_032", sequence: 34, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_032.png", correctAnswer: "yes" },
  { id: "wholistic_033", sequence: 35, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_033.png", correctAnswer: "yes" },
  { id: "wholistic_034", sequence: 36, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_034.png", correctAnswer: "yes" },
  { id: "wholistic_035", sequence: 37, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_035.png", correctAnswer: "yes" },
  { id: "wholistic_036", sequence: 38, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_036.png", correctAnswer: "yes" },
  { id: "wholistic_037", sequence: 39, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_037.png", correctAnswer: "yes" },
  { id: "wholistic_038", sequence: 40, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_038.png", correctAnswer: "yes" },
  { id: "wholistic_039", sequence: 41, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_039.png", correctAnswer: "yes" },
  { id: "wholistic_040", sequence: 42, subtest: "wholistic", practice: false, itemSet: "extended", asset: "/ecsa/wholistic_040.png", correctAnswer: "yes" },
  { id: "analytic_practice_01", sequence: 43, subtest: "analytic", practice: true, itemSet: "practice", asset: "/ecsa/analytic_practice_01.png", correctAnswer: "yes" },
  { id: "analytic_practice_02", sequence: 44, subtest: "analytic", practice: true, itemSet: "practice", asset: "/ecsa/analytic_practice_02.png", correctAnswer: "no" },
  { id: "analytic_001", sequence: 45, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_001.png", correctAnswer: "yes" },
  { id: "analytic_002", sequence: 46, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_002.png", correctAnswer: "no" },
  { id: "analytic_003", sequence: 47, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_003.png", correctAnswer: "yes" },
  { id: "analytic_004", sequence: 48, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_004.png", correctAnswer: "yes" },
  { id: "analytic_005", sequence: 49, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_005.png", correctAnswer: "no" },
  { id: "analytic_006", sequence: 50, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_006.png", correctAnswer: "no" },
  { id: "analytic_007", sequence: 51, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_007.png", correctAnswer: "no" },
  { id: "analytic_008", sequence: 52, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_008.png", correctAnswer: "yes" },
  { id: "analytic_009", sequence: 53, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_009.png", correctAnswer: "no" },
  { id: "analytic_010", sequence: 54, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_010.png", correctAnswer: "yes" },
  { id: "analytic_011", sequence: 55, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_011.png", correctAnswer: "yes" },
  { id: "analytic_012", sequence: 56, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_012.png", correctAnswer: "yes" },
  { id: "analytic_013", sequence: 57, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_013.png", correctAnswer: "no" },
  { id: "analytic_014", sequence: 58, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_014.png", correctAnswer: "yes" },
  { id: "analytic_015", sequence: 59, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_015.png", correctAnswer: "no" },
  { id: "analytic_016", sequence: 60, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_016.png", correctAnswer: "no" },
  { id: "analytic_017", sequence: 61, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_017.png", correctAnswer: "no" },
  { id: "analytic_018", sequence: 62, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_018.png", correctAnswer: "yes" },
  { id: "analytic_019", sequence: 63, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_019.png", correctAnswer: "no" },
  { id: "analytic_020", sequence: 64, subtest: "analytic", practice: false, itemSet: "original", asset: "/ecsa/analytic_020.png", correctAnswer: "yes" },
  { id: "analytic_021", sequence: 65, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_021.png", correctAnswer: "yes" },
  { id: "analytic_022", sequence: 66, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_022.png", correctAnswer: "yes" },
  { id: "analytic_023", sequence: 67, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_023.png", correctAnswer: "yes" },
  { id: "analytic_024", sequence: 68, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_024.png", correctAnswer: "yes" },
  { id: "analytic_025", sequence: 69, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_025.png", correctAnswer: "yes" },
  { id: "analytic_026", sequence: 70, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_026.png", correctAnswer: "yes" },
  { id: "analytic_027", sequence: 71, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_027.png", correctAnswer: "yes" },
  { id: "analytic_028", sequence: 72, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_028.png", correctAnswer: "yes" },
  { id: "analytic_029", sequence: 73, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_029.png", correctAnswer: "yes" },
  { id: "analytic_030", sequence: 74, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_030.png", correctAnswer: "no" },
  { id: "analytic_031", sequence: 75, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_031.png", correctAnswer: "no" },
  { id: "analytic_032", sequence: 76, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_032.png", correctAnswer: "no" },
  { id: "analytic_033", sequence: 77, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_033.png", correctAnswer: "no" },
  { id: "analytic_034", sequence: 78, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_034.png", correctAnswer: "no" },
  { id: "analytic_035", sequence: 79, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_035.png", correctAnswer: "no" },
  { id: "analytic_036", sequence: 80, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_036.png", correctAnswer: "no" },
  { id: "analytic_037", sequence: 81, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_037.png", correctAnswer: "no" },
  { id: "analytic_038", sequence: 82, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_038.png", correctAnswer: "no" },
  { id: "analytic_039", sequence: 83, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_039.png", correctAnswer: "no" },
  { id: "analytic_040", sequence: 84, subtest: "analytic", practice: false, itemSet: "extended", asset: "/ecsa/analytic_040.png", correctAnswer: "yes" },
];

export function validateEcsaMaterials(trials: EcsaTrial[]) {
  const ids = new Set(trials.map((trial) => trial.id));
  const sequences = new Set(trials.map((trial) => trial.sequence));
  const practice = trials.filter((trial) => trial.practice);
  const analytic = trials.filter((trial) => !trial.practice && trial.subtest === "analytic");
  const wholistic = trials.filter((trial) => !trial.practice && trial.subtest === "wholistic");
  const valid = trials.length === 84 && practice.length === 4 && analytic.length === 40 && wholistic.length === 40 && ids.size === trials.length && sequences.size === trials.length && Math.min(...sequences) === 1 && Math.max(...sequences) === 84;
  return { valid, total: trials.length, practice: practice.length, analytic: analytic.length, wholistic: wholistic.length };
}
