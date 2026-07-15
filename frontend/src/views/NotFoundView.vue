<script setup lang="ts">
import { Compass } from "lucide-vue-next";
</script>

<template>
  <main class="page-shell centered-page">
    <div class="not-found-mark"><Compass :size="38" /></div>
    <span class="section-eyebrow">404</span>
    <h1>길을 잠시 잃었어요</h1>
    <p>요청한 페이지를 찾을 수 없습니다.</p>
    <RouterLink class="primary-button" to="/">서울 탐색으로 돌아가기</RouterLink>
  </main>
</template>

