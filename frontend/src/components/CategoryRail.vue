<script setup lang="ts">
import {
  BedDouble,
  Bike,
  Building2,
  CalendarDays,
  Camera,
  Compass,
  Map,
  ShoppingBag,
} from "lucide-vue-next";
import type { Component } from "vue";
import type { CategoryCount } from "../types/place";

defineProps<{
  categories: CategoryCount[];
  selected: string;
  loading?: boolean;
}>();

const emit = defineEmits<{ select: [contentTypeId: string] }>();

const icons: Record<string, Component> = {
  "12": Camera,
  "14": Building2,
  "15": CalendarDays,
  "25": Map,
  "28": Bike,
  "32": BedDouble,
  "38": ShoppingBag,
};
</script>

<template>
  <div class="category-rail" aria-label="장소 카테고리">
    <button
      class="category-chip"
      :class="{ active: selected === '' }"
      type="button"
      @click="emit('select', '')"
    >
      <span class="category-icon"><Compass :size="21" /></span>
      <span>전체</span>
      <small>{{ categories.reduce((sum, item) => sum + item.count, 0).toLocaleString() }}</small>
    </button>
    <button
      v-for="category in categories"
      :key="category.content_type_id"
      class="category-chip"
      :class="{ active: selected === category.content_type_id }"
      type="button"
      @click="emit('select', category.content_type_id)"
    >
      <span class="category-icon">
        <component :is="icons[category.content_type_id]" :size="21" />
      </span>
      <span>{{ category.content_type }}</span>
      <small>{{ category.count.toLocaleString() }}</small>
    </button>
  </div>
</template>
