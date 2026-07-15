<script setup lang="ts">
import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  ImagePlus,
  LoaderCircle,
  MapPin,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  createPlace,
  deletePlaceImage,
  duplicateWarning,
  errorMessage,
  getCategories,
  getPlace,
  mediaUrl,
  updatePlace,
} from "../api/client";
import BaseModal from "../components/BaseModal.vue";
import MapLocationPicker from "../components/MapLocationPicker.vue";
import type { CategoryCount, DuplicateWarning, PlaceImage } from "../types/place";

const props = defineProps<{ id?: string }>();
const route = useRoute();
const router = useRouter();
const editing = computed(() => route.name === "place-edit");
const loading = ref(editing.value);
const submitting = ref(false);
const error = ref("");
const categories = ref<CategoryCount[]>([]);
const tagsInput = ref("");
const files = ref<File[]>([]);
const previews = ref<{ file: File; url: string }[]>([]);
const existingImages = ref<PlaceImage[]>([]);
const duplicate = ref<DuplicateWarning | null>(null);
const form = reactive({
  title: "",
  contentTypeId: "12",
  description: "",
  address: "",
  detailAddress: "",
  latitude: null as number | null,
  longitude: null as number | null,
  password: "",
});

function selectLocation(value: { latitude: number; longitude: number; address: string; zipcode: string }) {
  form.latitude = Number(value.latitude.toFixed(7));
  form.longitude = Number(value.longitude.toFixed(7));
  if (value.address) form.address = value.address;
}

const parsedTags = computed(() => {
  const unique = new Set<string>();
  tagsInput.value.split(/[,\s]+/).forEach((value) => {
    const tag = value.trim().replace(/^#/, "");
    if (tag) unique.add(tag);
  });
  return [...unique].slice(0, 10);
});

const imageCount = computed(() => existingImages.value.length + files.value.length);

function releasePreviews() {
  previews.value.forEach((preview) => URL.revokeObjectURL(preview.url));
}

function addFiles(selected: FileList | File[]) {
  error.value = "";
  const incoming = Array.from(selected);
  if (imageCount.value + incoming.length > 5) {
    error.value = "장소 이미지는 기존 이미지를 포함해 최대 5장까지 등록할 수 있습니다.";
    return;
  }
  for (const file of incoming) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      error.value = "JPEG, PNG, WebP 이미지만 선택할 수 있습니다.";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      error.value = "이미지 한 장은 5MB 이하여야 합니다.";
      return;
    }
  }
  files.value.push(...incoming);
  previews.value.push(...incoming.map((file) => ({ file, url: URL.createObjectURL(file) })));
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files) addFiles(input.files);
  input.value = "";
}

function removeNewImage(index: number) {
  URL.revokeObjectURL(previews.value[index].url);
  previews.value.splice(index, 1);
  files.value.splice(index, 1);
}

async function removeExistingImage(image: PlaceImage) {
  if (!form.password) {
    error.value = "기존 이미지를 삭제하려면 먼저 수정용 비밀번호를 입력해 주세요.";
    return;
  }
  try {
    await deletePlaceImage(props.id!, image.id, form.password);
    existingImages.value = existingImages.value.filter((item) => item.id !== image.id);
  } catch (caught) {
    error.value = errorMessage(caught);
  }
}

function buildFormData(allowDuplicate: boolean) {
  const payload = new FormData();
  payload.set("title", form.title.trim());
  payload.set("content_type_id", form.contentTypeId);
  payload.set("description", form.description.trim());
  payload.set("latitude", String(form.latitude));
  payload.set("longitude", String(form.longitude));
  payload.set("password", form.password);
  payload.set("address", form.address.trim());
  payload.set("detail_address", form.detailAddress.trim());
  payload.set("tags", JSON.stringify(parsedTags.value));
  payload.set("allow_duplicate", String(allowDuplicate));
  files.value.forEach((file) => payload.append("images", file));
  return payload;
}

function validate() {
  if (!form.title.trim() || !form.description.trim()) return "장소명과 설명을 입력해 주세요.";
  if (form.latitude === null || form.longitude === null) return "장소의 위도와 경도를 입력해 주세요.";
  if (!Number.isFinite(Number(form.latitude)) || !Number.isFinite(Number(form.longitude))) {
    return "위도와 경도는 숫자로 입력해 주세요.";
  }
  if (Number(form.latitude) < 33 || Number(form.latitude) > 39.5) return "위도는 33~39.5 범위로 입력해 주세요.";
  if (Number(form.longitude) < 124 || Number(form.longitude) > 132) return "경도는 124~132 범위로 입력해 주세요.";
  if (!form.password.trim()) return "수정과 삭제에 사용할 비밀번호를 입력해 주세요.";
  if (parsedTags.value.some((tag) => tag.length > 6)) return "태그는 6글자 이하여야 합니다.";
  return "";
}

async function submit(allowDuplicate = false) {
  const validation = validate();
  if (validation) {
    error.value = validation;
    return;
  }
  submitting.value = true;
  error.value = "";
  try {
    const result = editing.value
      ? await updatePlace(props.id!, buildFormData(allowDuplicate))
      : await createPlace(buildFormData(allowDuplicate));
    duplicate.value = null;
    router.replace({ name: "place-detail", params: { id: result.id } });
  } catch (caught) {
    const warning = duplicateWarning(caught);
    if (warning) duplicate.value = warning;
    else error.value = errorMessage(caught);
  } finally {
    submitting.value = false;
  }
}

async function initialize() {
  try {
    categories.value = await getCategories();
    if (editing.value && props.id) {
      const place = await getPlace(props.id);
      if (place.source !== "user") {
        error.value = "공공데이터 장소는 수정할 수 없습니다.";
        return;
      }
      form.title = place.title;
      form.contentTypeId = place.content_type_id;
      form.description = place.description;
      form.address = place.address;
      form.detailAddress = place.detail_address;
      form.latitude = place.latitude;
      form.longitude = place.longitude;
      tagsInput.value = place.tags.join(", ");
      existingImages.value = place.images;
    }
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

onMounted(initialize);
onBeforeUnmount(releasePreviews);
</script>

<template>
  <main class="page-shell form-page">
    <header class="form-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="router.back()"><ArrowLeft :size="21" /></button>
      <div><span>{{ editing ? 'PLACE EDIT' : 'NEW DISCOVERY' }}</span><h1>{{ editing ? '장소 정보 수정' : '새로운 장소 등록' }}</h1></div>
      <span class="form-step">필수 *</span>
    </header>

    <div v-if="loading" class="form-loading"><LoaderCircle class="spin" :size="30" /><p>장소 정보를 준비하고 있어요.</p></div>
    <form v-else class="place-form" @submit.prevent="submit(false)">
      <section class="form-section">
        <div class="form-section-heading"><span class="form-section-number">01</span><div><h2>어떤 장소인가요?</h2><p>사람들이 장소를 쉽게 알아볼 수 있게 알려주세요.</p></div></div>
        <div class="field-grid">
          <label class="field-label field-span-2">장소명 *<input v-model="form.title" type="text" maxlength="300" placeholder="예: 노을이 아름다운 작은 공원" required /></label>
          <label class="field-label">카테고리 *<select v-model="form.contentTypeId" required><option v-for="category in categories" :key="category.content_type_id" :value="category.content_type_id">{{ category.content_type }}</option></select></label>
          <label class="field-label field-span-2">장소 설명 *<textarea v-model="form.description" maxlength="10000" rows="6" placeholder="이 장소만의 분위기와 방문 팁을 자세히 소개해 주세요." required /><small>{{ form.description.length.toLocaleString() }} / 10,000</small></label>
        </div>
      </section>

      <section class="form-section">
        <div class="form-section-heading"><span class="form-section-number">02</span><div><h2>어디에 있나요?</h2><p>주소는 선택 사항이지만 정확한 좌표는 꼭 필요합니다.</p></div></div>
        <div class="location-helper"><span><MapPin :size="21" /><strong>지도에서 위치 선택</strong><small>주소를 검색하거나 지도 핀을 움직여 좌표를 지정하세요.</small></span></div>
        <MapLocationPicker :latitude="form.latitude" :longitude="form.longitude" :address="form.address" @select="selectLocation" />
        <div class="field-grid two-columns">
          <label class="field-label">위도 *<input v-model.number="form.latitude" type="number" min="33" max="39.5" step="any" inputmode="decimal" placeholder="37.5665000" required /></label>
          <label class="field-label">경도 *<input v-model.number="form.longitude" type="number" min="124" max="132" step="any" inputmode="decimal" placeholder="126.9780000" required /></label>
          <label class="field-label">주소<input v-model="form.address" type="text" maxlength="500" placeholder="서울특별시 ○○구 ○○로" /></label>
          <label class="field-label">상세 주소<input v-model="form.detailAddress" type="text" maxlength="500" placeholder="건물명, 층 등" /></label>
        </div>
      </section>

      <section class="form-section">
        <div class="form-section-heading"><span class="form-section-number">03</span><div><h2>사진과 태그를 더해요</h2><p>분위기가 잘 드러나는 사진을 최대 5장까지 등록할 수 있어요.</p></div></div>
        <label class="upload-zone" :class="{ compact: imageCount > 0 }">
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple @change="onFileInput" />
          <ImagePlus :size="29" /><strong>사진 선택하기</strong><span>JPEG, PNG, WebP · 장당 최대 5MB</span><small>{{ imageCount }} / 5장</small>
        </label>
        <div v-if="existingImages.length || previews.length" class="upload-preview-grid">
          <div v-for="image in existingImages" :key="image.id" class="upload-preview"><img :src="mediaUrl(image.url) || ''" :alt="image.filename" /><button type="button" aria-label="기존 이미지 삭제" @click="removeExistingImage(image)"><Trash2 :size="16" /></button><span>등록됨</span></div>
          <div v-for="(preview, index) in previews" :key="preview.url" class="upload-preview"><img :src="preview.url" :alt="preview.file.name" /><button type="button" aria-label="선택 이미지 제거" @click="removeNewImage(index)"><X :size="17" /></button><span>새 이미지</span></div>
        </div>
        <label class="field-label tag-input">태그<input v-model="tagsInput" type="text" placeholder="#숨은명소, #산책, #야경" /><small>쉼표나 띄어쓰기로 구분 · 태그당 6글자 이하 · 최대 10개</small></label>
        <div v-if="parsedTags.length" class="tag-row form-tags"><span v-for="tag in parsedTags" :key="tag">#{{ tag }}</span></div>
      </section>

      <section class="form-section password-section">
        <div class="form-section-heading"><span class="form-section-number">04</span><div><h2>수정용 비밀번호</h2><p>로그인 없이 이 장소를 수정하거나 삭제할 때 사용합니다.</p></div></div>
        <label class="field-label">비밀번호 *<input v-model="form.password" type="password" maxlength="200" autocomplete="new-password" placeholder="나중에 꼭 기억할 수 있는 비밀번호" required /></label>
        <p class="password-notice"><AlertTriangle :size="17" />교육 요구사항에 따라 비밀번호가 평문으로 저장됩니다. 다른 서비스에서 쓰는 비밀번호는 사용하지 마세요.</p>
      </section>

      <p v-if="error" class="form-error"><AlertTriangle :size="18" />{{ error }}</p>
      <p class="ai-profile-notice"><Sparkles :size="16" /><span><strong>감정 프로필 자동 분석</strong>장소를 저장하면 AI가 16개 기본 감정 수치를 만들고 추천 벡터에 반영해요.</span></p>
      <div class="form-actions"><button class="secondary-button" type="button" @click="router.back()">취소</button><button class="primary-button" type="submit" :disabled="submitting"><LoaderCircle v-if="submitting" class="spin" :size="18" /><Plus v-else :size="18" />{{ submitting ? '감정 프로필 만드는 중…' : editing ? '수정 완료' : '장소 등록' }}</button></div>
    </form>

    <BaseModal :open="Boolean(duplicate)" title="비슷한 장소가 있어요" @close="duplicate = null">
      <p class="modal-description">같은 이름의 장소가 50m 안에 있습니다. 아래 장소와 다른 곳이 맞는지 확인해 주세요.</p>
      <div class="duplicate-list"><RouterLink v-for="candidate in duplicate?.candidates" :key="candidate.id" :to="`/places/${candidate.id}`" target="_blank"><MapPin :size="18" /><span><strong>{{ candidate.title }}</strong><small>{{ candidate.address || '주소 정보 없음' }} · {{ candidate.distance_meters }}m</small></span></RouterLink></div>
      <template #footer><button class="secondary-button" type="button" @click="duplicate = null">다시 확인</button><button class="primary-button" type="button" :disabled="submitting" @click="submit(true)">다른 장소로 등록</button></template>
    </BaseModal>
  </main>
</template>
