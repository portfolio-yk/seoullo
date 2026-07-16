<script setup lang="ts">
import {
  ArrowLeft, ArrowRight, Check, Eye, Heart, Image, MapPin, RotateCcw, Sparkles, Star,
} from "lucide-vue-next";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { errorMessage, getEmotionRecommendations, mediaUrl } from "../api/client";
import { useEmotionRecommendationStore, type EmotionGroupKey } from "../stores/emotionRecommendation";

const router = useRouter();
const recommendationStore = useEmotionRecommendationStore();
const { step, selected, result } = storeToRefs(recommendationStore);
const loading = ref(false);
const error = ref("");

const steps: { key: EmotionGroupKey; eyebrow: string; title: string; description: string; options: { label: string; hint: string }[] }[] = [
  {
    key: "mood", eyebrow: "NOW", title: "지금 마음은 어떤가요?", description: "현재 마음과 가까운 표현을 모두 선택해 주세요.",
    options: [
      { label: "지침", hint: "충전이 필요해요" }, { label: "불안", hint: "마음을 가라앉히고 싶어요" },
      { label: "답답함", hint: "탁 트인 곳이 필요해요" }, { label: "설렘", hint: "좋은 기분을 이어가고 싶어요" },
      { label: "외로움", hint: "따뜻한 온기가 필요해요" }, { label: "평온함", hint: "잔잔한 하루를 원해요" },
    ],
  },
  {
    key: "afterFeeling", eyebrow: "AFTER", title: "여행 뒤 어떤 마음이고 싶나요?", description: "이번 서울 여행에서 얻고 싶은 감정을 모두 골라 주세요.",
    options: [
      { label: "회복", hint: "다시 힘을 채우기" }, { label: "해방", hint: "복잡한 생각 내려놓기" },
      { label: "활력", hint: "몸과 마음 깨우기" }, { label: "위로", hint: "다정한 안정감 얻기" },
      { label: "몰입", hint: "한 가지에 깊이 빠지기" }, { label: "설렘", hint: "새로운 기대 만나기" },
    ],
  },
  {
    key: "style", eyebrow: "STYLE", title: "어떻게 여행하고 싶나요?", description: "오늘 가장 편안한 여행 방식을 선택해 주세요.",
    options: [
      { label: "조용히 혼자", hint: "나만의 속도로" }, { label: "가볍게 산책", hint: "부담 없이 천천히" },
      { label: "새로운 자극", hint: "낯선 장면과 경험" }, { label: "누군가와 함께", hint: "좋은 순간을 나누기" },
    ],
  },
];

const current = computed(() => steps[step.value]);
const currentSelection = computed(() => selected.value[current.value.key]);

function toggle(keyword: string) {
  error.value = "";
  const values = selected.value[current.value.key];
  if (current.value.key === "style") {
    values.splice(0, values.length, keyword);
    return;
  }
  const index = values.indexOf(keyword);
  if (index >= 0) values.splice(index, 1); else values.push(keyword);
}

async function next() {
  if (!currentSelection.value.length) { error.value = "하나 이상의 키워드를 선택해 주세요."; return; }
  if (step.value < steps.length - 1) { step.value += 1; error.value = ""; return; }
  loading.value = true; error.value = "";
  try {
    result.value = await getEmotionRecommendations({
      mood: selected.value.mood,
      afterFeeling: selected.value.afterFeeling,
      style: selected.value.style,
    });
  } catch (caught) { error.value = errorMessage(caught); }
  finally { loading.value = false; }
}

function restart() {
  recommendationStore.reset();
  error.value = "";
}

function groupLabel(group: string) {
  return group === "mood" ? "지금" : group === "afterFeeling" ? "기대" : "스타일";
}
</script>

<template>
  <main class="emotion-page">
    <header class="emotion-topbar">
      <button class="icon-button" type="button" aria-label="뒤로 가기" @click="result ? router.back() : step > 0 ? step-- : router.back()"><ArrowLeft :size="21" /></button>
      <RouterLink class="compact-brand" to="/">Seoullo</RouterLink>
      <button v-if="result" class="icon-button" type="button" aria-label="감정 선택 다시 하기" @click="restart"><RotateCcw :size="19" /></button><span v-else class="emotion-step-count">{{ step + 1 }}/3</span>
    </header>

    <section v-if="!result" class="emotion-question-shell">
      <div class="emotion-progress"><span v-for="index in 3" :key="index" :class="{ active: index - 1 <= step }" /></div>
      <div class="emotion-question-copy"><span class="section-eyebrow">{{ current.eyebrow }}</span><h1>{{ current.title }}</h1><p>{{ current.description }}</p></div>
      <div class="emotion-options">
        <button v-for="option in current.options" :key="option.label" type="button" :class="{ active: currentSelection.includes(option.label) }" :aria-pressed="currentSelection.includes(option.label)" @click="toggle(option.label)">
          <span class="emotion-option-check"><Check :size="15" /></span><span><strong>{{ option.label }}</strong><small>{{ option.hint }}</small></span>
        </button>
      </div>
      <p v-if="error" class="emotion-error">{{ error }}</p>
      <div class="emotion-selection-summary"><span v-for="keyword in currentSelection" :key="keyword">#{{ keyword }}</span></div>
      <button class="emotion-next-button" type="button" :disabled="loading" @click="next"><Sparkles v-if="step === 2" :size="18" /><span>{{ loading ? '6,518곳을 비교하는 중…' : step === 2 ? '나와 맞는 장소 찾기' : '다음 질문' }}</span><ArrowRight v-if="!loading" :size="18" /></button>
    </section>

    <section v-else class="emotion-results-shell">
      <div class="emotion-results-heading"><span class="section-eyebrow">YOUR SEOUL</span><h1>지금 마음에 가까운<br />서울 5곳이에요</h1><div class="emotion-query-tags"><span v-for="keyword in [...selected.mood, ...selected.afterFeeling, ...selected.style]" :key="keyword">#{{ keyword }}</span></div></div>
      <div class="emotion-result-list">
        <article v-for="item in result.items" :key="item.place.id" class="emotion-result-card">
          <RouterLink :to="`/places/${item.place.id}`" class="emotion-result-main">
            <div class="emotion-rank"><strong>{{ item.rank }}</strong><small>MATCH</small></div>
            <div class="emotion-result-image"><img v-if="mediaUrl(item.place.image_url)" :src="mediaUrl(item.place.image_url) || ''" :alt="`${item.place.title} 이미지`" /><span v-else><Image :size="28" /></span><b>{{ Math.round(item.similarity * 100) }}%</b></div>
            <div class="emotion-result-copy"><span>{{ item.place.content_type }}</span><h2>{{ item.place.title }}</h2><p><MapPin :size="14" />{{ item.place.address || '주소 정보 확인 중' }}</p><div class="emotion-place-meta"><span><Star :size="14" fill="currentColor" />{{ item.place.average_rating.toFixed(1) }}</span><span><Heart :size="14" />{{ item.place.like_count.toLocaleString() }}</span><span><Eye :size="14" />{{ item.place.view_count.toLocaleString() }}</span></div></div>
          </RouterLink>
          <div class="emotion-reason">
            <span><Sparkles :size="13" />{{ item.reason_source === 'openai' ? 'AI 추천 이유' : '감정 매칭 이유' }}</span>
            <p>{{ item.reason }}</p>
          </div>
          <div class="emotion-match-row"><span v-for="match in item.matched_keywords" :key="`${match.group}-${match.keyword}`"><small>{{ groupLabel(match.group) }}</small>{{ match.keyword }} · {{ match.value }}</span></div>
        </article>
      </div>
      <div class="emotion-result-actions"><button class="secondary-button" type="button" @click="restart"><RotateCcw :size="17" />다시 선택</button><RouterLink class="primary-button" :to="{ path: '/map', query: { ids: result.items.map((item) => item.place.id).join(',') } }">지도에서 보기<MapPin :size="17" /></RouterLink></div>
    </section>
  </main>
</template>
