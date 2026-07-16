<script setup lang="ts">
import { Plus } from "lucide-vue-next";
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import ChatWidget from "./components/ChatWidget.vue";

const route = useRoute();
const showLaunchers = computed(() => ["home", "place-detail"].includes(String(route.name)));
</script>

<template>
  <div class="app-root">
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
    <RouterLink v-if="showLaunchers" class="place-create-launcher" to="/places/new" aria-label="새 장소 등록" title="새 장소 등록">
      <Plus :size="25" stroke-width="2.8" />
    </RouterLink>
    <ChatWidget v-if="showLaunchers" />
  </div>
</template>
