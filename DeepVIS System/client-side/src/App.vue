<template>
  <div class="app-container">
    <!-- Left Panel -->
    <div class="left-panel">
      <div class="cot-view">
        <div class="capsule-wrapper">
          <CotView ref="cotView" @updateInfo="updateInfo" @updateCounts="handleUpdateCounts" />
        </div>
      </div>

      <IndicatorRow
          :redCount="redCount"
          :yellowCount="yellowCount"
          @regenerate="handleRegenerate"
      />

      <div class="input-panel-fixed">
        <InputPanel
            @dbLoaded="handleDbLoaded"
            @questionSubmit="handleQuestionSubmit"
            @fileUploaded="handleFileUploaded"
        />
      </div>
    </div>
    <!-- Right Panel -->
    <div class="right-panel">
      <div class="info-view">
        <div class="capsule-wrapper">
          <InfoView
              :title="infoTitle"
              :content="infoContent"
              :isSelfCorrect="currentNodeSelfCorrect"
              :isManualCorrect="currentNodeManualCorrect"
              :manualCorrectionText="currentNodeManualCorrectText"
              @updateCorrection="handleCorrectionUpdate"
          />
        </div>
      </div>
      <div class="chart-view">
        <div class="capsule-wrapper">
          <ChartView :svgContent="svgContent" />
        </div>
      </div>
      <div class="table-view">
        <div class="capsule-wrapper">
          <TableView :db="db" :tables="tables" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import CotView from "./components/CotView.vue";
import InputPanel from "./components/InputPanel.vue";
import InfoView from "./components/InfoView.vue";
import ChartView from "./components/ChartView.vue";
import TableView from "./components/TableView.vue";

import IndicatorRow from "./components/IndicatorRow.vue";
import sampleChartSvg from "@/assets/sample_chart.svg?raw";
import sampleChartSvg2 from "@/assets/sample_chart2.svg?raw";


const useBackend = true;

export default {
  components: {
    CotView,
    InputPanel,
    InfoView,
    ChartView,
    TableView,
    IndicatorRow
  },
  data() {
    return {
      infoTitle: "",
      infoContent: "",
      currentNodeId: null,
      currentNodeSelfCorrect: false,
      currentNodeManualCorrect: false,
      currentNodeManualCorrectText: "",
      db: null,
      tables: [],
      redCount: 0,
      yellowCount: 0,
      svgContent: "",  
      dbFile: null     
    };
  },
  methods: {
    updateInfo({ title, content, id, selfCorrect, manualCorrect }) {
      this.infoTitle = title;
      this.infoContent = content;
      this.currentNodeId = id;
      this.currentNodeSelfCorrect = selfCorrect;
      this.currentNodeManualCorrect = !!manualCorrect;
      this.currentNodeManualCorrectText = manualCorrect;
    },
    handleUpdateCounts({ redCount, yellowCount }) {
      this.redCount = redCount;
      this.yellowCount = yellowCount;
    },
    handleCorrectionUpdate(correctionData) {
      if (!this.currentNodeId) return;
      this.$refs.cotView.updateNodeCorrection(
          this.currentNodeId,
          correctionData.type,
          correctionData.value
      );
      if (correctionData.type === "self") {
        this.currentNodeSelfCorrect = correctionData.value;
        if (correctionData.value) {
          this.currentNodeManualCorrect = false;
          this.currentNodeManualCorrectText = "";
        }
      } else if (correctionData.type === "manual") {
        if (correctionData.value) {
          this.currentNodeManualCorrect = true;
          this.currentNodeManualCorrectText = correctionData.value;
          this.currentNodeSelfCorrect = false;
        } else {
          this.currentNodeManualCorrect = false;
          this.currentNodeManualCorrectText = "";
        }
      }
    },
    handleDbLoaded({ db, tables }) {
      this.db = db;
      this.tables = tables;
    },
    handleFileUploaded(file) {
      this.dbFile = file;
    },
    handleQuestionSubmit({ query }) {
      console.log("Submit query:", query);
      if (this.$refs.cotView && this.$refs.cotView.showLoading) {
        this.$refs.cotView.showLoading();
      }
      if (useBackend) {
        const formData = new FormData();
        formData.append("question", query);
        if (this.dbFile) {
          formData.append("sqlite_file", this.dbFile);
        }
        axios
            .post("http://127.0.0.1:5001/api/visualization/generate", formData, {
              headers: { "Content-Type": "multipart/form-data" }
            })
            .then((response) => {
              const data = response.data;
              if (this.$refs.cotView && this.$refs.cotView.reloadDataWithData) {
                this.$refs.cotView.reloadDataWithData(data.nodesData);
              }
              this.svgContent = data.chartSVG;
              if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
                this.$refs.cotView.hideLoading();
              }
            })
            .catch((error) => {
              console.error("Error in generate:", error);
              if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
                this.$refs.cotView.hideLoading();
              }
              alert(error.response.data.error || "There is an error in the request.");
            });
      } else {
        setTimeout(() => {
          if (this.$refs.cotView && this.$refs.cotView.reloadData) {
            this.$refs.cotView.reloadData("/case1_node1.json");
          }
          this.svgContent = sampleChartSvg;
          if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
            this.$refs.cotView.hideLoading();
          }
        }, 2000);
      }
    },
    handleRegenerate() {
      console.log("Regenerate button clicked!");
      if (this.$refs.cotView && this.$refs.cotView.showLoading) {
        this.$refs.cotView.showLoading();
      }
      if (useBackend) {
        const corrections = this.$refs.cotView.getCorrections();
        const payload = {
          corrections: corrections
        };
        axios
            .post("http://127.0.0.1:5001/api/visualization/regenerate", payload, {
              headers: { "Content-Type": "application/json" }
            })
            .then((response) => {
              const data = response.data;
              if (this.$refs.cotView && this.$refs.cotView.reloadDataWithData) {
                this.$refs.cotView.reloadDataWithData(data.nodesData);
              }
              this.svgContent = data.chartSVG;
              if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
                this.$refs.cotView.hideLoading();
              }
            })
            .catch((error) => {
              console.error("Error in regenerate:", error);
              if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
                this.$refs.cotView.hideLoading();
              }
              alert(error.response.data.error || "There is an error in the request.");
            });
      } else {
        setTimeout(() => {
          if (this.$refs.cotView && this.$refs.cotView.reloadData) {
            this.$refs.cotView.reloadData("/case1_node2.json");
          }
          this.svgContent = sampleChartSvg2;
          if (this.$refs.cotView && this.$refs.cotView.hideLoading) {
            this.$refs.cotView.hideLoading();
          }
        }, 6000);
      }
    }
  }
};
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: row;
  height: 100dvh;
  width: 100dvw;
  overflow: hidden;
  box-sizing: border-box;
  background: linear-gradient(135deg, #f5f4f6 0%, #e9edf7 100%);
}

.left-panel {
  width: 65%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  min-width: 0;
}

.cot-view {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.input-panel-fixed {
  height: 100px;
  padding: 8px;
  box-sizing: border-box;
}

.right-panel {
  width: 35%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  min-width: 0;
}

.info-view {
  height: 25%;
  padding: 8px;
  box-sizing: border-box;
}

.chart-view {
  height: 50%;
  padding: 8px;
  box-sizing: border-box;
}

.table-view {
  height: 25%;
  padding: 8px;
  box-sizing: border-box;
}

.capsule-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: white;
  border-radius: 16px;
  padding: 8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
  width: 100%;
  height: 100%;
  box-sizing: border-box;
}
</style>
