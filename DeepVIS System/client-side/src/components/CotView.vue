<template>
  <div class="cotflow-container" style="position: relative; height: 100%;">
    <div v-if="loading" class="loading-overlay">
      <div class="spinner">Loading...</div>
    </div>
    <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        class="cotflow"
        ref="flowView"
        :fit-view="true"
        :max-zoom="1"
        :fit-view-options="{ padding: 10,maxZoom: 1 }"
        :zoom-on-scroll="false"
        :nodes-draggable="false"
        @node-click="handleNodeClick"
        
    >
      <template #node-custom="{ data, id }">
        <transition name="fade-zoom">
          <div
              class="custom-node"
              :class="[
                data.depth === 1? 'depth-node1':'depth-node2',
                'depth-' + data.depth,
                'data-id-'+ id,
                { faded: data.faded },
                { selected: selectedId === id },
              ]"
              :style="{ opacity: data.status === 0 ? 0.5 : 1 }"
              v-show="!data.animatingOut && !data.hidden"
              @click.stop="selectNode(id)"
          >
          <!-- <div v-if="data.depth === 0 && showTimeLoading" class="item-loading"></div> -->
          <!-- s<div v-if="showLoadingArray.includes(id) && showTimeLoading" class="item-loading"></div> -->
            <div
                class="node-top"
                :style="{ backgroundColor: data.topBg || '#e8f5e9' }"
            >
              <span v-if="data.selfCorrect" class="correction-icon self">
                <img src="@/assets/red.svg" alt="self-correct" />
              </span>
              <span v-else-if="data.manualCorrect" class="correction-icon manual">
                <img src="@/assets/yellow.svg" alt="manual-correct" />
              </span>
              <span v-if="data.icon" class="icon">❗</span>
              <span class="node-title" >{{ data.title }}</span>
              <span
                  v-if="data.children && data.children.length"
                  class="toggle"
                  @click.stop="toggleCollapse(id,data)"
              >
                {{ data.collapsed ? '+' : '-' }}
              </span>
            </div>
            <div
                class="node-bottom"
                :style="{ backgroundColor: getBottomColor(data.topBg) }"
            >
              <div class="node-body" :class="[
                'node-body-id-'+ id
              ]"  v-html="formatContent(data.content)"></div>
            </div>
          </div>
        </transition>
      </template>
    </VueFlow>
  </div>
</template>

<script>
import { VueFlow } from "@vue-flow/core";
import dagre from "dagre";

export default {
  components: { VueFlow },
  data() {
    return {
      nodes: [],
      edges: [],
      rawNodes: [],
      showLoadingArray:[],
      selfManual:[],
      selectedId: null,
      loading: false, // loading
      showTimeLoading:false,
    };
  },
  methods: {
    loadStaticData(fileName, initial = false) {
      fetch(fileName)
          .then((response) => response.json())
          .then((data) => {
            this.showLoadingArray = []
            const oldRawNodes = JSON.parse(JSON.stringify(this.rawNodes))
            const newData = this.processData(data);
            this.selfManual = oldRawNodes.filter(fitem => fitem.data.selfCorrect || fitem.data.manualCorrect !== '')
            newData.forEach((parent) => {
              const oldItem = oldRawNodes.find(item => item.id === parent.id)
              if(oldItem){
                parent.data.collapsed = oldItem.data.collapsed
                if(parent.data.content !== oldItem.data.content && !(oldItem.data.selfCorrect || oldItem.data.manualCorrect !== '')){
                  console.log('The content of the edge of this node has changed -------------',parent.id)
                  this.showLoadingArray.push(parent.id)
                  const domNode = document.querySelector(`.node-body-id-${Number(parent.id)}`);
                  console.log(document,'add animate class',`.node-body-id-${Number(parent.id)}`,domNode)
                  if (domNode) domNode.classList.add('animate-in');
                  console.log( document)
                }
                // if(oldItem.data.selfCorrect || oldItem.data.manualCorrect !== ''){
                //   parent.data.collapsed = false
                // }
              }
              if (parent.data.children && parent.data.children.length > 0) {
                
                const childrenArr = parent.data.children.slice();
                const sameName = childrenArr.filter((childId) => {
                  const child = newData.find((n) => n.id === childId);
                  return child && child.data.title === parent.data.title;
                });
                const diffName = childrenArr.filter((childId) => {
                  const child = newData.find((n) => n.id === childId);
                  return child && child.data.title !== parent.data.title;
                });
                sameName.sort((a, b) => Number(a) - Number(b));
                diffName.sort((a, b) => Number(a) - Number(b));
                parent.data.children = [...diffName, ...sameName];
              }
            });
            this.rawNodes = newData
            this.applyLayout(initial);
            this.hideLoading();
            this.selfManual.forEach(smItem => {
              const domNode = document.querySelector(`.data-id-${Number(smItem.id)}`);
              console.log(document,'add exiting class',`.data-id-${Number(smItem.id)}`,domNode)
              if (domNode) domNode.classList.add('exiting');
            })
            this.applyLayout();
            setTimeout(() => {
              this.selfManual.forEach(smItem => {
                const domNode = document.querySelector(`.data-id-${Number(smItem.id)}`);
                console.log('remove exiting class',domNode)
                if (domNode) domNode.classList.remove('exiting');
              })

              this.showLoadingArray.forEach(itemId => {
                const domNode = document.querySelector(`.node-body-id-${Number(itemId)}`);
                console.log('remove animate-in class',domNode)
                if (domNode) domNode.classList.remove('animate-in');
              })
              this.applyLayout();
              setTimeout(() => {
                const keys = this.selfManual.map(key => key.id)
                this.rawNodes.forEach((parent) => {
                  if(keys.includes(parent.id)){
                    parent.data.collapsed = false
                  }
                })
                this.showLoadingArray.forEach(itemId => {
                  const domNode = document.querySelector(`.node-body-id-${Number(itemId)}`);
                  console.log('remove animate-in class',domNode)
                  if (domNode) domNode.classList.remove('animate-in');
                  // if (domNode) domNode.classList.remove('animate-out');
                })
                console.log('There is a warning or a modification.')
                this.applyLayout();
              }, 1000);
            }, 1000);
            
          })
          .catch((err) => {
            console.error("Failed to load JSON:", err);
            this.hideLoading();
          });
    },
    reloadData(fileName = "/case1_node1.json") {
      this.showTimeLoading = true
      setTimeout(()=>{
          this.loadStaticData(fileName);
          setTimeout(() => {
            this.showTimeLoading =false
          }, 3000);
      },1500)
    },
    reloadDataWithData(nodesData) {
      this.rawNodes = this.processData(nodesData);
      this.applyLayout();
    },
    showLoading() {
      this.loading = true;
    },
    hideLoading() {
      this.loading = false;
    },
    processData(data) {
      const itemMap = {};
      data.forEach((item) => {
        itemMap[item.Index] = item;
      });
      const flatNodes = [];
      const buildNode = (item, depth) => {
        let color;
        if (depth === 0) {
          color = "#c5e2f6";
        } else if (depth === 1) {
          color = "#d9f0e2";
        } else {
          color = "#fce4d6";
        }
        const collapsed = depth === 0 ? false : true;
        const node = {
          id: item.Index.toString(),
          data: {
            title: item.Name,
            content: item.Result,
            reasoning: item.Reasoning,
            topBg: color,
            children: [],
            selfCorrect: false,
            manualCorrect: "",
            status: item.Status !== undefined ? item.Status : 1,
            collapsed: collapsed
          }
        };
        node.data.depth = depth;
        if (item["Sub - node Indices"] && item["Sub - node Indices"].length > 0) {
          item["Sub - node Indices"].forEach((childIndex) => {
            const childItem = itemMap[childIndex];
            if (childItem) {
              const childNode = buildNode(childItem, depth + 1);
              node.data.children.push(childNode.id);
            }
          });
        }
        flatNodes.push(node);
        return node;
      };
      if (!itemMap[0]) {
        console.error("Root node with Index 0 not found.");
        return [];
      }
      buildNode(itemMap[0], 0);
      return flatNodes;
    },
    getBottomColor(topBg) {
      const rgba = {
        "#c5e2f6": "rgba(197, 226, 246, 0.5)",
        "#d9f0e2": "rgba(217, 240, 226, 0.5)",
        "#fce4d6": "rgba(252, 228, 214, 0.5)"
      };
      return rgba[topBg?.toLowerCase()] || "rgba(255,255,255,0.5)";
    },
    
    toggleCollapse(id,data) {
      console.log('toggleCollapse',data)
      const node = this.rawNodes.find((n) => n.id === id);
      if (!node || !node.data.children) return;
      const children = node.data.children;
      
      if (!node.data.collapsed) {
        console.log('/expand-> collapse')
        children.forEach((cid) => {
          const child = this.rawNodes.find((n) => n.id === cid);
          if (child) child.data.animatingOut = true;
          const domNode = document.querySelector(`.data-id-${Number(cid)}`);
          console.log('add exiting class',`.data-id-${Number(cid)}`,domNode)
          if (domNode) domNode.classList.add('exiting');
        });
        setTimeout(() => {
          node.data.collapsed = true;
          children.forEach((cid) => {
            const child = this.rawNodes.find((n) => n.id === cid);
            if (child) {
              child.data.animatingOut = false;
              child.data.hidden = true;
              const domNode = document.querySelector(`.data-id-${Number(cid)}`);
              console.log('remove exiting class',domNode)
              if (domNode) domNode.classList.remove('exiting');
            }
          });
          this.applyLayout();
        }, 300);
      } else {
         console.log('expand-> collapse')
       
        children.forEach((cid) => {
          const child = this.rawNodes.find((n) => n.id === cid);
          if (child) {
            child.data.collapsed = true;
              child.data.hidden = false;
            const domNode = document.querySelector(`.data-id-${Number(cid)}`);
            console.log('add exiting class',`.data-id-${Number(cid)}`,domNode)
            if (domNode) {
              domNode.classList.add('exiting');
              domNode.classList.add('depth-node' + (child.data.depth >= 2 ? '2' : '1'));
            }
            this.applyLayout();
          }
        });
        setTimeout(() => {
          node.data.collapsed = false;
          children.forEach((cid) => {
            const child = this.rawNodes.find((n) => n.id === cid);
            if (child) {
              const domNode = document.querySelector(`.data-id-${Number(cid)}`);
              console.log('remove exiting class',domNode)
              if (domNode) domNode.classList.remove('exiting');
              
            }
          });
          this.applyLayout();
        }, 300);
        
      }
    },
    selectNode(id) {
      this.selectedId = id;
      const node = this.rawNodes.find((n) => n.id === id);
      if (node) {
        this.$emit("updateInfo", {
          title: node.data.title,
          content: node.data.reasoning,
          id: id,
          selfCorrect: node.data.selfCorrect,
          manualCorrect: node.data.manualCorrect
        });
      }
    },
    updateNodeCorrection(id, type, value) {
      const node = this.rawNodes.find((n) => n.id === id);
      if (!node) return;
      if (type === "self") {
        if (value) {
          node.data.selfCorrect = true;
          node.data.manualCorrect = "";
        } else {
          node.data.selfCorrect = false;
        }
      } else if (type === "manual") {
        if (value) {
          node.data.manualCorrect = value;
          node.data.selfCorrect = false;
        } else {
          node.data.manualCorrect = "";
        }
      }
      this.applyLayout();
    },
    formatContent(text) {
      if (!text) return "";
      const formatted = text.replace(/\[red\]([\s\S]*?)\[\/red\]/g, '<span style="color:red;">$1</span>');
      return `<span>${formatted}</span>`;
    },
    applyLayout(initial = false) {
      const g = new dagre.graphlib.Graph();
      const padding = 10;
      console.log(g,this.node)
      const maxZoom = this.nodes.some(n => n.data.depth > 1) ? 0.8 : 1.2;
      g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 40 });
      g.setDefaultEdgeLabel(() => ({}));

      const visibleNodes = [];
      const visibleEdges = [];

      const addNode = (node, depth = 0) => {
        if (!visibleNodes.find((n) => n.id === node.id)) {
          visibleNodes.push({
            id: node.id,
            type: "custom",
            data: { ...node.data, depth },
            position: { x: 0, y: 0 }
          });
        }
        if (node.data.children && !node.data.collapsed) {
          node.data.children.forEach((cid) => {
            const child = this.rawNodes.find((n) => n.id === cid);
            if (child) {
              addNode(child, depth + 1);
              visibleEdges.push({
                id: `e${node.id}-${child.id}`,
                source: node.id,
                target: child.id
              });
            }
          });
        }
      };

      const root = this.rawNodes.find((n) => n.id === "0");
      if (root) {
        addNode(root);
      } else {
        console.error("Root node with id '0' not found in rawNodes.");
      }

      visibleNodes.forEach((n) => {
        let width = 250;
        if (n.data.depth === 0) width = 600;
        else if (n.data.depth === 1) width = 300;
        else width = 250;
        const lineCount = n.data.content.split("<br>").length;
        const estimatedHeight = Math.max(110, 66 + (lineCount - 1) * 20);
        g.setNode(n.id, { width, height: estimatedHeight });
      });

      visibleEdges.forEach((e) => g.setEdge(e.source, e.target));
      dagre.layout(g);

      const rootNode = visibleNodes.find(n => n.id === '0');
      if (rootNode) {
        const containerWidth = document.querySelector('.cotflow').offsetWidth;
        const nodeWidth = 600;
        rootNode.position.x = (containerWidth - nodeWidth) / 2;
      }

      visibleNodes.forEach((n) => {
        const pos = g.node(n.id);
        if (n.id !== '0') {
          n.position = { 
            x: pos.x - 120, 
            y: pos.y - 55 
          };
        }
      });
      this.rawNodes.forEach((parent) => {
        if (parent.data.children && parent.data.children.length > 0) {
          const childrenArr = parent.data.children.slice();
          const sameName = childrenArr.filter((childId) => {
            const child = this.rawNodes.find((n) => n.id === childId);
            return child && child.data.title === parent.data.title;
          });
          const diffName = childrenArr.filter((childId) => {
            const child = this.rawNodes.find((n) => n.id === childId);
            return child && child.data.title !== parent.data.title;
          });
          sameName.sort((a, b) => Number(a) - Number(b));
          diffName.sort((a, b) => Number(a) - Number(b));
          parent.data.children = [...diffName, ...sameName];

        }
      });

      this.rawNodes.forEach((parent) => {
        if (parent.data.children && parent.data.children.length > 0) {
          const parentTitle = parent.data.title;
          const hasSameChild = parent.data.children.some((childId) => {
            const child = this.rawNodes.find((n) => n.id === childId);
            return child && child.data.title === parentTitle;
          });
          if (hasSameChild) {
            visibleEdges.forEach((edge) => {
              if (edge.source === parent.id) {
                const child = this.rawNodes.find((n) => n.id === edge.target);
                if (child && child.data.title !== parentTitle) {
                  edge.style = { strokeDasharray: "5,5" };
                }
              }
            });
          }
        }
      });

      this.nodes = visibleNodes;
      this.edges = visibleEdges;

      this.$nextTick(() => {
        this.$refs.flowView.fitView({
          padding: 10,
          duration: 300,
          maxZoom: Math.min(1.2, 1 / Math.sqrt(this.nodes.length)),
          // maxZoom:maxZoom,
          includeHiddenNodes: true
        });
      });

      // this.$nextTick(() => {
      //   this.fitView({
      //     padding,
      //     duration: 300,
      //     maxZoom
      //   });
      // });

      const redCount = visibleNodes.filter((n) => n.data.selfCorrect).length;
      const yellowCount = visibleNodes.filter(
          (n) => n.data.manualCorrect && n.data.manualCorrect.trim() !== ""
      ).length;
      this.$emit("updateCounts", { redCount, yellowCount });
    },

    getCorrections() {
      let corrections = [];
      this.rawNodes.forEach((node) => {
        if (node.data.selfCorrect) {
          corrections.push({
            node_id: node.id,
            node_name: node.data.title,
            type: "self",
            value: true
          });
        }
        if (node.data.manualCorrect && node.data.manualCorrect.trim() !== "") {
          corrections.push({
            node_name: node.data.title,
            node_id: node.id,
            type: "manual",
            value: node.data.manualCorrect
          });
        }
      });
      return corrections;
    }
  }
};
</script>

<style scoped>
.cotflow {
  width: 100%;
  height: 100%;
  background: transparent;
  display: flex;
  justify-content: center;
} 

.cotflow-container {
  display: flex;
  justify-content: center;
  overflow: hidden;
}
.fade-zoom-enter-active,
.fade-zoom-leave-active {
  transition: all 0.3s ease;
}
.fade-zoom-enter-from,
.fade-zoom-leave-to {
  opacity: 0;
  transform: scale(0.8);
}
.custom-node {
  font-size: 13px;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  word-wrap: break-word;
  word-break: break-word;
  border-radius: 8px;
  border: 2px solid transparent;
  
}

.custom-node.selected {
  border-color: #4b83f5;
}
.depth-node1{
  transition: 
    opacity 0.4s,
    max-width 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28),
    min-width 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}
.depth-node2{
  transition: 
    opacity 0.4s,
    /* max-width 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28),
    min-width 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28); */
}
@keyframes nodeIn1 {
  from {
    opacity: 0;
    transform: scale(0) translateY(-20px);
    max-width: 0;
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
    max-width: 300px;
  }
}

@keyframes nodeOut1 {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
    max-width: 300px;
  }
  to {
    opacity: 0;
    transform: scale(0) translateY(20px);
    max-width: 0;
  }
}
.depth-node1:not(.exiting) {
  animation: nodeIn1 0.6s forwards;
  /* animation: nodeIn1 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; */
}

.depth-node1.exiting {
  animation: nodeOut1 0.4s forwards;
}
@keyframes nodeIn2 {
  from {
    opacity: 0;
    transform: scale(0) translateY(-20px);
    max-width: 0;
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
    max-width: 250px;
  }
}

@keyframes nodeOut2 {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
    max-width: 250px;
  }
  to {
    opacity: 0;
    transform: scale(0) translateY(20px);
    max-width: 0;
  }
}
.depth-node2:not(.exiting) {
  animation: nodeIn2 0.6s forwards;
}

.depth-node2.exiting {
  animation: nodeOut2 0.4s forwards;
}
.depth-0 {
  max-width: 600px;
  min-width: 600px;
}
.depth-1 {
  max-width: 300px;
  min-width: 300px;
 
}
       
.depth-2,
.depth-3,
.depth-4,
.depth-5 {
  max-width: 250px;
  min-width: 250px;
 
}

.node-top {
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  padding: 6px 10px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #687182;
  border-bottom: none;
}
.node-bottom {
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  padding: 6px 10px;
  border: 1px solid #687182;
}
.node-title {
  flex: 1;
  color: #333;
  font-weight: bold;
 
}
.node-body {
  color: #444;
  line-height: 1.4;
  padding-top: 2px;
  white-space: pre-wrap;
  min-height: 56px;
  display: inline-block;
  width: 100%;
  opacity: 1; 
  transition: opacity 2s ease-in-out; 
}
.node-body.animate-in {
  animation: fadeIn 2s ease-in-out forwards;
}

.node-body.animate-out {
  animation: fadeOut 2s ease-in-out forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeOut {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
.icon {
  color: red;
  font-weight: bold;
  margin-right: 6px;
}
.toggle {
  font-weight: bold;
  color: #888;
  margin-left: 6px;
  cursor: pointer;
}
.correction-icon {
  display: inline-flex;
  margin-right: 4px;
}
.correction-icon.self img,
.correction-icon.manual img {
  width: 16px;
  height: 16px;
}
.red-inline {
  color: red;
  display: inline;
}
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.spinner {
  font-size: 1.2rem;
  color: #333;
}

.item-loading{
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  backdrop-filter: blur(5px);
  background-color: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  
}
.item-loading:not(.loading-exiting){
  animation: fade 2s ease-in-out forwards;
}
.item-loading.loading-exiting{
  animation: fade 2s ease-in-out forwards;
}
@keyframes fade {
  0%, 100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}
</style>
