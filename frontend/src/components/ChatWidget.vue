<script setup lang="ts">
import { nextTick, ref } from "vue";
import {
  ChevronRight,
  LoaderCircle,
  MapPin,
  MessageCircle,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-vue-next";
import { RouterLink } from "vue-router";
import { errorMessage, mediaUrl, sendChatMessage } from "../api/client";
import type { ChatHistoryMessage, ChatRecommendation, ChatSource } from "../types/place";

interface UiMessage extends ChatHistoryMessage {
  sources?: ChatSource[];
  recommendations?: ChatRecommendation[];
  fallback?: boolean;
  isGreeting?: boolean;
}

const greeting = "서울에서 어디로 갈지 고민되시나요? Seoullo의 관광 데이터에서 장소를 찾아드릴게요.";
const suggestions = ["종로구 관광지 추천", "서울 축제 장소 알려줘", "서울 야경 명소 알려줘"];

const isOpen = ref(false);
const isSending = ref(false);
const draft = ref("");
const textarea = ref<HTMLTextAreaElement | null>(null);
const messageList = ref<HTMLElement | null>(null);
const messages = ref<UiMessage[]>([{ role: "assistant", content: greeting, isGreeting: true }]);

async function scrollToLatest() {
  await nextTick();
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: "smooth" });
}

async function openChat() {
  isOpen.value = true;
  await nextTick();
  textarea.value?.focus();
}

function clearChat() {
  messages.value = [{ role: "assistant", content: greeting, isGreeting: true }];
  draft.value = "";
}

function recommendationFor(message: UiMessage, placeId: number) {
  return message.recommendations?.find((item) => item.id === placeId);
}

async function submit(value = draft.value) {
  const message = value.trim();
  if (!message || isSending.value) return;

  const history = messages.value
    .filter((item) => !item.isGreeting)
    .map(({ role, content }) => ({ role, content }))
    .slice(-10);
  messages.value.push({ role: "user", content: message });
  draft.value = "";
  isSending.value = true;
  await scrollToLatest();

  try {
    const response = await sendChatMessage(message, history);
    messages.value.push({
      role: "assistant",
      content: response.answer,
      sources: response.sources,
      recommendations: response.recommendations,
      fallback: response.fallback,
    });
  } catch (error) {
    messages.value.push({
      role: "assistant",
      content: `답변을 불러오지 못했어요. ${errorMessage(error)}`,
    });
  } finally {
    isSending.value = false;
    await scrollToLatest();
    textarea.value?.focus();
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    void submit();
  }
}
</script>

<template>
  <button
    v-if="!isOpen"
    class="chat-launcher"
    type="button"
    aria-label="Seoullo 여행 챗봇 열기"
    @click="openChat"
  >
    <Sparkles :size="15" />
    <MessageCircle :size="24" />
  </button>

  <Transition name="chat-panel">
    <section v-if="isOpen" class="chat-widget" role="dialog" aria-modal="true" aria-label="Seoullo 여행 챗봇">
      <header class="chat-widget-header">
        <div class="chat-agent-mark"><Sparkles :size="19" /></div>
        <div>
          <strong>Seoullo AI</strong>
          <span><i /> 관광 데이터 기반 안내</span>
        </div>
        <button type="button" aria-label="대화 내용 지우기" title="대화 내용 지우기" @click="clearChat">
          <Trash2 :size="18" />
        </button>
        <button type="button" aria-label="챗봇 닫기" @click="isOpen = false">
          <X :size="20" />
        </button>
      </header>

      <div ref="messageList" class="chat-messages" aria-live="polite">
        <article
          v-for="(message, index) in messages"
          :key="`${message.role}-${index}`"
          class="chat-message-row"
          :class="`is-${message.role}`"
        >
          <div v-if="message.role === 'assistant'" class="chat-mini-mark"><Sparkles :size="13" /></div>
          <div class="chat-message-content">
            <p class="chat-bubble">{{ message.content }}</p>
            <span v-if="message.fallback" class="chat-fallback-note">조건을 바꿔 다시 질문해 보세요</span>
            <div v-if="message.sources?.length" class="chat-sources">
              <span class="chat-source-label">답변에 사용한 장소</span>
              <RouterLink
                v-for="source in message.sources"
                :key="source.id"
                class="chat-source-card"
                :to="`/places/${source.id}`"
                @click="isOpen = false"
              >
                <img v-if="mediaUrl(source.image_url)" :src="mediaUrl(source.image_url)!" :alt="source.title" />
                <div v-else class="chat-source-placeholder"><MapPin :size="19" /></div>
                <div>
                  <small>{{ source.content_type }} · {{ source.source === 'dataset' ? '관광 데이터' : '커뮤니티' }}</small>
                  <strong>{{ source.title }}</strong>
                  <span><MapPin :size="11" /> {{ source.address || '주소 정보 없음' }}</span>
                  <p v-if="recommendationFor(message, source.id)" class="chat-source-reason">
                    {{ recommendationFor(message, source.id)?.reason }}
                  </p>
                  <div
                    v-if="recommendationFor(message, source.id)?.emotion_categories.length"
                    class="chat-emotion-tags"
                  >
                    <em
                      v-for="keyword in recommendationFor(message, source.id)?.emotion_categories"
                      :key="keyword"
                    >{{ keyword }}</em>
                  </div>
                </div>
                <ChevronRight :size="17" />
              </RouterLink>
            </div>
          </div>
        </article>

        <article v-if="isSending" class="chat-message-row is-assistant">
          <div class="chat-mini-mark"><Sparkles :size="13" /></div>
          <p class="chat-bubble chat-thinking"><LoaderCircle :size="15" class="spin" /> 장소를 찾고 있어요</p>
        </article>
      </div>

      <div v-if="messages.length === 1" class="chat-suggestions">
        <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="submit(suggestion)">
          {{ suggestion }}
        </button>
      </div>

      <form class="chat-composer" @submit.prevent="submit()">
        <textarea
          ref="textarea"
          v-model="draft"
          rows="1"
          maxlength="500"
          aria-label="여행 질문 입력"
          placeholder="서울 여행지를 물어보세요"
          @keydown="handleKeydown"
        />
        <button type="submit" :disabled="!draft.trim() || isSending" aria-label="질문 보내기">
          <Send :size="18" />
        </button>
      </form>
      <p class="chat-disclaimer">AI 답변은 제공된 장소 데이터를 기준으로 하며 실제 정보와 다를 수 있어요.</p>
    </section>
  </Transition>
</template>
