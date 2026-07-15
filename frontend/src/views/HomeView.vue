<script setup lang="ts">
import { ArrowRight, Frown, LocateFixed, MapPinned, Search, SlidersHorizontal, Sparkles } from "lucide-vue-next";
import { nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { errorMessage, getCategories, getPlaces, getPopularTags } from "../api/client";
import AppTopbar from "../components/AppTopbar.vue";
import CategoryRail from "../components/CategoryRail.vue";
import LoadingCards from "../components/LoadingCards.vue";
import PlaceCard from "../components/PlaceCard.vue";
import type { CategoryCount, PlaceSort, PlaceSummary, PopularTag } from "../types/place";

const route = useRoute();
const router = useRouter();
const searchInput = ref<HTMLInputElement | null>(null);
const search = ref(typeof route.query.q === "string" ? route.query.q : "");
const selectedCategory = ref("");
const selectedSource = ref<"" | "dataset" | "user">("");
const sort = ref<PlaceSort>("latest");
const categories = ref<CategoryCount[]>([]);
const popularTags = ref<PopularTag[]>([]);
const searchFocused = ref(false);
const places = ref<PlaceSummary[]>([]);
const page = ref(1);
const totalPages = ref(1);
const total = ref(0);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref("");
const notice = ref("");
const coordinates = ref<{ latitude: number; longitude: number } | null>(null);
let debounceTimer: number | undefined;

async function loadPlaces(append = false) {
  if (append) loadingMore.value = true;
  else loading.value = true;
  error.value = "";
  try {
    const response = await getPlaces({
      q: search.value.trim(),
      content_type_id: selectedCategory.value || undefined,
      source: selectedSource.value || undefined,
      sort: sort.value,
      latitude: coordinates.value?.latitude,
      longitude: coordinates.value?.longitude,
      page: page.value,
      size: 18,
    });
    places.value = append ? [...places.value, ...response.items] : response.items;
    total.value = response.total;
    totalPages.value = response.total_pages;
    router.replace({ query: search.value.trim() ? { q: search.value.trim() } : {} });
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function refresh() {
  page.value = 1;
  loadPlaces();
}

function selectCategory(id: string) {
  selectedCategory.value = id;
  refresh();
}

function scheduleSearch() {
  window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(refresh, 320);
}

function choosePopularTag(tag: string) {
  search.value = `#${tag}`;
  searchFocused.value = false;
  refresh();
}

function hidePopularTags() {
  window.setTimeout(() => (searchFocused.value = false), 160);
}

async function selectSort(event: Event) {
  const nextSort = (event.target as HTMLSelectElement).value as PlaceSort;
  if (nextSort === "distance" && !coordinates.value) {
    if (!("geolocation" in navigator)) {
      notice.value = "이 브라우저에서는 위치 정보를 사용할 수 없습니다.";
      return;
    }
    try {
      coordinates.value = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
          (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
          reject,
          { enableHighAccuracy: true, timeout: 8000 },
        );
      });
    } catch {
      notice.value = "거리순 정렬을 사용하려면 위치 권한을 허용해 주세요.";
      return;
    }
  }
  sort.value = nextSort;
  refresh();
}

function loadMore() {
  if (loadingMore.value || page.value >= totalPages.value) return;
  page.value += 1;
  loadPlaces(true);
}

function showUpcoming(feature: string) {
  notice.value = `${feature} 기능은 다음 구현 단계에서 연결됩니다.`;
  window.setTimeout(() => (notice.value = ""), 2600);
}

onMounted(async () => {
  try {
    [categories.value, popularTags.value] = await Promise.all([getCategories(), getPopularTags()]);
  } catch (caught) {
    error.value = errorMessage(caught);
  }
  await loadPlaces();
  if (route.query.focus === "search") await nextTick(() => searchInput.value?.focus());
});

watch(
  () => route.query.focus,
  async (value) => {
    if (value === "search") await nextTick(() => searchInput.value?.focus());
  },
);
</script>

<template>
  <main class="page-shell home-page">
    <AppTopbar />

    <section class="home-hero">
      <div class="hero-copy">
        <span class="hero-kicker"><Sparkles :size="16" />오늘의 서울을 발견해요</span>
        <h1>지금 내 마음에 맞는<br /><em>서울의 장소</em></h1>
        <p>익숙한 골목부터 숨은 명소까지, 6천 개가 넘는 서울의 장소를 한곳에서 만나보세요.</p>
      </div>
      <div class="hero-orbit" aria-hidden="true">
        <span class="orbit-card orbit-one">한강 산책</span>
        <span class="orbit-card orbit-two">조용한 전시</span>
        <span class="orbit-pin"><MapPinned :size="28" /></span>
      </div>
    </section>

    <section class="search-panel" aria-label="장소 검색">
      <form class="search-field" @submit.prevent="refresh">
        <Search :size="20" />
        <input
          ref="searchInput"
          v-model="search"
          type="search"
          placeholder="장소, 지역 또는 #태그를 검색해 보세요"
          aria-label="장소 검색어"
          @input="scheduleSearch"
          @focus="searchFocused = true"
          @blur="hidePopularTags"
        />
        <button type="submit">검색</button>
      </form>
      <Transition name="popover">
        <aside v-if="searchFocused && !search.trim()" class="popular-tag-popover">
          <div><strong>지금 인기 있는 태그</strong><small>Seoullo 사용자가 많이 등록한 태그예요.</small></div>
          <div v-if="popularTags.length" class="popular-tag-list">
            <button v-for="tag in popularTags" :key="tag.name" type="button" @mousedown.prevent="choosePopularTag(tag.name)">#{{ tag.name }}<span>{{ tag.usage_count }}</span></button>
          </div>
          <p v-else>새 장소가 등록되면 인기 태그가 여기에 표시됩니다.</p>
        </aside>
      </Transition>
      <button class="map-view-button" type="button" @click="router.push({ name: 'map' })">
        <LocateFixed :size="19" />지도 보기
      </button>
    </section>

    <section class="emotion-banner">
      <div>
        <span>마음 여행 큐레이터</span>
        <h2>오늘은 어떤 기분으로 떠나고 싶나요?</h2>
        <p>현재 감정을 알려주면 어울리는 장소를 찾아드릴게요.</p>
      </div>
      <button type="button" @click="router.push({ name: 'emotions' })">
        감정 체크 시작 <ArrowRight :size="17" />
      </button>
    </section>

    <section class="content-section category-section">
      <div class="section-heading">
        <div><span class="section-eyebrow">EXPLORE</span><h2>어디로 가볼까요?</h2></div>
        <span class="desktop-hint">좌우로 둘러보세요</span>
      </div>
      <CategoryRail :categories="categories" :selected="selectedCategory" @select="selectCategory" />
    </section>

    <section class="content-section place-section">
      <div class="list-toolbar">
        <div>
          <span class="section-eyebrow">PLACES</span>
          <h2>{{ selectedCategory ? categories.find(item => item.content_type_id === selectedCategory)?.content_type : '서울의 모든 장소' }}</h2>
          <p>총 {{ total.toLocaleString() }}곳</p>
        </div>
        <div class="toolbar-controls">
          <div class="source-segment" aria-label="장소 출처 필터">
            <button :class="{ active: selectedSource === '' }" type="button" @click="selectedSource = ''; refresh()">전체</button>
            <button :class="{ active: selectedSource === 'dataset' }" type="button" @click="selectedSource = 'dataset'; refresh()">공공데이터</button>
            <button :class="{ active: selectedSource === 'user' }" type="button" @click="selectedSource = 'user'; refresh()">새 발견</button>
          </div>
          <label class="sort-select">
            <SlidersHorizontal :size="17" />
            <select :value="sort" aria-label="정렬 방식" @change="selectSort">
              <option value="latest">최신순</option>
              <option value="rating">별점순</option>
              <option value="likes">좋아요순</option>
              <option value="distance">거리순</option>
            </select>
          </label>
        </div>
      </div>

      <LoadingCards v-if="loading" />
      <div v-else-if="error" class="state-card error-state">
        <Frown :size="38" />
        <h3>장소를 불러오지 못했어요</h3>
        <p>{{ error }}</p>
        <button class="primary-button" type="button" @click="refresh">다시 시도</button>
      </div>
      <div v-else-if="!places.length" class="state-card">
        <Search :size="38" />
        <h3>조건에 맞는 장소가 없어요</h3>
        <p>검색어나 카테고리를 바꿔 다시 찾아보세요.</p>
      </div>
      <div v-else class="place-grid">
        <PlaceCard v-for="place in places" :key="place.id" :place="place" />
      </div>

      <button v-if="!loading && page < totalPages" class="load-more" type="button" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? '불러오는 중…' : '장소 더 보기' }}
      </button>
    </section>

    <Transition name="toast"><div v-if="notice" class="toast">{{ notice }}</div></Transition>
  </main>
</template>
