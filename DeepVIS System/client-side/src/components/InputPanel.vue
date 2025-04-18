<template>
  <div class="input-container">
    <button class="icon-button" @click="uploadFile" v-html="uploadSvg"></button>
    <input
        v-model="query"
        type="text"
        class="input-box"
        placeholder="Enter your question..."
    />
    <button class="icon-button" @click="handleSubmit">
      <img :src="sendSvg" alt="send" />
    </button>
    <input
        type="file"
        ref="fileInput"
        style="display: none;"
        @change="handleFileChange"
        accept=".sqlite,.db"
    />
  </div>
</template>

<script>
import initSqlJs from "sql.js";
import sendSvg from "@/assets/send.svg"; 

export default {
  data() {
    return {
      query: "",
      uploadSvg: `
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" width="33" height="34" viewBox="0 0 33 34">
          <defs>
            <linearGradient x1="1" y1="0.5" x2="0" y2="0.5" id="upload_svg">
              <stop offset="0%" stop-color="#3B72E9" />
              <stop offset="100%" stop-color="#8B8EF6" />
            </linearGradient>
          </defs>
          <g opacity="0.3">
            <path d="M0 10C0 4.5 4.5 0 10 0H23C28.5 0 33 4.5 33 10V24C33 29.5 28.5 34 23 34H10C4.5 34 0 29.5 0 24Z" fill="url(#upload_svg)" />
          </g>
          <path d="M11.1 22.42h11.8a.5.5 0 0 0 .5-.5v-4.53a.5.5 0 0 1 .5-.5h.6a.5.5 0 0 1 .5.5v5.82a.8.8 0 0 1-.8.79H9.8a.8.8 0 0 1-.8-.8v-5.82a.5.5 0 0 1 .5-.5h.6a.5.5 0 0 1 .5.5v4.53a.5.5 0 0 0 .5.5Z" fill="#fff"/>
        </svg>
      `
    };
  },
  computed: {
    sendSvg() {
      return sendSvg;
    }
  },
  methods: {
    handleSubmit() {
      this.$emit("questionSubmit", { query: this.query });
      this.query = "";
    },
    uploadFile() {
      this.$refs.fileInput.click();
    },
    handleFileChange(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.$emit("fileUploaded", file);
      const reader = new FileReader();
      reader.onload = async (e) => {
        const arrayBuffer = e.target.result;
        const SQL = await initSqlJs({
          locateFile: (fileName) => `https://sql.js.org/dist/${fileName}`
        });
        const db = new SQL.Database(new Uint8Array(arrayBuffer));
        const res = db.exec("SELECT name FROM sqlite_master WHERE type='table'");
        let tables = [];
        if (res.length > 0 && res[0].values) {
          tables = res[0].values.map((row) => row[0]);
        }
        this.$emit("dbLoaded", { db, tables });
      };
      reader.readAsArrayBuffer(file);
    }
  }
};
</script>

<style scoped>
.input-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  background: white;
  border-radius: 999px;
  padding: 0 12px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
  box-sizing: border-box;
}
.icon-button {
  width: 44px;
  height: 100%;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.input-box {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 1rem;
  padding: 10px;
  outline: none;
  color: #333;
}
</style>
