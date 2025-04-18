<template>
  <div class="indicator-row">
    <div class="indicator" ref="redIndicatorEl">
      <img src="@/assets/red.svg" alt="red" class="indicator-icon" />
      <span class="count">{{ redCount }}</span>
    </div>
    <div class="indicator" ref="yellowIndicatorEl">
      <img src="@/assets/yellow.svg" alt="yellow" class="indicator-icon" />
      <span class="count">{{ yellowCount }}</span>
    </div>
    <button class="regenerate-button" @click="onRegenerate">
      <img src="@/assets/regenerate.svg" alt="regenerate" class="regenerate-icon" />
      <span>Regenerate</span>
    </button>
  </div>
</template>

<script>
export default {
  name: 'IndicatorRow',
  props: {
    redCount: {
      type: Number,
      default: 0
    },
    yellowCount: {
      type: Number,
      default: 0
    }
  },
  watch: {
    redCount(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.animateCount(this.$refs.redIndicatorEl);
      }
    },
    yellowCount(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.animateCount(this.$refs.yellowIndicatorEl);
      }
    }
  },
  methods: {
    onRegenerate() {
      this.$emit('regenerate');
    },
    animateCount(el) {
      if (!el) return;
      el.classList.add("pop");
      el.addEventListener("animationend", function handler() {
        el.classList.remove("pop");
        el.removeEventListener("animationend", handler);
      });
    }
  }
}
</script>

<style scoped>
.indicator-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  padding: 0 8px;
  margin-bottom: 8px;
}

.indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.indicator-icon {
  width: 20px;
  height: 20px;
}

.count {
  font-size: 14px;
  color: #444;
  display: inline-block;
}

@keyframes popAnimation {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.7);
  }
  100% {
    transform: scale(1);
  }
}
.pop {
  animation: popAnimation 0.5s ease-in-out;
}

.regenerate-button {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
}

.regenerate-button:hover {
  color: #333;
}

.regenerate-icon {
  width: 20px;
  height: 20px;
}
</style>
