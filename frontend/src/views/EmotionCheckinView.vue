<script setup lang="ts">
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Footprints,
  LoaderCircle,
  MapPin,
  Sparkles,
} from "lucide-vue-next";
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { createEmotionCheckin, errorMessage, getPlace } from "../api/client";
import type { EmotionCheckinResponse, PlaceDetail } from "../types/place";

const props = defineProps<{ id: string }>();
const router = useRouter();
const place = ref<PlaceDetail | null>(null);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const result = ref<EmotionCheckinResponse | null>(null);

const moods = ["지침", "불안", "답답함", "설렘", "외로움", "평온함"];
const afterFeelings = ["회복", "해방", "활력", "위로", "몰입", "설렘"];
const styles = ["조용히 혼자", "가볍게 산책", "새로운 자극", "누군가와 함께"];
const intensityLabels = ["아주 약함", "약함", "보통", "강함", "아주 강함"];

const form = reactive({
  beforeEmotion: "",
  beforeIntensity: 3,
  afterEmotion: "",
  afterIntensity: 4,
  travelStyle: "",
});

async function load() {
  try {
    place.value = await getPlace(props.id);
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

async function submit() {
  if (!form.beforeEmotion || !form.afterEmotion || !form.travelStyle) {
    error.value = "방문 전 감정, 방문 후 감정, 여행 스타일을 모두 선택해 주세요.";
    return;
  }
  submitting.value = true;
  error.value = "";
  try {
    result.value = await createEmotionCheckin({
      place_id: Number(props.id),
      before_emotion: form.beforeEmotion,
      before_intensity: form.beforeIntensity,
      after_emotion: form.afterEmotion,
      after_intensity: form.afterIntensity,
      travel_style: form.travelStyle,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (caught) {
    error.value = errorMessage(caught);
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <main class="checkin-page">
    <header class="checkin-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="router.back()"><ArrowLeft :size="21" /></button>
      <RouterLink class="compact-brand" to="/">Seoullo</RouterLink>
      <span class="checkin-top-label">POST TRIP</span>
    </header>

    <div v-if="loading" class="checkin-loading"><LoaderCircle class="spin" :size="29" /><p>장소를 불러오고 있어요</p></div>
    <section v-else-if="error && !place" class="state-card error-state"><h2>체크인을 시작할 수 없어요</h2><p>{{ error }}</p><button class="primary-button" type="button" @click="router.back()">돌아가기</button></section>

    <section v-else-if="result && place" class="checkin-success">
      <div class="checkin-success-icon"><CheckCircle2 :size="38" /></div>
      <span class="section-eyebrow">EMOTION UPDATED</span>
      <h1>여행의 감정이<br />추천 데이터에 반영됐어요</h1>
      <p><strong>{{ place.title }}</strong>의 {{ form.beforeEmotion }}·{{ form.afterEmotion }}·{{ form.travelStyle }} 수치가 각각 1씩 증가했고 Pinecone 벡터도 갱신됐습니다.</p>
      <div class="checkin-success-tags"><span>#{{ form.beforeEmotion }}</span><span>#{{ form.afterEmotion }}</span><span>#{{ form.travelStyle }}</span></div>
      <div class="checkin-success-actions"><RouterLink class="secondary-button" :to="`/places/${place.id}`">장소로 돌아가기</RouterLink><RouterLink class="primary-button" to="/emotions"><Sparkles :size="17" />새 추천 받기</RouterLink></div>
    </section>

    <template v-else-if="place">
      <section class="checkin-hero">
        <span class="section-eyebrow">POST TRIP CHECK-IN</span>
        <h1>다녀온 뒤의 마음을<br />들려주세요</h1>
        <p>선택한 감정은 이 장소의 추천 데이터에 한 표씩 더해져요.</p>
        <RouterLink class="checkin-place-chip" :to="`/places/${place.id}`"><MapPin :size="17" /><span><strong>{{ place.title }}</strong><small>{{ place.address || place.content_type }}</small></span><ChevronRight :size="17" /></RouterLink>
      </section>

      <form class="checkin-form" @submit.prevent="submit">
        <section class="checkin-card">
          <div class="checkin-card-heading"><span>01</span><div><h2>가기 전에는 어떤 마음이었나요?</h2><p>가장 가까웠던 감정 하나를 골라주세요.</p></div></div>
          <div class="checkin-choice-grid" role="radiogroup" aria-label="방문 전 감정"><button v-for="mood in moods" :key="mood" type="button" :class="{ active: form.beforeEmotion === mood }" :aria-pressed="form.beforeEmotion === mood" @click="form.beforeEmotion = mood">{{ mood }}</button></div>
          <div class="checkin-scale"><strong>감정 강도</strong><div role="radiogroup" aria-label="방문 전 감정 강도"><button v-for="score in 5" :key="score" type="button" :class="{ active: form.beforeIntensity === score }" :aria-label="`${score}점 ${intensityLabels[score - 1]}`" @click="form.beforeIntensity = score">{{ score }}</button></div><small>{{ intensityLabels[form.beforeIntensity - 1] }}</small></div>
        </section>

        <section class="checkin-card">
          <div class="checkin-card-heading"><span>02</span><div><h2>다녀온 뒤에는 무엇이 남았나요?</h2><p>여행 후 가장 크게 느낀 감정을 골라주세요.</p></div></div>
          <div class="checkin-choice-grid" role="radiogroup" aria-label="방문 후 감정"><button v-for="feeling in afterFeelings" :key="feeling" type="button" :class="{ active: form.afterEmotion === feeling }" :aria-pressed="form.afterEmotion === feeling" @click="form.afterEmotion = feeling">{{ feeling }}</button></div>
          <div class="checkin-scale"><strong>감정 강도</strong><div role="radiogroup" aria-label="방문 후 감정 강도"><button v-for="score in 5" :key="score" type="button" :class="{ active: form.afterIntensity === score }" :aria-label="`${score}점 ${intensityLabels[score - 1]}`" @click="form.afterIntensity = score">{{ score }}</button></div><small>{{ intensityLabels[form.afterIntensity - 1] }}</small></div>
        </section>

        <section class="checkin-card">
          <div class="checkin-card-heading"><span>03</span><div><h2>이번 여행은 어떤 스타일이었나요?</h2><p>장소를 즐긴 방식 하나를 선택해 주세요.</p></div></div>
          <div class="checkin-style-list" role="radiogroup" aria-label="여행 스타일"><button v-for="style in styles" :key="style" type="button" :class="{ active: form.travelStyle === style }" :aria-pressed="form.travelStyle === style" @click="form.travelStyle = style"><Footprints :size="17" /><span>{{ style }}</span><CheckCircle2 :size="17" /></button></div>
        </section>

        <p v-if="error" class="form-error"><span>{{ error }}</span></p>
        <div class="checkin-submit-bar"><button class="primary-button" type="submit" :disabled="submitting"><LoaderCircle v-if="submitting" class="spin" :size="18" /><Sparkles v-else :size="18" />{{ submitting ? '감정 벡터 반영 중…' : '감정 체크인 완료' }}</button></div>
      </form>
    </template>
  </main>
</template>
