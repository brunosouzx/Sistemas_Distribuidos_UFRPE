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
  
  // Modal Pedidos
  modalAcao: document.getElementById("modalAcao"),
  modalTitulo: document.getElementById("modalTitulo"),
  modalPedidoId: document.getElementById("modalPedidoId"),
  modalCliente: document.getElementById("modalCliente"),
  modalItem: document.getElementById("modalItem"),
  modalObs: document.getElementById("modalObs"),
  modalObsContainer: document.getElementById("modalObsContainer"),
  tempoPreparoContainer: document.getElementById("tempoPreparoContainer"),
  inputTempoPreparo: document.getElementById("inputTempoPreparo"),
  btnConfirmar: document.getElementById("btnConfirmar"),
  btnCancelar: document.getElementById("btnCancelar"),
  
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

// Inicialização Robusta
function init() {
  console.log("Iniciando aplicação...");
  try {
    setupEventListeners();
    carregarPedidos();
    carregarEstoque();
    iniciarAtualizacaoAutomatica();
  } catch (error) {
    console.error("Erro fatal na inicialização:", error);
    mostrarToast("Erro ao iniciar sistema. Verifique o console.", "error");
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
          if (typeof fecharModalEstoque === 'function') fecharModalEstoque();
      });
  });

  window.onclick = function (event) {
    if (elements.modalAcao && event.target === elements.modalAcao) fecharModal();
    if (elements.modalEstoque && event.target === elements.modalEstoque) if (typeof fecharModalEstoque === 'function') fecharModalEstoque();
  };
}

// --- API Calls (Pedidos) ---
async function carregarPedidos() {
  try {
    mostrarLoading(true);
    const response = await fetch(`${API_URL}/fila`);
    const data = await response.json();
    state.pedidos = data.pedidos || [];
    renderizarPedidos();
    atualizarEstatisticas();
  } catch (error) {
    console.error("Erro ao carregar pedidos:", error);
    mostrarToast("Erro ao carregar pedidos", "error");
  } finally {
    mostrarLoading(false);
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
    // Não enviamos mais tempo manual, o backend calcula
    const response = await fetch(`${API_URL}/pedidos/${pedidoId}/finalizar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}), 
    });
    const data = await response.json();
    if (response.ok) {
      // O backend retorna o tempo calculado
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

// --- API Calls (Estoque) ---
async function carregarEstoque() {
  try {
    if (elements.estoqueLoading) elements.estoqueLoading.style.display = "flex";
    const response = await fetch(`${ESTOQUE_API_URL}/estoque`);
    const data = await response.json();
    state.estoque = data.estoque || [];
    renderizarEstoque();
  } catch (error) {
    console.error("Erro estoque:", error);
  } finally {
    if (elements.estoqueLoading) elements.estoqueLoading.style.display = "none";
  }
}

// --- Lógica Modal Estoque ---
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

        const data = await response.json();

        if (response.ok) {
            mostrarToast(`✅ ${ingrediente} abastecido (+${quantidade})`, "success");
            carregarEstoque();
            fecharModalEstoque();
        } else {
            mostrarToast(data.erro || "Erro ao repor", "error");
        }
    } catch (error) {
        console.error(error);
        mostrarToast("Erro de conexão", "error");
    }
}

window.abrirModalEstoque = abrirModalEstoque;
window.fecharModalEstoque = fecharModalEstoque;
window.confirmarReposicao = confirmarReposicao;

// --- Renderização ---
function renderizarPedidos() {
  let pedidosFiltrados = state.pedidos;
  if (state.filtroAtivo !== "todos") {
    pedidosFiltrados = state.pedidos.filter((p) => p.status === state.filtroAtivo);
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
    elements.pedidosGrid.appendChild(criarPedidoCard(pedido));
  });
}

function criarPedidoCard(pedido) {
  const card = document.createElement("div");
  card.className = `pedido-card status-${pedido.status}`;

  const dataRecebimento = new Date(pedido.data_recebimento).toLocaleString("pt-BR");
  let tempoInfo = `<p class="pedido-tempo">📅 ${dataRecebimento}</p>`;
  
  // Se estiver pronto, mostra o tempo final
  if (pedido.status === 'PRONTO' && pedido.tempo_preparacao) {
      tempoInfo += `<p class="pedido-tempo">⏱️ Total: ${pedido.tempo_preparacao} min</p>`;
  }
  // Se estiver preparando, mostra a hora que iniciou
  if (pedido.status === 'PREPARANDO' && pedido.data_inicio_preparo) {
      const horaInicio = new Date(pedido.data_inicio_preparo).toLocaleTimeString("pt-BR", {hour: '2-digit', minute:'2-digit'});
      tempoInfo += `<p class="pedido-tempo" style="color: var(--secondary-color)">🍳 Iniciado às ${horaInicio}</p>`;
  }

  const obsHtml = pedido.observacao
    ? `<div class="pedido-obs">⚠️ ${pedido.observacao}</div>`
    : "";

  let acoes = "";
  if (pedido.status === "RECEBIDO") {
    acoes = `<button class="btn btn-warning" onclick="abrirModalIniciar(${pedido.id})">🍳 Iniciar</button>`;
  } else if (pedido.status === "PREPARANDO") {
    acoes = `<button class="btn btn-success" onclick="abrirModalFinalizar(${pedido.id})">✅ Finalizar</button>`;
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
          <td>
            <button class="btn-sm btn-success" onclick="abrirModalEstoque('${item.nome}')" title="Adicionar">
                + Repor
            </button>
          </td>
        </tr>
      `;
    }).join("");
}

// --- LÓGICA DE MODAIS DO PEDIDO (MODIFICADA) ---

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
  
  // Esconde qualquer input de tempo (contagem será automática ao clicar)
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
  
  // CÁLCULO VISUAL DO TEMPO
  let textoTempo = "Calculando...";
  if (p.data_inicio_preparo) {
      // Tenta calcular diferença visualmente para o usuário saber quanto tempo levou
      try {
          // O formato da data pode variar dependendo do browser/banco, mas o Date do JS costuma aceitar ISO
          // Se o banco salvar em UTC e o browser estiver em local, pode dar diferença se não tiver 'Z'. 
          // Mas como gravamos CURRENT_TIMESTAMP, geralmente está ok.
          const inicio = new Date(p.data_inicio_preparo);
          const agora = new Date();
          
          // Fallback para caso a data seja inválida
          if(!isNaN(inicio.getTime())){
             const diffMs = agora - inicio;
             // Se der negativo (fuso horário), assumimos pelo menos 1 min
             const diffMins = Math.max(1, Math.floor(diffMs / 60000));
             textoTempo = `${diffMins} minutos decorridos`;
          }
      } catch(e) { console.error(e); }
  }

  // Mostra o tempo calculado AUTOMATICAMENTE no modal, sem input para editar
  const container = elements.tempoPreparoContainer;
  container.style.display = "block";
  container.innerHTML = `
      <div style="background: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #c8e6c9;">
        <p style="margin-bottom: 5px; font-size: 0.9rem;">Tempo de preparo:</p>
        <strong style="font-size: 1.4rem;">⏱️ ${textoTempo}</strong>
      </div>
  `;
  
  elements.btnConfirmar.textContent = "Finalizar Pedido";
  elements.btnConfirmar.className = "btn btn-success";
  elements.modalAcao.style.display = "block";
}

function fecharModal() {
  elements.modalAcao.style.display = "none";
  state.pedidoSelecionado = null;
}

function confirmarAcao() {
  if (!state.pedidoSelecionado) return;
  
  if (state.pedidoSelecionado.status === "RECEBIDO") {
    // Ação: Iniciar (sem parâmetros extras)
    iniciarPreparo(state.pedidoSelecionado.id);
  } else {
    // Ação: Finalizar (sem parâmetros extras, backend calcula)
    finalizarPedido(state.pedidoSelecionado.id);
  }
}

// Globais para HTML
window.abrirModalIniciar = abrirModalIniciar;
window.abrirModalFinalizar = abrirModalFinalizar;

function mostrarLoading(show) { elements.loading.style.display = show ? "block" : "none"; }
function mostrarToast(msg, tipo = "success") {
  elements.toast.textContent = msg;
  elements.toast.className = `toast ${tipo} show`;
  setTimeout(() => elements.toast.classList.remove("show"), 3000);
}
function iniciarAtualizacaoAutomatica() {
  state.atualizacaoAutomatica = setInterval(() => {
    carregarPedidos();
    carregarEstoque();
  }, 10000);
}
window.addEventListener("beforeunload", () => { if (state.atualizacaoAutomatica) clearInterval(state.atualizacaoAutomatica); });