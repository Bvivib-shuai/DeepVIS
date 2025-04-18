<template>
  <div class="table-root">
    <div v-if="!db" class="no-file-message">
      Please upload sqlite file from left input panel.
    </div>
    <div v-else class="table-content">
      <!-- Table selection bar -->
      <div class="table-select">
        <label for="tableSelect">Select Table:</label>
        <select id="tableSelect" v-model="selectedTable" @change="loadTableData">
          <option v-for="table in tables" :key="table" :value="table">
            {{ table }}
          </option>
        </select>
      </div>
      <!-- Data table display -->
      <div class="table-container">
        <div class="table-wrapper">
          <table v-if="tableData && tableData.length">
            <thead>
            <tr>
              <th v-for="(col, index) in columns" :key="index">{{ col }}</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="(row, rowIndex) in tableData" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
            </tbody>
          </table>
          <div v-else class="no-data-message">
            No data in this table.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    db: {
      type: Object,
      default: null
    },
    tables: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      selectedTable: '',
      tableData: [],
      columns: []
    }
  },
  watch: {
    db(newVal) {
      if (newVal && this.tables.length) {
        this.selectedTable = this.tables[0]
        this.loadTableData()
      } else {
        this.selectedTable = ''
        this.tableData = []
        this.columns = []
      }
    },
    tables(newVal) {
      if (this.db && newVal.length) {
        this.selectedTable = newVal[0]
        this.loadTableData()
      }
    }
  },
  mounted() {
    if (this.db && this.tables.length) {
      this.selectedTable = this.tables[0]
      this.loadTableData()
    }
  },
  methods: {
    loadTableData() {
      if (!this.db || !this.selectedTable) return
      try {
        const res = this.db.exec(`SELECT * FROM "${this.selectedTable}"`)
        if (res && res.length > 0) {
          this.columns = res[0].columns
          this.tableData = res[0].values
        } else {
          this.columns = []
          this.tableData = []
        }
      } catch (e) {
        console.error('SQL query error:', e)
        this.columns = []
        this.tableData = []
      }
    }
  }
}
</script>

<style scoped>
.table-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  font-size: 12px;
}

.no-file-message {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 1rem;
}

.table-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.table-select {
  flex: 0 0 auto;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-select label {
  font-weight: bold;
  font-size: 12px;
}

.table-select select {
  padding: 4px 8px;
  font-size: 12px;
}

.table-container {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-wrapper {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

th, td {
  padding: 4px;
  border: 1px solid #ddd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

thead tr {
  transform: translateY(-4px);
}

thead {
  background-color: #f2f2f2;
  font-weight: bold;
  position: sticky;
  top: 0;
  z-index: 1;
}

.no-data-message {
  text-align: center;
  padding: 10px;
  color: #666;
}
</style>
