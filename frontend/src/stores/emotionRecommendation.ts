import { defineStore } from "pinia";
import { ref } from "vue";
import type { EmotionRecommendationResponse } from "../types/place";

export type EmotionGroupKey = "mood" | "afterFeeling" | "style";
export type EmotionSelections = Record<EmotionGroupKey, string[]>;

export const useEmotionRecommendationStore = defineStore("emotion-recommendation", () => {
  const step = ref(0);
  const selected = ref<EmotionSelections>({ mood: [], afterFeeling: [], style: [] });
  const result = ref<EmotionRecommendationResponse | null>(null);

  function reset() {
    step.value = 0;
    selected.value = { mood: [], afterFeeling: [], style: [] };
    result.value = null;
  }

  return { step, selected, result, reset };
});
