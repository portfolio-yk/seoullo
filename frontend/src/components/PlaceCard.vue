<script setup lang="ts">
import { Eye, Heart, Image, MapPin, Star } from "lucide-vue-next";
import { computed, ref, watch } from "vue";
import { mediaUrl } from "../api/client";
import type { PlaceSummary } from "../types/place";

const props = defineProps<{ place: PlaceSummary }>();
const imageFailed = ref(false);
const source = computed(() => mediaUrl(props.place.image_url));

watch(source, () => {
  imageFailed.value = false;
});

const location = computed(() =>
  [props.place.address, props.place.detail_address].filter(Boolean).join(" ") || "주소 정보 확인 중",
);
</script>

<template>
  <RouterLink :to="`/places/${place.id}`" class="place-card">
    <div class="place-card-media">
      <img
        v-if="source && !imageFailed"
        :src="source"
        :alt="`${place.title} 대표 이미지`"
        loading="lazy"
        @error="imageFailed = true"
      />
      <div v-else class="image-placeholder" aria-label="등록된 이미지 없음">
        <Image :size="34" />
        <span>Seoullo</span>
      </div>
      <span class="place-category">{{ place.content_type }}</span>
      <span v-if="place.source === 'user'" class="community-badge">새 발견</span>
    </div>
    <div class="place-card-body">
      <h3>{{ place.title }}</h3>
      <p class="place-location"><MapPin :size="15" />{{ location }}</p>
      <div v-if="place.tags.length" class="tag-row">
        <span v-for="tag in place.tags.slice(0, 3)" :key="tag">#{{ tag }}</span>
      </div>
      <div class="place-card-meta">
        <span><Star :size="15" :fill="place.average_rating ? 'currentColor' : 'none'" />{{ place.average_rating.toFixed(1) }}</span>
        <span><Heart :size="15" />{{ place.like_count.toLocaleString() }}</span>
        <span><Eye :size="15" />{{ place.view_count.toLocaleString() }}</span>
        <span v-if="place.distance_meters !== null" class="distance">
          {{ place.distance_meters < 1000 ? `${Math.round(place.distance_meters)}m` : `${(place.distance_meters / 1000).toFixed(1)}km` }}
        </span>
      </div>
    </div>
  </RouterLink>
</template>

