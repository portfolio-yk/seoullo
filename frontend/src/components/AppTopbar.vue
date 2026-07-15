<script setup lang="ts">
import { Bookmark, Compass, Search } from "lucide-vue-next";
import { useRouter } from "vue-router";

const router = useRouter();

function openSearch() {
  router.push({ name: "home", query: { focus: "search" } });
}
</script>

<template>
  <header class="topbar">
    <RouterLink class="brand" to="/" aria-label="Seoullo 홈">
      <span class="brand-symbol"><Compass :size="21" stroke-width="2.6" /></span>
      <span>Seoullo</span>
    </RouterLink>
    <nav class="desktop-nav" aria-label="주요 메뉴">
      <RouterLink to="/">장소 탐색</RouterLink>
      <RouterLink to="/emotions">마음 추천</RouterLink>
    </nav>
    <div class="top-actions">
      <button class="icon-button" type="button" aria-label="검색" @click="openSearch">
        <Search :size="20" />
      </button>
      <RouterLink class="icon-button" to="/bookmarks" aria-label="저장한 장소">
        <Bookmark :size="20" />
      </RouterLink>
    </div>
  </header>
</template>
