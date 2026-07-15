<script setup lang="ts">
import { LoaderCircle, MapPin, Search } from "lucide-vue-next";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { errorMessage, reverseGeocode, searchKakaoAddress } from "../api/client";
import { loadKakaoMaps } from "../lib/kakaoMaps";
import type { AddressSearchResult } from "../types/place";

const props = defineProps<{ latitude: number | null; longitude: number | null; address: string }>();
const emit = defineEmits<{ select: [value: { latitude: number; longitude: number; address: string; zipcode: string }] }>();
const mapElement = ref<HTMLElement | null>(null);
const query = ref(props.address);
const results = ref<AddressSearchResult[]>([]);
const searching = ref(false);
const error = ref("");
let map: any = null;
let marker: any = null;

function setMarker(latitude: number, longitude: number, pan = true) {
  if (!map) return;
  const position = new window.kakao.maps.LatLng(latitude, longitude);
  if (!marker) {
    marker = new window.kakao.maps.Marker({ map, position, draggable: true });
    window.kakao.maps.event.addListener(marker, "dragend", async () => {
      const next = marker.getPosition();
      await selectCoordinates(next.getLat(), next.getLng());
    });
  } else marker.setPosition(position);
  if (pan) map.panTo(position);
}

async function selectCoordinates(latitude: number, longitude: number) {
  setMarker(latitude, longitude);
  try {
    const location = await reverseGeocode(latitude, longitude);
    query.value = location.address;
    emit("select", { latitude, longitude, address: location.address, zipcode: location.zipcode });
  } catch (caught) {
    error.value = errorMessage(caught);
    emit("select", { latitude, longitude, address: "", zipcode: "" });
  }
}

async function search() {
  if (query.value.trim().length < 2) { error.value = "주소를 두 글자 이상 입력해 주세요."; return; }
  searching.value = true; error.value = "";
  try { results.value = await searchKakaoAddress(query.value.trim()); }
  catch (caught) { error.value = errorMessage(caught); }
  finally { searching.value = false; }
}

function choose(result: AddressSearchResult) {
  results.value = [];
  query.value = result.address;
  setMarker(result.latitude, result.longitude);
  emit("select", { latitude: result.latitude, longitude: result.longitude, address: result.address, zipcode: result.zipcode });
}

onMounted(async () => {
  try {
    await loadKakaoMaps();
    if (!mapElement.value) return;
    const latitude = props.latitude ?? 37.5665;
    const longitude = props.longitude ?? 126.9780;
    map = new window.kakao.maps.Map(mapElement.value, { center: new window.kakao.maps.LatLng(latitude, longitude), level: 5 });
    if (props.latitude !== null && props.longitude !== null) setMarker(props.latitude, props.longitude, false);
    window.kakao.maps.event.addListener(map, "click", async (event: any) => {
      await selectCoordinates(event.latLng.getLat(), event.latLng.getLng());
    });
  } catch (caught) { error.value = errorMessage(caught); }
});

watch(
  () => [props.latitude, props.longitude] as const,
  ([latitude, longitude]) => { if (latitude !== null && longitude !== null) setMarker(latitude, longitude); },
);
onBeforeUnmount(() => { if (marker) marker.setMap(null); });
</script>

<template>
  <div class="location-picker">
    <form class="location-search" @submit.prevent="search">
      <Search :size="18" /><input v-model="query" type="search" placeholder="도로명, 지번 또는 장소 주소 검색" aria-label="주소 검색" /><button type="submit" :disabled="searching"><LoaderCircle v-if="searching" class="spin" :size="16" />{{ searching ? '검색 중' : '검색' }}</button>
    </form>
    <div v-if="results.length" class="location-results"><button v-for="result in results" :key="`${result.latitude}-${result.longitude}`" type="button" @click="choose(result)"><MapPin :size="17" /><span><strong>{{ result.road_address || result.address }}</strong><small v-if="result.lot_address">{{ result.lot_address }}</small></span></button></div>
    <div ref="mapElement" class="location-picker-map" aria-label="장소 위치 선택 지도" />
    <p class="location-picker-help">지도를 누르거나 핀을 움직여 정확한 위치를 지정하세요.</p>
    <p v-if="error" class="field-error">{{ error }}</p>
  </div>
</template>

