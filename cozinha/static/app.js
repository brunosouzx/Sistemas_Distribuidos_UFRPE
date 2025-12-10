// Configuração da API
const API_URL = "http://localhost:5001";
const ESTOQUE_API_URL = "http://localhost:5002";

// Estado da aplicação
let state = {
  pedidos: [],
  estoque: [],
  filtroAtivo: "todos",
  pedidoSelecionado: null,
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
  btnRefresh: document.getElementById("btnRefresh"),
  toast: document.getElementById("toast"),
  estoqueTableBody: document.getElementById("estoqueTableBody"),
  estoqueLoading: document.getElementById("estoqueLoading"),
  btnRefreshEstoque: document.getElementById("btnRefreshEstoque"),
};

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  carregarPedidos();
  carregarEstoque();
  iniciarAtualizacaoAutomatica();
});

// Event Listeners
function setupEventListeners() {
  // Filtros
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      state.filtroAtivo = this.dataset.status;
      renderizarPedidos();
    });
  });

  // Refresh
  elements.btnRefresh.addEventListener("click", () => {
    carregarPedidos();
    mostrarToast("Atualizando pedidos...", "info");
  });

  // Refresh Estoque
  elements.btnRefreshEstoque.addEventListener("click", () => {
    carregarEstoque();
    mostrarToast("Atualizando estoque...", "info");
  });

  // Modal
  elements.btnCancelar.addEventListener("click", fecharModal);
  elements.btnConfirmar.addEventListener("click", confirmarAcao);

  document.querySelector(".close").addEventListener("click", fecharModal);

  // Fechar modal clicando fora
  window.onclick = function (event) {
    if (event.target === elements.modalAcao) {
      fecharModal();
    }
  };
}

// API Calls
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
    const response = await fetch(`${API_URL}/pedidos/${pedidoId}/iniciar`, {
      method: "PUT",
    });

    const data = await response.json();

    if (response.ok) {
      mostrarToast("Preparo iniciado com sucesso!", "success");
      carregarPedidos();
      fecharModal();
    } else {
      mostrarToast(data.erro || "Erro ao iniciar preparo", "error");
    }
  } catch (error) {
    console.error("Erro ao iniciar preparo:", error);
    mostrarToast("Erro ao iniciar preparo", "error");
  }
}

async function finalizarPedido(pedidoId, tempoPreparo) {
  try {
    const response = await fetch(`${API_URL}/pedidos/${pedidoId}/finalizar`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tempo_preparacao: parseInt(tempoPreparo),
      }),
    });

    const data = await response.json();

    if (response.ok) {
      mostrarToast("Pedido finalizado com sucesso!", "success");
      carregarPedidos();
      fecharModal();
    } else {
      mostrarToast(data.erro || "Erro ao finalizar pedido", "error");
    }
  } catch (error) {
    console.error("Erro ao finalizar pedido:", error);
    mostrarToast("Erro ao finalizar pedido", "error");
  }
}

async function carregarEstoque() {
  try {
    if (elements.estoqueLoading) {
      elements.estoqueLoading.style.display = "flex";
    }
    const response = await fetch(`${ESTOQUE_API_URL}/estoque`);
    const data = await response.json();

    state.estoque = data.estoque || [];
    renderizarEstoque();
  } catch (error) {
    console.error("Erro ao carregar estoque:", error);
    mostrarToast("Erro ao carregar estoque", "error");
  } finally {
    if (elements.estoqueLoading) {
      elements.estoqueLoading.style.display = "none";
    }
  }
}

// Renderização
function renderizarPedidos() {
  let pedidosFiltrados = state.pedidos;

  if (state.filtroAtivo !== "todos") {
    pedidosFiltrados = state.pedidos.filter(
      (p) => p.status === state.filtroAtivo
    );
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
    const card = criarPedidoCard(pedido);
    elements.pedidosGrid.appendChild(card);
  });
}

function criarPedidoCard(pedido) {
  const card = document.createElement("div");
  card.className = `pedido-card status-${pedido.status}`;

  const dataRecebimento = new Date(pedido.data_recebimento).toLocaleString(
    "pt-BR"
  );
  let tempoInfo = `<p class="pedido-tempo">📅 Recebido: ${dataRecebimento}</p>`;

  if (pedido.data_inicio_preparo) {
    const dataInicio = new Date(pedido.data_inicio_preparo).toLocaleString(
      "pt-BR"
    );
    tempoInfo += `<p class="pedido-tempo">🍳 Iniciado: ${dataInicio}</p>`;
  }

  if (pedido.data_conclusao) {
    const dataConclusao = new Date(pedido.data_conclusao).toLocaleString(
      "pt-BR"
    );
    tempoInfo += `<p class="pedido-tempo">✅ Finalizado: ${dataConclusao}</p>`;
    if (pedido.tempo_preparacao) {
      tempoInfo += `<p class="pedido-tempo">⏱️ Tempo: ${pedido.tempo_preparacao} min</p>`;
    }
  }

  const obsHtml = pedido.observacao
    ? `<div class="pedido-obs">⚠️ <strong>Obs:</strong> ${pedido.observacao}</div>`
    : "";

  let acoes = "";
  if (pedido.status === "RECEBIDO") {
    acoes = `<button class="btn btn-warning" onclick="abrirModalIniciar(${pedido.id})">🍳 Iniciar Preparo</button>`;
  } else if (pedido.status === "PREPARANDO") {
    acoes = `<button class="btn btn-success" onclick="abrirModalFinalizar(${pedido.id})">✅ Finalizar</button>`;
  }

  card.innerHTML = `
        <div class="pedido-header">
            <div class="pedido-numero">#${pedido.pedido_id}</div>
            <span class="pedido-status status-badge-${pedido.status}">${pedido.status}</span>
        </div>
        <div class="pedido-info">
            <p><strong>Cliente:</strong> ${pedido.cliente}</p>
            <p class="item-destaque">🍔 ${pedido.item}</p>
            ${obsHtml}
            ${tempoInfo}
        </div>
        <div class="pedido-actions">
            ${acoes}
        </div>
    `;

  return card;
}

function atualizarEstatisticas() {
  const recebidos = state.pedidos.filter((p) => p.status === "RECEBIDO").length;
  const preparando = state.pedidos.filter(
    (p) => p.status === "PREPARANDO"
  ).length;
  const prontos = state.pedidos.filter((p) => p.status === "PRONTO").length;

  elements.statRecebidos.textContent = recebidos;
  elements.statPreparando.textContent = preparando;
  elements.statProntos.textContent = prontos;
}

function renderizarEstoque() {
  if (!elements.estoqueTableBody) return;

  if (state.estoque.length === 0) {
    elements.estoqueTableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; padding: 30px; color: #999;">
          📦 Nenhum ingrediente cadastrado
        </td>
      </tr>
    `;
    return;
  }

  elements.estoqueTableBody.innerHTML = state.estoque
    .map((item) => {
      const quantidade = item.quantidade || 0;
      const estoqueMinimo = item.estoque_minimo || 10;

      let statusClass = "status-ok";
      let statusText = "OK";

      if (quantidade === 0) {
        statusClass = "status-critico";
        statusText = "Esgotado";
      } else if (quantidade <= estoqueMinimo) {
        statusClass = "status-baixo";
        statusText = "Baixo";
      }

      return `
        <tr>
          <td><strong>${item.nome}</strong></td>
          <td>${quantidade}</td>
          <td>${item.unidade || "unidade"}</td>
          <td><span class="estoque-status ${statusClass}">${statusText}</span></td>
        </tr>
      `;
    })
    .join("");
}

// Modal
function abrirModalIniciar(pedidoId) {
  const pedido = state.pedidos.find((p) => p.id === pedidoId);
  if (!pedido) return;

  state.pedidoSelecionado = pedido;

  elements.modalTitulo.textContent = "🍳 Iniciar Preparo";
  elements.modalPedidoId.textContent = `#${pedido.pedido_id}`;
  elements.modalCliente.textContent = pedido.cliente;
  elements.modalItem.textContent = pedido.item;

  if (pedido.observacao) {
    elements.modalObs.textContent = pedido.observacao;
    elements.modalObsContainer.style.display = "block";
  } else {
    elements.modalObsContainer.style.display = "none";
  }

  elements.tempoPreparoContainer.style.display = "none";
  elements.btnConfirmar.textContent = "Iniciar";
  elements.btnConfirmar.className = "btn btn-warning";

  elements.modalAcao.style.display = "block";
}

function abrirModalFinalizar(pedidoId) {
  const pedido = state.pedidos.find((p) => p.id === pedidoId);
  if (!pedido) return;

  state.pedidoSelecionado = pedido;

  elements.modalTitulo.textContent = "✅ Finalizar Pedido";
  elements.modalPedidoId.textContent = `#${pedido.pedido_id}`;
  elements.modalCliente.textContent = pedido.cliente;
  elements.modalItem.textContent = pedido.item;

  if (pedido.observacao) {
    elements.modalObs.textContent = pedido.observacao;
    elements.modalObsContainer.style.display = "block";
  } else {
    elements.modalObsContainer.style.display = "none";
  }

  elements.tempoPreparoContainer.style.display = "block";
  elements.inputTempoPreparo.value = 8;
  elements.btnConfirmar.textContent = "Finalizar";
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
    iniciarPreparo(state.pedidoSelecionado.id);
  } else if (state.pedidoSelecionado.status === "PREPARANDO") {
    const tempo = elements.inputTempoPreparo.value;
    if (!tempo || tempo < 1) {
      mostrarToast("Informe o tempo de preparação", "error");
      return;
    }
    finalizarPedido(state.pedidoSelecionado.id, tempo);
  }
}

// Tornar funções globais para onclick
window.abrirModalIniciar = abrirModalIniciar;
window.abrirModalFinalizar = abrirModalFinalizar;

// Utilitários
function mostrarLoading(show) {
  elements.loading.style.display = show ? "block" : "none";
}

function mostrarToast(mensagem, tipo = "success") {
  elements.toast.textContent = mensagem;
  elements.toast.className = `toast ${tipo} show`;

  setTimeout(() => {
    elements.toast.classList.remove("show");
  }, 3000);
}

function iniciarAtualizacaoAutomatica() {
  // Atualizar a cada 10 segundos
  state.atualizacaoAutomatica = setInterval(() => {
    carregarPedidos();
    carregarEstoque();
  }, 10000);
}

// Limpar intervalo ao sair da página
window.addEventListener("beforeunload", () => {
  if (state.atualizacaoAutomatica) {
    clearInterval(state.atualizacaoAutomatica);
  }
});
