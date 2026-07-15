<template>
  <div class="place-grid" aria-label="장소 정보를 불러오는 중">
    <article v-for="item in 6" :key="item" class="place-card skeleton-card">
      <div class="skeleton skeleton-media" />
      <div class="place-card-body">
        <div class="skeleton skeleton-title" />
        <div class="skeleton skeleton-line" />
        <div class="skeleton skeleton-line short" />
      </div>
    </article>
  </div>
</template>

