<script setup lang="ts">
import {
  ArrowLeft, Bookmark, ChevronRight, Edit3, Eye, Heart, Image, MapPin,
  Navigation, Phone, Plus, Sparkles, Star, Trash2, ThumbsUp, X,
} from "lucide-vue-next";
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  addPlaceTags, createReview, deletePlace, deletePlaceTag, deleteReview, errorMessage,
  getPlace, getReviews, incrementPlaceView, mediaUrl, togglePlaceLike,
  toggleReviewLike, updateReview,
} from "../api/client";
import BaseModal from "../components/BaseModal.vue";
import { useBookmarks } from "../composables/useBookmarks";
import type { PlaceDetail, Review } from "../types/place";

const props = defineProps<{ id: string }>();
const router = useRouter();
const bookmarks = useBookmarks();
const place = ref<PlaceDetail | null>(null);
const loading = ref(true);
const error = ref("");
const activeImage = ref("");
const imageFailed = ref(false);
const deleteOpen = ref(false);
const deletePassword = ref("");
const deleting = ref(false);
const actionError = ref("");
const notice = ref("");
const likingPlace = ref(false);
const reviews = ref<Review[]>([]);
const reviewSort = ref<"latest" | "likes" | "rating">("latest");
const reviewsLoading = ref(false);
const reviewSubmitting = ref(false);
const reviewError = ref("");
const reviewForm = reactive({ rating: 5, content: "", password: "" });
const reviewModalOpen = ref(false);
const reviewModalMode = ref<"edit" | "delete">("edit");
const selectedReview = ref<Review | null>(null);
const reviewEdit = reactive({ rating: 5, content: "", password: "" });
const tagInput = ref("");
const tagSubmitting = ref(false);
const tagError = ref("");
const tagDeleteOpen = ref(false);
const tagToDelete = ref("");
const tagDeletePassword = ref("");
let loadSequence = 0;
let reviewLoadSequence = 0;

const gallery = computed(() => {
  if (!place.value) return [];
  const images = place.value.images.map((item) => mediaUrl(item.url)).filter(Boolean) as string[];
  const datasetImage = mediaUrl(place.value.primary_image_url || place.value.thumbnail_url);
  if (!images.length && datasetImage) images.push(datasetImage);
  return images;
});
const locationText = computed(() => {
  if (!place.value) return "";
  return [place.value.address, place.value.detail_address].filter(Boolean).join(" ") || "주소 정보 확인 중";
});
const bookmarked = computed(() => place.value ? bookmarks.has(place.value.id) : false);

function showNotice(message: string) {
  notice.value = message;
  window.setTimeout(() => (notice.value = ""), 2200);
}

async function recordViewOnce() {
  if (!place.value) return;
  const placeId = place.value.id;
  const key = "seoullo-viewed-place-ids";
  let ids: number[] = [];
  try { ids = JSON.parse(localStorage.getItem(key) || "[]"); } catch { ids = []; }
  if (ids.includes(placeId)) return;
  try {
    const result = await incrementPlaceView(placeId);
    if (place.value?.id === placeId) place.value.view_count = result.view_count;
    localStorage.setItem(key, JSON.stringify([...ids, placeId]));
  } catch { /* 조회 기록 실패는 상세 열람을 막지 않는다. */ }
}

async function loadReviews() {
  if (!place.value) return;
  const sequence = ++reviewLoadSequence;
  const placeId = place.value.id;
  const requestedSort = reviewSort.value;
  reviewsLoading.value = true;
  reviewError.value = "";
  try {
    const response = await getReviews(placeId, requestedSort);
    if (sequence === reviewLoadSequence && place.value?.id === placeId && reviewSort.value === requestedSort) {
      reviews.value = response.items;
    }
  }
  catch (caught) {
    if (sequence === reviewLoadSequence) reviewError.value = errorMessage(caught);
  }
  finally {
    if (sequence === reviewLoadSequence) reviewsLoading.value = false;
  }
}

async function refreshPlace() {
  const requestedId = props.id;
  const nextPlace = await getPlace(requestedId);
  if (props.id === requestedId) place.value = nextPlace;
}

async function load() {
  const sequence = ++loadSequence;
  const requestedId = props.id;
  loading.value = true;
  error.value = "";
  try {
    const nextPlace = await getPlace(requestedId);
    if (sequence !== loadSequence || props.id !== requestedId) return;
    place.value = nextPlace;
    activeImage.value = gallery.value[0] || "";
    await Promise.all([loadReviews(), recordViewOnce()]);
  } catch (caught) {
    if (sequence === loadSequence) error.value = errorMessage(caught);
  }
  finally {
    if (sequence === loadSequence) loading.value = false;
  }
}

function resetDetailState() {
  reviewLoadSequence += 1;
  place.value = null;
  reviews.value = [];
  activeImage.value = "";
  imageFailed.value = false;
  error.value = "";
  actionError.value = "";
  reviewError.value = "";
  tagError.value = "";
  deleteOpen.value = false;
  reviewModalOpen.value = false;
  tagDeleteOpen.value = false;
  selectedReview.value = null;
  tagInput.value = "";
}

function toggleBookmark() {
  if (!place.value) return;
  const saved = bookmarks.toggle(place.value.id);
  showNotice(saved ? "저장한 장소에 추가했어요." : "저장한 장소에서 삭제했어요.");
}

async function likePlace() {
  if (!place.value || likingPlace.value) return;
  likingPlace.value = true;
  try {
    const result = await togglePlaceLike(place.value.id);
    place.value.liked_by_me = result.liked;
    place.value.like_count = result.like_count;
  } catch (caught) { showNotice(errorMessage(caught)); }
  finally { likingPlace.value = false; }
}

function parsedTagInput(): string[] {
  return [...new Set(
    tagInput.value
      .split(/[,\s]+/)
      .map((value) => value.trim().replace(/^#/, ""))
      .filter(Boolean),
  )];
}

async function submitTags() {
  if (!place.value || tagSubmitting.value) return;
  const tags = parsedTagInput();
  tagError.value = "";
  if (!tags.length) { tagError.value = "추가할 태그를 입력해 주세요."; return; }
  if (tags.some((tag) => tag.length > 6)) { tagError.value = "태그는 6글자 이하로 입력해 주세요."; return; }
  tagSubmitting.value = true;
  try {
    place.value.tags = (await addPlaceTags(place.value.id, tags)).tags;
    tagInput.value = "";
    showNotice("태그를 추가했어요.");
  } catch (caught) { tagError.value = errorMessage(caught); }
  finally { tagSubmitting.value = false; }
}

function openTagDelete(tag: string) {
  tagToDelete.value = tag;
  tagDeletePassword.value = "";
  actionError.value = "";
  tagDeleteOpen.value = true;
}

async function confirmTagDelete() {
  if (!place.value || !tagDeletePassword.value || tagSubmitting.value) {
    actionError.value = "장소 등록 비밀번호를 입력해 주세요.";
    return;
  }
  tagSubmitting.value = true;
  actionError.value = "";
  try {
    place.value.tags = (
      await deletePlaceTag(place.value.id, tagToDelete.value, tagDeletePassword.value)
    ).tags;
    tagDeleteOpen.value = false;
    showNotice("태그를 삭제했어요.");
  } catch (caught) { actionError.value = errorMessage(caught); }
  finally { tagSubmitting.value = false; }
}

async function submitReview() {
  if (!place.value || reviewSubmitting.value) return;
  reviewError.value = "";
  if (!reviewForm.content.trim() || !reviewForm.password) {
    reviewError.value = "리뷰와 비밀번호를 입력해 주세요.";
    return;
  }
  reviewSubmitting.value = true;
  try {
    await createReview(place.value.id, { ...reviewForm, content: reviewForm.content.trim() });
    reviewForm.rating = 5; reviewForm.content = ""; reviewForm.password = "";
    await Promise.all([loadReviews(), refreshPlace()]);
    showNotice("별점 리뷰를 등록했어요.");
  } catch (caught) { reviewError.value = errorMessage(caught); }
  finally { reviewSubmitting.value = false; }
}

async function likeReview(review: Review) {
  try {
    const result = await toggleReviewLike(review.id);
    review.liked_by_me = result.liked;
    review.like_count = result.like_count;
  } catch (caught) { showNotice(errorMessage(caught)); }
}

function openReviewModal(review: Review, mode: "edit" | "delete") {
  selectedReview.value = review;
  reviewModalMode.value = mode;
  reviewEdit.rating = review.rating;
  reviewEdit.content = review.content;
  reviewEdit.password = "";
  actionError.value = "";
  reviewModalOpen.value = true;
}

async function confirmReviewAction() {
  if (!selectedReview.value || !reviewEdit.password) {
    actionError.value = "리뷰 등록 시 사용한 비밀번호를 입력해 주세요.";
    return;
  }
  reviewSubmitting.value = true;
  actionError.value = "";
  try {
    if (reviewModalMode.value === "edit") {
      await updateReview(selectedReview.value.id, reviewEdit);
    } else {
      await deleteReview(selectedReview.value.id, reviewEdit.password);
    }
    reviewModalOpen.value = false;
    await Promise.all([loadReviews(), refreshPlace()]);
    showNotice(reviewModalMode.value === "edit" ? "리뷰를 수정했어요." : "리뷰를 삭제했어요.");
  } catch (caught) { actionError.value = errorMessage(caught); }
  finally { reviewSubmitting.value = false; }
}

async function confirmDelete() {
  if (!deletePassword.value) { actionError.value = "등록할 때 사용한 비밀번호를 입력해 주세요."; return; }
  deleting.value = true; actionError.value = "";
  try { await deletePlace(props.id, deletePassword.value); router.replace({ name: "home" }); }
  catch (caught) { actionError.value = errorMessage(caught); }
  finally { deleting.value = false; }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function openMap() { router.push({ name: "map", query: { placeId: props.id } }); }
watch(reviewSort, loadReviews);
watch(
  () => props.id,
  () => {
    resetDetailState();
    window.scrollTo({ top: 0, behavior: "auto" });
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <main class="page-shell detail-page">
    <header class="detail-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="router.back()"><ArrowLeft :size="21" /></button>
      <RouterLink class="compact-brand" to="/">Seoullo</RouterLink>
      <button class="icon-button" :class="{ 'bookmark-active': bookmarked }" type="button" :aria-pressed="bookmarked" aria-label="북마크" @click="toggleBookmark"><Bookmark :size="20" :fill="bookmarked ? 'currentColor' : 'none'" /></button>
    </header>

    <div v-if="loading" class="detail-loading"><div class="skeleton detail-hero-skeleton" /><div class="skeleton skeleton-title" /><div class="skeleton skeleton-line" /></div>
    <section v-else-if="error" class="state-card error-state"><h2>장소를 찾을 수 없어요</h2><p>{{ error }}</p><RouterLink class="primary-button" to="/">홈으로 돌아가기</RouterLink></section>

    <template v-else-if="place">
      <section class="detail-layout">
        <div class="detail-gallery">
          <div class="detail-main-image">
            <img v-if="activeImage && !imageFailed" :src="activeImage" :alt="`${place.title} 이미지`" @error="imageFailed = true" />
            <div v-else class="image-placeholder"><Image :size="48" /><span>Seoullo</span></div>
            <span class="place-category">{{ place.content_type }}</span>
          </div>
          <div v-if="gallery.length > 1" class="thumbnail-row"><button v-for="image in gallery" :key="image" type="button" :class="{ active: activeImage === image }" @click="activeImage = image; imageFailed = false"><img :src="image" alt="장소 이미지 미리보기" /></button></div>
        </div>

        <div class="detail-summary">
          <div class="detail-badges"><span>{{ place.source === 'dataset' ? '한국관광공사 제공' : 'Seoullo 사용자 발견' }}</span></div>
          <h1>{{ place.title }}</h1>
          <p class="detail-address"><MapPin :size="18" />{{ locationText }}</p>
          <div class="detail-stats">
            <span><Star :size="18" fill="currentColor" /><strong>{{ place.average_rating.toFixed(1) }}</strong><small>{{ place.review_count }}개 리뷰</small></span>
            <span><Heart :size="18" :fill="place.liked_by_me ? 'currentColor' : 'none'" /><strong>{{ place.like_count.toLocaleString() }}</strong><small>좋아요</small></span>
            <span><Eye :size="18" /><strong>{{ place.view_count.toLocaleString() }}</strong><small>조회</small></span>
          </div>
          <div class="detail-tag-editor">
            <div v-if="place.tags.length" class="tag-row detail-tags">
              <span v-for="tag in place.tags" :key="tag">#{{ tag }}<button v-if="place.source === 'user'" type="button" :aria-label="`${tag} 태그 삭제`" @click="openTagDelete(tag)"><X :size="11" /></button></span>
            </div>
            <form class="tag-add-form" @submit.prevent="submitTags">
              <input v-model="tagInput" type="text" maxlength="80" aria-label="장소 태그 추가" placeholder="#숨은명소, #산책" />
              <button type="submit" :disabled="tagSubmitting"><Plus :size="15" />{{ tagSubmitting ? '추가 중' : '태그 추가' }}</button>
            </form>
            <small>쉼표나 띄어쓰기로 여러 개 입력 · 태그당 6글자 이하</small>
            <p v-if="tagError" class="field-error">{{ tagError }}</p>
          </div>
          <div class="detail-primary-actions">
            <button class="primary-button" :class="{ liked: place.liked_by_me }" type="button" :disabled="likingPlace" @click="likePlace"><Heart :size="18" :fill="place.liked_by_me ? 'currentColor' : 'none'" />{{ place.liked_by_me ? '좋아요 취소' : '좋아요' }}</button>
            <button class="secondary-button" :class="{ 'bookmark-active': bookmarked }" type="button" @click="toggleBookmark"><Bookmark :size="18" :fill="bookmarked ? 'currentColor' : 'none'" />{{ bookmarked ? '저장됨' : '저장' }}</button>
          </div>
          <RouterLink class="emotion-checkin-link" :to="`/places/${place.id}/checkin`"><Sparkles :size="17" /><span><strong>다녀왔어요</strong><small>여행 후 감정 체크인</small></span><ChevronRight :size="18" /></RouterLink>
          <div v-if="place.source === 'user'" class="owner-actions"><RouterLink class="text-button" :to="`/places/${place.id}/edit`"><Edit3 :size="16" />장소 수정</RouterLink><button class="text-button danger" type="button" @click="deleteOpen = true"><Trash2 :size="16" />삭제</button></div>
        </div>
      </section>

      <section class="detail-content-grid">
        <article class="detail-card description-card">
          <span class="section-eyebrow">ABOUT</span><h2>장소 정보</h2>
          <p v-if="place.description">{{ place.description }}</p><p v-else class="muted-copy">제공된 상세 설명이 없습니다. 위치와 연락처를 확인한 후 방문을 계획해 보세요.</p>
          <dl class="info-list"><div v-if="place.telephone"><dt><Phone :size="17" />전화</dt><dd>{{ place.telephone }}</dd></div><div><dt><Navigation :size="17" />좌표</dt><dd>{{ place.latitude.toFixed(5) }}, {{ place.longitude.toFixed(5) }}</dd></div><div v-if="place.zipcode"><dt><MapPin :size="17" />우편번호</dt><dd>{{ place.zipcode }}</dd></div></dl>
        </article>
        <button class="detail-card map-preview" type="button" @click="openMap"><span class="map-grid" aria-hidden="true" /><span class="map-pin-large"><MapPin :size="27" /></span><span class="map-preview-copy"><strong>지도에서 위치 확인</strong><small>{{ locationText }}</small></span><ChevronRight :size="20" /></button>

        <article class="detail-card review-preview">
          <div class="review-section-header"><div><span class="section-eyebrow">REVIEWS</span><h2>방문자 별점 리뷰</h2></div><label class="sort-select"><select v-model="reviewSort" aria-label="리뷰 정렬"><option value="latest">최신순</option><option value="likes">좋아요순</option><option value="rating">별점순</option></select></label></div>
          <form class="review-form" @submit.prevent="submitReview">
            <div class="star-picker" role="radiogroup" aria-label="별점"><button v-for="score in 5" :key="score" type="button" :class="{ active: score <= reviewForm.rating }" :aria-label="`${score}점`" @click="reviewForm.rating = score"><Star :size="25" :fill="score <= reviewForm.rating ? 'currentColor' : 'none'" /></button><strong>{{ reviewForm.rating }}점</strong></div>
            <label class="field-label">리뷰<textarea v-model="reviewForm.content" maxlength="1000" placeholder="이 장소에서의 경험을 들려주세요." required /></label>
            <div class="review-form-footer"><label class="field-label">수정·삭제 비밀번호<input v-model="reviewForm.password" type="password" maxlength="100" autocomplete="new-password" placeholder="비밀번호" required /></label><button class="primary-button" type="submit" :disabled="reviewSubmitting">{{ reviewSubmitting ? '등록 중…' : '리뷰 등록' }}</button></div>
            <p v-if="reviewError" class="field-error">{{ reviewError }}</p><small class="review-policy">리뷰는 한 개만 작성할 수 있습니다.</small>
          </form>

          <div v-if="reviewsLoading" class="review-loading">리뷰를 불러오는 중…</div>
          <div v-else-if="!reviews.length" class="review-empty"><Star :size="31" /><strong>첫 리뷰를 기다리고 있어요</strong><p>이 장소를 다녀왔다면 첫 경험을 남겨주세요.</p></div>
          <div v-else class="review-list">
            <article v-for="review in reviews" :key="review.id" class="review-card">
              <div class="review-card-head"><span class="review-stars"><Star v-for="score in 5" :key="score" :size="15" :fill="score <= review.rating ? 'currentColor' : 'none'" /></span><time :datetime="review.created_at">{{ formatDate(review.created_at) }}</time></div>
              <p>{{ review.content }}</p>
              <div class="review-card-actions"><button class="review-like-button" :class="{ liked: review.liked_by_me }" type="button" @click="likeReview(review)"><ThumbsUp :size="15" :fill="review.liked_by_me ? 'currentColor' : 'none'" />{{ review.like_count }}</button><span /><button type="button" @click="openReviewModal(review, 'edit')">수정</button><button type="button" class="danger" @click="openReviewModal(review, 'delete')">삭제</button></div>
            </article>
          </div>
        </article>
      </section>
    </template>

    <BaseModal :open="deleteOpen" title="장소를 삭제할까요?" @close="deleteOpen = false"><p class="modal-description">삭제하면 등록한 이미지와 태그도 함께 사라집니다.</p><label class="field-label">등록 비밀번호<input v-model="deletePassword" type="password" autocomplete="current-password" placeholder="비밀번호 입력" /></label><p v-if="actionError" class="field-error">{{ actionError }}</p><template #footer><button class="secondary-button" type="button" @click="deleteOpen = false">취소</button><button class="danger-button" type="button" :disabled="deleting" @click="confirmDelete">{{ deleting ? '삭제 중…' : '삭제하기' }}</button></template></BaseModal>

    <BaseModal :open="reviewModalOpen" :title="reviewModalMode === 'edit' ? '리뷰 수정' : '리뷰 삭제'" @close="reviewModalOpen = false">
      <div v-if="reviewModalMode === 'edit'" class="review-modal-form"><div class="star-picker"><button v-for="score in 5" :key="score" type="button" :class="{ active: score <= reviewEdit.rating }" @click="reviewEdit.rating = score"><Star :size="23" :fill="score <= reviewEdit.rating ? 'currentColor' : 'none'" /></button></div><label class="field-label">리뷰<textarea v-model="reviewEdit.content" maxlength="1000" /></label></div>
      <p v-else class="modal-description">삭제한 리뷰는 복구할 수 없습니다.</p>
      <label class="field-label">등록 비밀번호<input v-model="reviewEdit.password" type="password" autocomplete="current-password" placeholder="비밀번호 입력" /></label><p v-if="actionError" class="field-error">{{ actionError }}</p>
      <template #footer><button class="secondary-button" type="button" @click="reviewModalOpen = false">취소</button><button :class="reviewModalMode === 'delete' ? 'danger-button' : 'primary-button'" type="button" :disabled="reviewSubmitting" @click="confirmReviewAction">{{ reviewModalMode === 'edit' ? '수정하기' : '삭제하기' }}</button></template>
    </BaseModal>
    <BaseModal :open="tagDeleteOpen" title="태그를 삭제할까요?" @close="tagDeleteOpen = false">
      <p class="modal-description">#{{ tagToDelete }} 태그를 삭제하려면 장소 등록 비밀번호를 입력해 주세요.</p>
      <label class="field-label">등록 비밀번호<input v-model="tagDeletePassword" type="password" autocomplete="current-password" placeholder="비밀번호 입력" /></label>
      <p v-if="actionError" class="field-error">{{ actionError }}</p>
      <template #footer><button class="secondary-button" type="button" @click="tagDeleteOpen = false">취소</button><button class="danger-button" type="button" :disabled="tagSubmitting" @click="confirmTagDelete">{{ tagSubmitting ? '삭제 중…' : '삭제하기' }}</button></template>
    </BaseModal>
    <Transition name="toast"><div v-if="notice" class="toast">{{ notice }}</div></Transition>
  </main>
</template>
