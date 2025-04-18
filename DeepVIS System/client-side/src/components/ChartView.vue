<template>
  <div class="chart-scroll-wrapper">
    <div v-if="svgContent" class="chart-svg" v-html="svgContent"></div>
  </div>
</template>

<script>
export default {
  props: {
    svgContent: {
      type: String,
      default: ''
    }
  },
  watch: {
    svgContent(newVal) {
      this.$nextTick(() => {
        const svgEl = this.$el.querySelector('.chart-svg svg');
        if (svgEl) {
          svgEl.style.height = '100%';
          svgEl.style.width = 'auto';
          svgEl.getBoundingClientRect();
        }
      });
    }
  }
}
</script>

<style scoped>
.chart-scroll-wrapper {
  width: 100%;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chart-svg {
  height: 100%;
  display: block;
  margin: 0 auto;
}
</style>
