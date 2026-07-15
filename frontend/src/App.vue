<script setup lang="ts">
import { RouterView } from "vue-router";
import BottomNav from "./components/BottomNav.vue";
import ChatWidget from "./components/ChatWidget.vue";
</script>

<template>
  <div class="app-root">
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
    <ChatWidget />
    <BottomNav />
  </div>
</template>
