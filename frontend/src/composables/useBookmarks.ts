import { computed, ref } from "vue";

const STORAGE_KEY = "seoullo-bookmarked-place-ids";

function readBookmarks(): number[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed)
      ? parsed.map(Number).filter((value) => Number.isInteger(value) && value > 0)
      : [];
  } catch {
    return [];
  }
}

const ids = ref<number[]>(typeof window === "undefined" ? [] : readBookmarks());

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids.value));
}

export function useBookmarks() {
  function has(placeId: number) {
    return ids.value.includes(placeId);
  }

  function toggle(placeId: number) {
    ids.value = has(placeId)
      ? ids.value.filter((id) => id !== placeId)
      : [placeId, ...ids.value];
    persist();
    return has(placeId);
  }

  return {
    ids: computed(() => ids.value),
    count: computed(() => ids.value.length),
    has,
    toggle,
  };
}

