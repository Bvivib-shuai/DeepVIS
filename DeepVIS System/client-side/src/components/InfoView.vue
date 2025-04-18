<template>
  <div class="info-card">
    <template v-if="title">
      <h3 class="info-title">Reasoning: {{ title }}</h3>
      <div class="info-scroll">
        <p class="info-text">
          {{ content || 'Select a node to see reasoning...' }}
        </p>
      </div>
      <div class="info-buttons">
        <button class="btn btn-self" @click="onSelfCorrect" :class="{ active: isSelfCorrect }">
          <span class="icon">
            <img src="@/assets/red.svg" alt="self-correct" />
          </span>
          Self-correct
        </button>
        <button class="btn btn-manual" @click="onManualCorrect" :class="{ active: isManualCorrect }" @mouseover="showTooltip" @mouseleave="hideTooltip">
          <span class="icon">
            <img src="@/assets/yellow.svg" alt="manual-correct" />
          </span>
          Manual correction
          <div v-if="tooltipVisible && isManualCorrect && manualCorrectionText" class="tooltip">
            {{ manualCorrectionText }}
          </div>
        </button>
      </div>
      <!-- Modal for manual correction input -->
      <div v-if="showModal" class="modal-overlay">
        <div class="modal-content">
          <h3>Manual Correction</h3>
          <textarea v-model="manualInput" placeholder="Enter correction details"></textarea>
          <div class="modal-buttons">
            <button @click="submitManualCorrection">Submit</button>
            <button @click="cancelManualCorrection">Cancel</button>
          </div>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="no-selection-message">
        No node selected.
      </div>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    title: String,
    content: String,
    isSelfCorrect: {
      type: Boolean,
      default: false
    },
    isManualCorrect: {
      type: Boolean,
      default: false
    },
    manualCorrectionText: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      tooltipVisible: false,
      showModal: false,
      manualInput: ''
    }
  },
  methods: {
    onSelfCorrect() {
      if (this.isSelfCorrect) {
        this.$emit('updateCorrection', { type: 'self', value: false })
      } else {
        this.$emit('updateCorrection', { type: 'self', value: true })
      }
    },
    onManualCorrect() {
      if (this.isManualCorrect) {
        this.$emit('updateCorrection', { type: 'manual', value: '' })
      } else {
        this.showModal = true
        this.manualInput = this.manualCorrectionText
      }
    },
    submitManualCorrection() {
      this.$emit('updateCorrection', { type: 'manual', value: this.manualInput })
      this.showModal = false
    },
    cancelManualCorrection() {
      this.showModal = false
    },
    showTooltip() {
      if (this.isManualCorrect && this.manualCorrectionText) {
        this.tooltipVisible = true
      }
    },
    hideTooltip() {
      this.tooltipVisible = false
    }
  }
}
</script>

<style scoped>
.info-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}
.info-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 8px;
}
.info-scroll {
  flex: 1;
  overflow-y: auto;
}
.info-text {
  font-size: 0.95rem;
  line-height: 1.5;
  color: #333;
  white-space: pre-line;
}
.info-buttons {
  margin-top: 16px;
  display: flex;
  gap: 10px;
}
.btn {
  border: none;
  padding: 6px 12px;
  font-size: 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-self {
  background-color: #f8d7da;
}
.btn-manual {
  background-color: #fff3cd;
}
.btn-self:not(.active),
.btn-manual:not(.active) {
  opacity: 0.5;
}
.btn-self.active,
.btn-manual.active {
  opacity: 1;
}
.icon {
  display: inline-flex;
  width: 1rem;
  height: 1rem;
  align-items: center;
  justify-content: center;
}
.icon img {
  height: 100%;
  width: auto;
  display: block;
}
.tooltip {
  position: absolute;
  background: #333;
  color: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: pre-wrap;
  z-index: 100;
  margin-top: 4px;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 300px;
  box-sizing: border-box;
}
.modal-content h3 {
  margin-top: 0;
}
.modal-content textarea {
  width: 100%;
  height: 80px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.no-selection-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 1rem;
}
</style>
