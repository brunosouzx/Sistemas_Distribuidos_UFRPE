// Configuração da API
const API_URL = "http://localhost:5001";
const ESTOQUE_API_URL = "http://localhost:5002";

// Estado da aplicação
let state = {
  pedidos: [],
  estoque: [],
  filtroAtivo: "todos",
  pedidoSelecionado: null,
  ingredienteSelecionado: null,
  atualizacaoAutomatica: null,
};

// Elementos DOM
const elements = {
  pedidosGrid: document.getElementById("pedidosGrid"),
  loading: document.getElementById("loading"),
  emptyState: document.getElementById("emptyState"),
  statRecebidos: document.getElementById("statRecebidos"),
  statPreparando: document.getElementById("statPreparando"),
  statProntos: document.getElementById("statProntos"),
  statCancelados: document.getElementById("statCancelados"),
  
  // Modal Pedidos
  modalAcao: document.getElementById("modalAcao"),
  modalTitulo: document.getElementById("modalTitulo"),
  modalPedidoId: document.getElementById("modalPedidoId"),
  modalCliente: document.getElementById("modalCliente"),
  modalItem: document.getElementById("modalItem"),
  modalObs: document.getElementById("modalObs"),
  modalObsContainer: document.getElementById("modalObsContainer"),
  tempoPreparoContainer: document.getElementById("tempoPreparoContainer"),
  btnConfirmar: document.getElementById("btnConfirmar"),
  btnCancelar: document.getElementById("btnCancelar"),
  
  // Modal Cancelamento
  modalCancelar: document.getElementById("modalCancelar"),
  cancelarPedidoId: document.getElementById("cancelarPedidoId"),
  inputMotivoCancelamento: document.getElementById("inputMotivoCancelamento"),

  // Modal de Estoque
  modalEstoque: document.getElementById("modalEstoque"),
  modalIngredienteNome: document.getElementById("modalIngredienteNome"),
  inputQuantidadeEstoque: document.getElementById("inputQuantidadeEstoque"),
  
  // Botões gerais
  btnRefresh: document.getElementById("btnRefresh"),
  toast: document.getElementById("toast"),
  estoqueTableBody: document.getElementById("estoqueTableBody"),
  estoqueLoading: document.getElementById("estoqueLoading"),
  btnRefreshEstoque: document.getElementById("btnRefreshEstoque"),
};

// Inicialização
function init() {
  console.log("Iniciando aplicação...");
  try {
    setupEventListeners();
    carregarPedidos();
    carregarEstoque();
    iniciarAtualizacaoAutomatica();
  } catch (error) {
    console.error("Erro fatal na inicialização:", error);
    mostrarToast("Erro ao iniciar sistema.", "error");
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Event Listeners
function setupEventListeners() {
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      state.filtroAtivo = this.dataset.status;
      renderizarPedidos();
    });
  });

  if (elements.btnRefresh) {
    elements.btnRefresh.addEventListener("click", () => {
      carregarPedidos(); 
      mostrarToast("Atualizando pedidos...", "info");
    });
  }

  if (elements.btnRefreshEstoque) {
    elements.btnRefreshEstoque.addEventListener("click", () => {
      carregarEstoque();
      mostrarToast("Atualizando estoque...", "info");
    });
  }

  // Modais
  if (elements.btnCancelar) elements.btnCancelar.addEventListener("click", fecharModal);
  if (elements.btnConfirmar) elements.btnConfirmar.addEventListener("click", confirmarAcao);

  document.querySelectorAll(".close").forEach(el => {
      el.addEventListener("click", () => {
          fecharModal();
          fecharModalCancelar();
          if (typeof fecharModalEstoque === 'function') fecharModalEstoque();
      });
  });

  window.onclick = function (event) {
    if (elements.modalAcao && event.target === elements.modalAcao) fecharModal();
    if (elements.modalCancelar && event.target === elements.modalCancelar) fecharModalCancelar();
    if (elements.modalEstoque && event.target === elements.modalEstoque) if (typeof fecharModalEstoque === 'function') fecharModalEstoque();
  };
}

// --- API Calls ---
async function carregarPedidos(silencioso = false) {
  try {
    if (!silencioso) mostrarLoading(true);
    const response = await fetch(`${API_URL}/fila`);
    if (!response.ok) throw new Error("Falha na API");
    
    const data = await response.json();
    state.pedidos = data.pedidos || [];
    renderizarPedidos();
    atualizarEstatisticas();
  } catch (error) {
    console.error("Erro ao carregar pedidos:", error);
    if (!silencioso) mostrarToast("Erro ao carregar pedidos", "error");
  } finally {
    if (!silencioso) mostrarLoading(false);
  }
}

async function iniciarPreparo(pedidoId) {
  try {
    const response = await fetch(`${API_URL}/pedidos/${pedidoId}/iniciar`, { method: "PUT" });
    const data = await response.json();
    if (response.ok) {
      mostrarToast("Cronômetro iniciado! ⏱️", "success");
      carregarPedidos();
      fecharModal();
    } else {
      mostrarToast(data.erro || "Erro", "error");
    }
  } catch (error) {
    mostrarToast("Erro ao iniciar preparo", "error");
  }
}

async function finalizarPedido(pedidoId) {
  try {
    const response = await fetch(`${API_URL}/pedidos/${pedidoId}/finalizar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}), 
    });
    const data = await response.json();
    if (response.ok) {
      const tempoTotal = data.tempo_total || "calculado";
      mostrarToast(`✅ Pedido finalizado em ${tempoTotal} min!`, "success");
      carregarPedidos();
      fecharModal();
    } else {
      mostrarToast(data.erro || "Erro", "error");
    }
  } catch (error) {
    mostrarToast("Erro ao finalizar pedido", "error");
  }
}

async function cancelarPedidoApi(pedidoId, motivo) {
    try {
        const response = await fetch(`${API_URL}/pedidos/${pedidoId}/cancelar`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ motivo: motivo }),
        });
        
        if (response.ok) {
            mostrarToast("Pedido cancelado com sucesso!", "success");
            carregarPedidos(); 
            fecharModalCancelar();
        } else {
            const data = await response.json();
            mostrarToast(data.erro || "Erro ao cancelar", "error");
        }
    } catch (error) {
        console.error(error);
        mostrarToast("Erro de conexão ao cancelar", "error");
    }
}

async function carregarEstoque() {
  try {
    const response = await fetch(`${ESTOQUE_API_URL}/estoque`);
    const data = await response.json();
    state.estoque = data.estoque || [];
    renderizarEstoque();
  } catch (error) {
    console.error("Erro estoque:", error);
  }
}

// --- Estoque ---
function abrirModalEstoque(ingrediente) {
    state.ingredienteSelecionado = ingrediente;
    elements.modalIngredienteNome.textContent = ingrediente;
    elements.inputQuantidadeEstoque.value = 10;
    elements.inputQuantidadeEstoque.focus();
    elements.modalEstoque.style.display = "block";
}

function fecharModalEstoque() {
    elements.modalEstoque.style.display = "none";
    state.ingredienteSelecionado = null;
}

async function confirmarReposicao() {
    const ingrediente = state.ingredienteSelecionado;
    const quantidade = elements.inputQuantidadeEstoque.value;

    if (!ingrediente || !quantidade || quantidade <= 0) {
        mostrarToast("Quantidade inválida", "error");
        return;
    }

    try {
        const response = await fetch(
            `${ESTOQUE_API_URL}/estoque/${ingrediente}/adicionar`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    quantidade: parseInt(quantidade),
                    motivo: "Reposição via Interface Cozinha",
                }),
            }
        );
        if (response.ok) {
            mostrarToast(`✅ ${ingrediente} abastecido (+${quantidade})`, "success");
            carregarEstoque();
            fecharModalEstoque();
        } else {
            mostrarToast("Erro ao repor", "error");
        }
    } catch (error) {
        mostrarToast("Erro de conexão", "error");
    }
}

// --- Renderização ---
function renderizarPedidos() {
  let pedidosFiltrados = state.pedidos;
  
  if (state.filtroAtivo !== "todos") {
    pedidosFiltrados = state.pedidos.filter((p) => p.status === state.filtroAtivo);
  } else {
    // Se for "todos", esconde os cancelados
    pedidosFiltrados = state.pedidos.filter(p => p.status !== 'CANCELADO');
  }

  if (pedidosFiltrados.length === 0) {
    elements.pedidosGrid.style.display = "none";
    elements.emptyState.style.display = "block";
    return;
  }

  elements.pedidosGrid.style.display = "grid";
  elements.emptyState.style.display = "none";
  elements.pedidosGrid.innerHTML = "";

  pedidosFiltrados.forEach((pedido) => {
    // AQUI OCORRIA O ERRO: appendChild precisa de um elemento HTML (nó), não string.
    elements.pedidosGrid.appendChild(criarPedidoCard(pedido));
  });
}

function criarPedidoCard(pedido) {
  // CRIA SEMPRE UM ELEMENTO DIV
  const card = document.createElement("div");
  
  if (pedido.status === "CANCELADO") {
      const motivo = pedido.observacao || "Cancelado pela cozinha";
      card.className = "pedido-card status-CANCELADO";
      card.innerHTML = `
            <div class="pedido-header">
                <div class="pedido-numero">#${pedido.pedido_id}</div>
                <span class="pedido-status status-badge-CANCELADO">CANCELADO</span>
            </div>
            <div class="pedido-info">
                <p><strong>${pedido.cliente}</strong></p>
                <p class="item-destaque" style="text-decoration: line-through; color: #999;">🍔 ${pedido.item}</p>
                <div class="pedido-obs" style="background: #fadbd8; border-color: #e74c3c; color: #78281f;">
                    🚫 Motivo: ${motivo}
                </div>
                <p class="pedido-tempo">📅 ${new Date(pedido.data_recebimento).toLocaleString("pt-BR")}</p>
            </div>
      `;
      return card; // Retorna o elemento
  }

  // Lógica Normal
  card.className = `pedido-card status-${pedido.status}`;

  const dataRecebimento = new Date(pedido.data_recebimento).toLocaleString("pt-BR");
  let tempoInfo = `<p class="pedido-tempo">📅 ${dataRecebimento}</p>`;
  
  if (pedido.status === 'PRONTO' && pedido.tempo_preparacao) {
      tempoInfo += `<p class="pedido-tempo">⏱️ Total: ${pedido.tempo_preparacao} min</p>`;
  }
  if (pedido.status === 'PREPARANDO' && pedido.data_inicio_preparo) {
      const horaInicio = new Date(pedido.data_inicio_preparo).toLocaleTimeString("pt-BR", {hour: '2-digit', minute:'2-digit'});
      tempoInfo += `<p class="pedido-tempo" style="color: var(--secondary-color)">🍳 Iniciado às ${horaInicio}</p>`;
  }

  const obsHtml = pedido.observacao
    ? `<div class="pedido-obs">⚠️ ${pedido.observacao}</div>`
    : "";

  let acoes = "";
  const btnCancelar = `<button class="btn btn-sm" style="background: #e74c3c; color: white; margin-left:5px; min-width: 40px;" onclick="abrirModalCancelar(${pedido.id}, '${pedido.item}')" title="Cancelar Pedido">✖</button>`;

  if (pedido.status === "RECEBIDO") {
    acoes = `<button class="btn btn-warning" onclick="abrirModalIniciar(${pedido.id})">🍳 Iniciar</button>${btnCancelar}`;
  } else if (pedido.status === "PREPARANDO") {
    acoes = `<button class="btn btn-success" onclick="abrirModalFinalizar(${pedido.id})">✅ Finalizar</button>${btnCancelar}`;
  } else if (pedido.status === "PRONTO") {
      acoes = `<span style="color: green; font-weight: bold;">Entregue na bancada</span>`;
  }

  card.innerHTML = `
        <div class="pedido-header">
            <div class="pedido-numero">#${pedido.pedido_id}</div>
            <span class="pedido-status status-badge-${pedido.status}">${pedido.status}</span>
        </div>
        <div class="pedido-info">
            <p><strong>${pedido.cliente}</strong></p>
            <p class="item-destaque">🍔 ${pedido.item}</p>
            ${obsHtml}
            ${tempoInfo}
        </div>
        <div class="pedido-actions">${acoes}</div>
    `;
  return card;
}

function atualizarEstatisticas() {
  elements.statRecebidos.textContent = state.pedidos.filter((p) => p.status === "RECEBIDO").length;
  elements.statPreparando.textContent = state.pedidos.filter((p) => p.status === "PREPARANDO").length;
  elements.statProntos.textContent = state.pedidos.filter((p) => p.status === "PRONTO").length;
  if(elements.statCancelados) {
      elements.statCancelados.textContent = state.pedidos.filter((p) => p.status === "CANCELADO").length;
  }
}

function renderizarEstoque() {
  if (!elements.estoqueTableBody) return;
  if (state.estoque.length === 0) {
    elements.estoqueTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px;">📦 Vazio</td></tr>`;
    return;
  }
  elements.estoqueTableBody.innerHTML = state.estoque.map((item) => {
      const qtd = item.quantidade || 0;
      let statusClass = qtd === 0 ? "status-critico" : qtd <= item.estoque_minimo ? "status-baixo" : "status-ok";
      let statusText = qtd === 0 ? "Esgotado" : qtd <= item.estoque_minimo ? "Baixo" : "OK";
      return `
        <tr>
          <td><strong>${item.nome}</strong></td>
          <td>${qtd}</td>
          <td>${item.unidade || "unidade"}</td>
          <td><span class="estoque-status ${statusClass}">${statusText}</span></td>
          <td><button class="btn-sm btn-success" onclick="abrirModalEstoque('${item.nome}')">+ Repor</button></td>
        </tr>
      `;
    }).join("");
}

// Modais Lógica
function abrirModalIniciar(id) {
  const p = state.pedidos.find((x) => x.id === id);
  if (!p) return;
  state.pedidoSelecionado = p;
  elements.modalTitulo.textContent = "🍳 Iniciar Preparo";
  elements.modalPedidoId.textContent = `#${p.pedido_id}`;
  elements.modalCliente.textContent = p.cliente;
  elements.modalItem.textContent = p.item;
  elements.modalObsContainer.style.display = p.observacao ? "block" : "none";
  if(p.observacao) elements.modalObs.textContent = p.observacao;
  if(elements.tempoPreparoContainer) elements.tempoPreparoContainer.style.display = "none";
  elements.btnConfirmar.textContent = "Iniciar Agora";
  elements.btnConfirmar.className = "btn btn-warning";
  elements.modalAcao.style.display = "block";
}

function abrirModalFinalizar(id) {
  const p = state.pedidos.find((x) => x.id === id);
  if (!p) return;
  state.pedidoSelecionado = p;
  elements.modalTitulo.textContent = "✅ Finalizar Pedido";
  elements.modalPedidoId.textContent = `#${p.pedido_id}`;
  elements.modalCliente.textContent = p.cliente;
  elements.modalItem.textContent = p.item;
  elements.modalObsContainer.style.display = p.observacao ? "block" : "none";
  if(p.observacao) elements.modalObs.textContent = p.observacao;
  
  let textoTempo = "Calculando...";
  if (p.data_inicio_preparo) {
      try {
          const inicio = new Date(p.data_inicio_preparo);
          const agora = new Date();
          if(!isNaN(inicio.getTime())){
             const diffMins = Math.max(1, Math.floor((agora - inicio) / 60000));
             textoTempo = `${diffMins} minutos decorridos`;
          }
      } catch(e) { console.error(e); }
  }
  elements.tempoPreparoContainer.style.display = "block";
  elements.tempoPreparoContainer.innerHTML = `<div style="background: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 8px; text-align: center;"><p>Tempo:</p><strong>${textoTempo}</strong></div>`;
  elements.btnConfirmar.textContent = "Finalizar Pedido";
  elements.btnConfirmar.className = "btn btn-success";
  elements.modalAcao.style.display = "block";
}

function abrirModalCancelar(id, nomeItem) {
    const p = state.pedidos.find((x) => x.id === id);
    if (!p) return;
    state.pedidoSelecionado = p;
    elements.cancelarPedidoId.textContent = `#${p.pedido_id} - ${nomeItem}`;
    elements.inputMotivoCancelamento.value = "Ingredientes insuficientes"; 
    elements.modalCancelar.style.display = "block";
}

function fecharModalCancelar() {
    elements.modalCancelar.style.display = "none";
    state.pedidoSelecionado = null;
}

function confirmarCancelamento() {
    if (!state.pedidoSelecionado) return;
    const motivo = elements.inputMotivoCancelamento.value;
    cancelarPedidoApi(state.pedidoSelecionado.id, motivo);
}

function fecharModal() {
  elements.modalAcao.style.display = "none";
  state.pedidoSelecionado = null;
}

function confirmarAcao() {
  if (!state.pedidoSelecionado) return;
  if (state.pedidoSelecionado.status === "RECEBIDO") {
    iniciarPreparo(state.pedidoSelecionado.id);
  } else {
    finalizarPedido(state.pedidoSelecionado.id);
  }
}

// Globais
window.abrirModalIniciar = abrirModalIniciar;
window.abrirModalFinalizar = abrirModalFinalizar;
window.abrirModalCancelar = abrirModalCancelar;
window.fecharModalCancelar = fecharModalCancelar;
window.confirmarCancelamento = confirmarCancelamento;
window.abrirModalEstoque = abrirModalEstoque;
window.fecharModalEstoque = fecharModalEstoque;
window.confirmarReposicao = confirmarReposicao;

function mostrarLoading(show) { if(elements.loading) elements.loading.style.display = show ? "block" : "none"; }
function mostrarToast(msg, tipo = "success") {
  elements.toast.textContent = msg;
  elements.toast.className = `toast ${tipo} show`;
  setTimeout(() => elements.toast.classList.remove("show"), 3000);
}
function iniciarAtualizacaoAutomatica() {
  state.atualizacaoAutomatica = setInterval(() => { carregarPedidos(true); carregarEstoque(); }, 10000);
}
window.addEventListener("beforeunload", () => { if (state.atualizacaoAutomatica) clearInterval(state.atualizacaoAutomatica); });