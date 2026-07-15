<script setup lang="ts">
import { ArrowLeft, Crosshair, Eye, Heart, Image, Layers3, MapPin, Star, X } from "lucide-vue-next";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { errorMessage, getCategories, getMapPoints, getPlace, mediaUrl } from "../api/client";
import { loadKakaoMaps } from "../lib/kakaoMaps";
import type { CategoryCount, PlaceMapPoint, PlaceSummary } from "../types/place";

type MapPlace = PlaceMapPoint | PlaceSummary;

const route = useRoute();
const router = useRouter();
const mapElement = ref<HTMLElement | null>(null);
const loading = ref(true);
const error = ref("");
const notice = ref("");
const categories = ref<CategoryCount[]>([]);
const selectedCategory = ref("");
const places = ref<MapPlace[]>([]);
const selectedPlace = ref<MapPlace | null>(null);
const currentPosition = ref({ latitude: 37.5665, longitude: 126.9780 });
const locationGranted = ref(false);
const placeId = computed(() => typeof route.query.placeId === "string" ? route.query.placeId : "");
const recommendationIds = computed(() => {
  if (typeof route.query.ids !== "string") return [];
  return [...new Set(route.query.ids.split(",").map(Number).filter((id) => Number.isInteger(id) && id > 0))].slice(0, 100);
});
const detailMode = computed(() => Boolean(placeId.value));
const recommendationMode = computed(() => !detailMode.value && recommendationIds.value.length > 0);
const nearbyMode = computed(() => !detailMode.value && !recommendationMode.value);
const mapTitle = computed(() => {
  if (detailMode.value) return selectedPlace.value?.title || "장소 위치";
  if (recommendationMode.value) return "추천 장소 5곳";
  return "내 주변 서울";
});
let map: any = null;
let markers: any[] = [];
let clusterer: any = null;
let userOverlay: any = null;

const selectedImage = computed(() => mediaUrl(selectedPlace.value?.image_url));

function geolocate(): Promise<{ latitude: number; longitude: number }> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error("이 브라우저는 위치 확인을 지원하지 않습니다.")); return; }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      () => reject(new Error("위치 권한이 없어 서울시청을 기준으로 보여드려요.")),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 },
    );
  });
}

async function loadNearby() {
  places.value = await getMapPoints({
    content_type_id: selectedCategory.value || undefined,
    latitude: currentPosition.value.latitude,
    longitude: currentPosition.value.longitude,
    radius_meters: 7000,
  });
}

async function loadRecommendations() {
  places.value = await getMapPoints({ ids: recommendationIds.value });
  if (places.value.length) {
    currentPosition.value = {
      latitude: places.value.reduce((sum, place) => sum + place.latitude, 0) / places.value.length,
      longitude: places.value.reduce((sum, place) => sum + place.longitude, 0) / places.value.length,
    };
  }
}

function clearMarkers() {
  if (clusterer) clusterer.clear();
  markers.forEach((marker) => marker.setMap(null));
  markers = [];
}

function renderUserPosition() {
  if (!map || !locationGranted.value) return;
  if (userOverlay) userOverlay.setMap(null);
  const dot = document.createElement("div");
  dot.className = "map-user-dot";
  dot.setAttribute("aria-label", "내 위치");
  userOverlay = new window.kakao.maps.CustomOverlay({
    map,
    position: new window.kakao.maps.LatLng(currentPosition.value.latitude, currentPosition.value.longitude),
    content: dot,
    yAnchor: 0.5,
  });
}

function fitRecommendationBounds() {
  if (!map || !recommendationMode.value || !places.value.length) return;
  if (places.value.length === 1) {
    map.setCenter(new window.kakao.maps.LatLng(places.value[0].latitude, places.value[0].longitude));
    map.setLevel(4);
    return;
  }
  const bounds = new window.kakao.maps.LatLngBounds();
  places.value.forEach((place) => bounds.extend(new window.kakao.maps.LatLng(place.latitude, place.longitude)));
  map.setBounds(bounds, 90, 45, 170, 45);
}

function renderMarkers() {
  if (!map) return;
  clearMarkers();
  markers = places.value.map((place) => {
    const marker = new window.kakao.maps.Marker({
      position: new window.kakao.maps.LatLng(place.latitude, place.longitude),
      title: place.title,
    });
    window.kakao.maps.event.addListener(marker, "click", () => {
      selectedPlace.value = place;
      map.panTo(new window.kakao.maps.LatLng(place.latitude, place.longitude));
    });
    return marker;
  });
  if (detailMode.value) markers.forEach((marker) => marker.setMap(map));
  else {
    if (!clusterer) clusterer = new window.kakao.maps.MarkerClusterer({ map, averageCenter: true, minLevel: 6 });
    clusterer.addMarkers(markers);
  }
  renderUserPosition();
  fitRecommendationBounds();
}

async function initializeMap() {
  await loadKakaoMaps();
  await nextTick();
  if (!mapElement.value) return;
  map = new window.kakao.maps.Map(mapElement.value, {
    center: new window.kakao.maps.LatLng(currentPosition.value.latitude, currentPosition.value.longitude),
    level: detailMode.value ? 4 : 7,
  });
  renderMarkers();
}

async function refreshCategory() {
  if (!nearbyMode.value) return;
  loading.value = true;
  error.value = "";
  selectedPlace.value = null;
  try { await loadNearby(); renderMarkers(); }
  catch (caught) { error.value = errorMessage(caught); }
  finally { loading.value = false; }
}

async function moveToMyLocation() {
  try {
    currentPosition.value = await geolocate();
    locationGranted.value = true;
    map?.setCenter(new window.kakao.maps.LatLng(currentPosition.value.latitude, currentPosition.value.longitude));
    await loadNearby();
    renderMarkers();
  } catch (caught) { notice.value = errorMessage(caught); window.setTimeout(() => (notice.value = ""), 2800); }
}

onMounted(async () => {
  try {
    if (detailMode.value) {
      const detail = await getPlace(placeId.value);
      places.value = [detail];
      selectedPlace.value = detail;
      currentPosition.value = { latitude: detail.latitude, longitude: detail.longitude };
    } else if (recommendationMode.value) {
      await loadRecommendations();
    } else {
      categories.value = await getCategories();
      try { currentPosition.value = await geolocate(); locationGranted.value = true; }
      catch (caught) { notice.value = errorMessage(caught); window.setTimeout(() => (notice.value = ""), 3500); }
      await loadNearby();
    }
    await initializeMap();
  } catch (caught) { error.value = errorMessage(caught); }
  finally { loading.value = false; }
});

watch(selectedCategory, refreshCategory);
onBeforeUnmount(() => {
  clearMarkers();
  if (userOverlay) userOverlay.setMap(null);
});
</script>

<template>
  <main class="map-page">
    <header class="map-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="router.back()"><ArrowLeft :size="21" /></button>
      <div><span>{{ detailMode ? 'PLACE MAP' : recommendationMode ? 'EMOTION PICKS' : 'AROUND ME' }}</span><h1>{{ mapTitle }}</h1></div>
      <button v-if="nearbyMode" class="icon-button" type="button" aria-label="현재 위치로 이동" @click="moveToMyLocation"><Crosshair :size="20" /></button>
      <span v-else class="map-count">{{ places.length }}</span>
    </header>

    <div v-if="nearbyMode" class="map-category-rail" aria-label="지도 카테고리">
      <button :class="{ active: selectedCategory === '' }" type="button" @click="selectedCategory = ''"><Layers3 :size="15" />전체</button>
      <button v-for="category in categories" :key="category.content_type_id" :class="{ active: selectedCategory === category.content_type_id }" type="button" @click="selectedCategory = category.content_type_id">{{ category.content_type }}</button>
    </div>

    <div ref="mapElement" class="kakao-map" :aria-label="detailMode ? `${selectedPlace?.title} 지도` : recommendationMode ? '감정 추천 장소 지도' : '내 주변 장소 지도'" />

    <div v-if="loading" class="map-status"><span class="map-status-spinner" />장소를 지도에 표시하고 있어요</div>
    <div v-else-if="error" class="map-status map-error"><MapPin :size="24" /><strong>지도를 열지 못했어요</strong><span>{{ error }}</span></div>
    <div v-else-if="!places.length" class="map-status"><MapPin :size="24" /><strong>{{ recommendationMode ? '추천 장소를 찾지 못했어요' : '7km 안에 해당 장소가 없어요' }}</strong><span>{{ recommendationMode ? '감정 추천을 다시 진행해 주세요.' : '다른 카테고리를 선택해 보세요.' }}</span></div>

    <Transition name="map-sheet">
      <article v-if="selectedPlace" class="map-place-sheet">
        <button class="map-sheet-close" type="button" aria-label="장소 정보 닫기" @click="selectedPlace = null"><X :size="18" /></button>
        <RouterLink :to="`/places/${selectedPlace.id}`" class="map-place-link">
          <div class="map-place-image"><img v-if="selectedImage" :src="selectedImage" :alt="`${selectedPlace.title} 이미지`" /><span v-else><Image :size="24" /></span></div>
          <div class="map-place-copy"><span class="map-place-category">{{ selectedPlace.content_type }}</span><h2>{{ selectedPlace.title }}</h2><p><MapPin :size="14" />{{ selectedPlace.address || '주소 정보 확인 중' }}</p><div><span><Star :size="14" fill="currentColor" />{{ selectedPlace.average_rating.toFixed(1) }}</span><span><Heart :size="14" />{{ selectedPlace.like_count.toLocaleString() }}</span><span><Eye :size="14" />{{ selectedPlace.view_count.toLocaleString() }}</span><strong v-if="selectedPlace.distance_meters !== null">{{ selectedPlace.distance_meters < 1000 ? `${Math.round(selectedPlace.distance_meters)}m` : `${(selectedPlace.distance_meters / 1000).toFixed(1)}km` }}</strong></div></div>
        </RouterLink>
      </article>
    </Transition>
    <Transition name="toast"><div v-if="notice" class="toast">{{ notice }}</div></Transition>
  </main>
</template>
