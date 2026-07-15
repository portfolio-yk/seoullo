<script setup lang="ts">
import { ArrowLeft, Bookmark, Search } from "lucide-vue-next";
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { errorMessage, getPlaces } from "../api/client";
import { useBookmarks } from "../composables/useBookmarks";
import LoadingCards from "../components/LoadingCards.vue";
import PlaceCard from "../components/PlaceCard.vue";
import type { PlaceSummary } from "../types/place";

const router = useRouter();
const bookmarks = useBookmarks();
const places = ref<PlaceSummary[]>([]);
const loading = ref(true);
const error = ref("");

async function load() {
  if (!bookmarks.ids.value.length) { places.value = []; loading.value = false; return; }
  loading.value = true; error.value = "";
  try {
    const response = await getPlaces({ ids: bookmarks.ids.value, size: 100 });
    const order = new Map(bookmarks.ids.value.map((id, index) => [id, index]));
    places.value = response.items.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0));
  } catch (caught) { error.value = errorMessage(caught); }
  finally { loading.value = false; }
}

onMounted(load);
watch(() => bookmarks.ids.value.join(","), load);
</script>

<template>
  <main class="page-shell bookmarks-page">
    <header class="detail-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="router.back()"><ArrowLeft :size="21" /></button>
      <div class="saved-heading"><span class="section-eyebrow">MY SEOUL</span><h1>저장한 장소</h1></div>
      <span class="saved-count">{{ bookmarks.count.value }}</span>
    </header>
    <LoadingCards v-if="loading" />
    <section v-else-if="error" class="state-card error-state"><h2>저장한 장소를 불러오지 못했어요</h2><p>{{ error }}</p><button class="primary-button" type="button" @click="load">다시 시도</button></section>
    <section v-else-if="!places.length" class="state-card saved-empty"><Bookmark :size="42" /><h2>아직 저장한 장소가 없어요</h2><p>마음에 드는 장소의 저장 버튼을 눌러 나만의 서울 목록을 만들어 보세요.</p><RouterLink class="primary-button" to="/"><Search :size="17" />장소 둘러보기</RouterLink></section>
    <section v-else><p class="saved-description">이 브라우저에 저장된 장소 {{ places.length }}곳입니다.</p><div class="place-grid"><PlaceCard v-for="place in places" :key="place.id" :place="place" /></div></section>
  </main>
</template>
