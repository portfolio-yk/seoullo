<script setup lang="ts">
import { Bookmark, Home, Plus, Search, UserRound } from "lucide-vue-next";
</script>

<template>
  <nav class="bottom-nav" aria-label="하단 메뉴">
    <RouterLink to="/" class="bottom-nav-item">
      <Home :size="21" />
      <span>홈</span>
    </RouterLink>
    <RouterLink :to="{ name: 'home', query: { focus: 'search' } }" class="bottom-nav-item">
      <Search :size="21" />
      <span>검색</span>
    </RouterLink>
    <RouterLink to="/places/new" class="bottom-nav-create" aria-label="새 장소 등록">
      <Plus :size="25" stroke-width="2.8" />
    </RouterLink>
    <RouterLink to="/bookmarks" class="bottom-nav-item">
      <Bookmark :size="21" />
      <span>저장</span>
    </RouterLink>
    <button class="bottom-nav-item" type="button" disabled title="마이 메뉴는 준비 중입니다">
      <UserRound :size="21" />
      <span>마이</span>
    </button>
  </nav>
</template>
