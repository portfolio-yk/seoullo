<script setup lang="ts">
import { X } from "lucide-vue-next";
import { onMounted, onUnmounted } from "vue";

const props = withDefaults(
  defineProps<{ open: boolean; title: string; closeLabel?: string }>(),
  { closeLabel: "닫기" },
);
const emit = defineEmits<{ close: [] }>();

function handleKey(event: KeyboardEvent) {
  if (props.open && event.key === "Escape") emit("close");
}

onMounted(() => window.addEventListener("keydown", handleKey));
onUnmounted(() => window.removeEventListener("keydown", handleKey));
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-backdrop" role="presentation" @click.self="emit('close')">
        <section class="modal-sheet" role="dialog" aria-modal="true" :aria-label="title">
          <header class="modal-header">
            <h2>{{ title }}</h2>
            <button class="icon-button" type="button" :aria-label="closeLabel" @click="emit('close')">
              <X :size="20" />
            </button>
          </header>
          <div class="modal-content"><slot /></div>
          <footer v-if="$slots.footer" class="modal-footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

